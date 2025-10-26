"""知识查询和GraphRAG相关的API路由。"""

from __future__ import annotations

import asyncio
import uuid
import datetime as dt
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from database import async_session_factory
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.source_service import get_source_service
from services.audit_logger import audit_logger
from security.casbin_enforcer import require_permission
from schemas import (
    GraphRAGQueryRequest,
    GraphRAGQueryResponse,
    GraphRAGErrorResponse,
    EvidenceAnchor,
)
from config import settings
from loguru import logger

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge-query"])


# Helper function to get actor info from request
def get_actor_info(user) -> Dict[str, Any]:
    """从请求中获取行动者信息。"""
    return {
        "user_id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "ip_address": getattr(user, "ip_address", None),
    }


class GraphRAGErrorCodes:
    """GraphRAG查询错误代码。"""
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_QUERY = "INVALID_QUERY"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@router.post(
    "/query",
    response_model=GraphRAGQueryResponse,
    summary="执行 GraphRAG 查询",
    description="对选定知识源发起 GraphRAG 查询，返回答案、置信度与证据锚点信息。",
    response_model_exclude_none=True,
    responses={
        200: {"description": "查询成功并返回结构化回答"},
        400: {
            "model": GraphRAGErrorResponse,
            "description": "查询请求无效或底层处理失败",
        },
        403: {"description": "RBAC：权限不足"},
        404: {"description": "指定的知识源不存在"},
        408: {
            "model": GraphRAGErrorResponse,
            "description": "查询超时",
        },
        500: {
            "model": GraphRAGErrorResponse,
            "description": "内部服务器错误",
        },
    },
)
async def query_knowledge_graph(
    query_request: GraphRAGQueryRequest,
    user=Depends(require_permission("/knowledge/query", "POST")),
):
    """使用GraphRAG查询知识图谱。"""
    start_time = dt.datetime.now()
    query_id = uuid.uuid4()

    try:
        async with asyncio.timeout(query_request.timeout_seconds):
            # 记录审计日志
            await audit_logger.record_event(
                actor_id=get_actor_info(user).get("user_id"),
                actor_email=get_actor_info(user).get("email"),
                resource="knowledge_graph",
                action="query",
                status="started",
                target=str(query_id),
                details=f"开始GraphRAG查询: {query_request.query[:100]}...",
                metadata={
                    "query_id": str(query_id),
                    "query_length": len(query_request.query),
                    "max_results": query_request.max_results,
                    "include_evidence": query_request.include_evidence,
                    "source_ids": [str(sid) for sid in query_request.source_ids] if query_request.source_ids else None,
                    "timeout_seconds": query_request.timeout_seconds,
                },
                ip_address=get_actor_info(user).get("ip_address"),
            )

            # 初始化Neo4j知识服务
            knowledge_service = Neo4jKnowledgeService()

            # 如果指定了源ID，进行权限验证
            if query_request.source_ids:
                async with async_session_factory() as session:
                    source_service = get_source_service(session)

                    # 验证所有指定的知识源都存在且用户有权限访问
                    for source_id in query_request.source_ids:
                        source = await source_service.get_source_by_id(source_id)
                        if not source:
                            raise HTTPException(
                                status_code=404,
                                detail=f"指定的知识源 {source_id} 不存在"
                            )
                        if not source.is_active:
                            raise HTTPException(
                                status_code=400,
                                detail=f"知识源 {source.name} 未激活，无法查询"
                            )

            # 执行GraphRAG查询
            logger.info(f"执行GraphRAG查询 {query_id}: {query_request.query[:50]}...")

            result = await knowledge_service.query(
                question=query_request.query,
                mode="hybrid",  # 使用混合模式
                max_results=query_request.max_results,
                include_evidence=query_request.include_evidence,
                source_ids=query_request.source_ids,
            )

            processing_time_ms = int((dt.datetime.now() - start_time).total_seconds() * 1000)

            if not result.get("success"):
                error_code = GraphRAGErrorCodes.PROCESSING_ERROR
                error_message = result.get("error", "查询处理失败")

                # 记录失败的审计日志
                await audit_logger.record_event(
                    actor_id=get_actor_info(user).get("user_id"),
                    actor_email=get_actor_info(user).get("email"),
                    resource="knowledge_graph",
                    action="query",
                    status="failed",
                    target=str(query_id),
                    details=f"GraphRAG查询失败: {error_message}",
                    metadata={
                        "query_id": str(query_id),
                        "error_code": error_code,
                        "processing_time_ms": processing_time_ms,
                    },
                    ip_address=get_actor_info(user).get("ip_address"),
                )

                return JSONResponse(
                    status_code=400,
                    content=GraphRAGErrorResponse(
                        error_code=error_code,
                        error_message=error_message,
                        query_id=query_id,
                        processing_time_ms=processing_time_ms,
                    ).model_dump(mode="json")
                )

            # 构建证据锚点
            evidence_anchors = []
            if query_request.include_evidence and result.get("evidence"):
                for evidence in result.get("evidence", []):
                    anchor = EvidenceAnchor(
                        source_id=evidence.get("source_id", uuid.uuid4()),
                        source_name=evidence.get("source_name", "未知来源"),
                        content_snippet=evidence.get("content", "")[:200],
                        relevance_score=evidence.get("relevance_score", 0.0),
                        page_number=evidence.get("page_number"),
                        section_title=evidence.get("section_title"),
                    )
                    evidence_anchors.append(anchor)

            # 构建响应
            response = GraphRAGQueryResponse(
                answer=result.get("answer", ""),
                confidence_score=result.get("confidence_score", 0.0),
                evidence_anchors=evidence_anchors,
                sources_queried=query_request.source_ids or [],
                processing_time_ms=processing_time_ms,
                query_id=query_id,
            )

            # 记录成功的审计日志
            await audit_logger.record_event(
                actor_id=get_actor_info(user).get("user_id"),
                actor_email=get_actor_info(user).get("email"),
                resource="knowledge_graph",
                action="query",
                status="success",
                target=str(query_id),
                details=f"GraphRAG查询成功完成",
                metadata={
                    "query_id": str(query_id),
                    "confidence_score": response.confidence_score,
                    "evidence_count": len(evidence_anchors),
                    "processing_time_ms": processing_time_ms,
                    "sources_queried_count": len(response.sources_queried),
                },
                ip_address=get_actor_info(user).get("ip_address"),
            )

            logger.info(f"GraphRAG查询 {query_id} 成功完成，耗时 {processing_time_ms}ms")
            return response

    except asyncio.TimeoutError:
        processing_time_ms = int((dt.datetime.now() - start_time).total_seconds() * 1000)

        # 记录超时的审计日志
        await audit_logger.record_event(
            actor_id=get_actor_info(user).get("user_id"),
            actor_email=get_actor_info(user).get("email"),
            resource="knowledge_graph",
            action="query",
            status="failed",
            target=str(query_id),
            details=f"GraphRAG查询超时 ({query_request.timeout_seconds}秒)",
            metadata={
                "query_id": str(query_id),
                "error_code": GraphRAGErrorCodes.TIMEOUT,
                "timeout_seconds": query_request.timeout_seconds,
                "processing_time_ms": processing_time_ms,
            },
            ip_address=get_actor_info(user).get("ip_address"),
        )

        logger.warning(f"GraphRAG查询 {query_id} 超时")
        return JSONResponse(
            status_code=408,
            content=GraphRAGErrorResponse(
                error_code=GraphRAGErrorCodes.TIMEOUT,
                error_message=f"查询超时，请尝试简化查询或增加超时时间",
                query_id=query_id,
                processing_time_ms=processing_time_ms,
            ).model_dump(mode="json")
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        processing_time_ms = int((dt.datetime.now() - start_time).total_seconds() * 1000)

        # 记录错误的审计日志
        await audit_logger.record_event(
            actor_id=get_actor_info(user).get("user_id"),
            actor_email=get_actor_info(user).get("email"),
            resource="knowledge_graph",
            action="query",
            status="failed",
            target=str(query_id),
            details=f"GraphRAG查询内部错误: {str(e)}",
            metadata={
                "query_id": str(query_id),
                "error_code": GraphRAGErrorCodes.INTERNAL_ERROR,
                "processing_time_ms": processing_time_ms,
            },
            ip_address=get_actor_info(user).get("ip_address"),
        )

        logger.error(f"GraphRAG查询 {query_id} 发生内部错误: {e}")
        return JSONResponse(
            status_code=500,
            content=GraphRAGErrorResponse(
                error_code=GraphRAGErrorCodes.INTERNAL_ERROR,
                error_message="内部服务器错误，请稍后重试",
                query_id=query_id,
                processing_time_ms=processing_time_ms,
            ).model_dump(mode="json")
        )


@router.get(
    "/sources",
    summary="列出可供查询的知识源",
    description="返回激活状态的知识源元数据，供前端在 GraphRAG 查询时选择。",
    responses={
        200: {"description": "成功返回知识源列表"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def list_available_sources(
    is_active: Optional[bool] = Query(True, description="只返回激活的知识源"),
    source_type: Optional[str] = Query(None, description="按源类型过滤"),
    user=Depends(require_permission("/knowledge/sources", "GET")),
):
    """获取可用的知识源列表，用于查询时选择。"""
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            sources, total = await source_service.list_sources(
                page=1,
                size=100,  # 获取前100个
                is_active=is_active,
                source_type=source_type,
            )

            # 转换为简单格式
            available_sources = []
            for source in sources:
                available_sources.append({
                    "id": str(source.id),
                    "name": source.name,
                    "description": source.description,
                    "source_type": source.source_type,
                    "last_synced_at": source.last_synced_at.isoformat() if source.last_synced_at else None,
                    "is_active": source.is_active,
                })

            return {
                "sources": available_sources,
                "total": total,
                "filters": {
                    "is_active": is_active,
                    "source_type": source_type,
                }
            }

    except Exception as e:
        logger.error(f"获取可用知识源列表失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/query/{query_id}",
    summary="查询历史记录详情",
    description="根据查询 ID 返回缓存的查询结果，当前版本为占位实现。",
    responses={
        200: {"description": "返回缓存或占位信息"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def get_query_result(
    query_id: uuid.UUID,
    user=Depends(require_permission("/knowledge/query", "GET")),
):
    """获取之前查询的结果（如果缓存中有）。"""
    try:
        # 这个功能可以实现查询结果缓存
        # 目前返回暂未实现的信息
        return {
            "query_id": str(query_id),
            "message": "查询结果缓存功能尚未实现",
            "status": "not_found",
        }

    except Exception as e:
        logger.error(f"获取查询结果失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get(
    "/stats",
    summary="获取知识图谱运行统计",
    description="汇总 Neo4j 统计、知识源数量以及 GraphRAG 服务能力。",
    responses={
        200: {"description": "成功返回知识图谱统计信息"},
        403: {"description": "RBAC：权限不足"},
        500: {"description": "内部服务器错误"},
    },
)
async def get_knowledge_stats(
    user=Depends(require_permission("/knowledge/stats", "GET")),
):
    """获取知识图谱统计信息。"""
    try:
        knowledge_service = Neo4jKnowledgeService()

        # 获取基础统计信息
        stats = await knowledge_service.get_statistics()

        # 添加额外的统计信息
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            # 获取知识源统计
            sources, _ = await source_service.list_sources(page=1, size=1)
            active_sources = [s for s in sources if s.is_active]

            stats.update({
                "knowledge_sources": {
                    "total": len(sources),
                    "active": len(active_sources),
                    "types": list(set(s.source_type for s in sources)),
                },
                "api_version": "v1",
                "graphrag_enabled": True,
                "max_query_timeout": settings.graphrag_query_timeout_seconds,
                "max_results_per_query": settings.graphrag_max_results,
                "evidence_collection_enabled": settings.graphrag_enable_evidence,
            })

        return stats

    except Exception as e:
        logger.error(f"获取知识图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
