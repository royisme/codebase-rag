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
from services.graph_rag_service import GraphRAGService
from services.graph_query_cache import graph_query_cache
from security.casbin_enforcer import require_permission
from schemas import (
    GraphRAGQueryRequest,
    GraphRAGQueryResponse,
    GraphRAGErrorResponse,
    EvidenceAnchor,
    GraphRAGAnswerPayload,
)
from config import settings
from loguru import logger

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge-query"])
graph_rag_service = GraphRAGService()


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
    context_query_id = query_request.context_query_id
    context_query_id_str = str(context_query_id) if context_query_id else None
    cached_context: Optional[GraphRAGQueryResponse] = None
    context_cache_hit = False

    if context_query_id_str:
        cached_context = await graph_query_cache.get(context_query_id_str)
        context_cache_hit = cached_context is not None

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
                    "context_query_id": context_query_id_str,
                    "context_cache_hit": context_cache_hit,
                },
                ip_address=get_actor_info(user).get("ip_address"),
            )

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

            # 构造带上下文的问题
            question_for_service = query_request.query.strip()
            if cached_context:
                previous_answer = cached_context.answer
                context_blocks: List[str] = [question_for_service]

                if previous_answer.summary:
                    context_blocks.append(f"上一轮摘要: {previous_answer.summary.strip()}")

                if previous_answer.related_entities:
                    entity_lines: List[str] = []
                    for entity in previous_answer.related_entities[:8]:
                        if isinstance(entity, dict):
                            entity_type = entity.get("type", "entity")
                            name = entity.get("name") or entity.get("detail") or ""
                            detail = entity.get("detail") or ""
                        else:
                            entity_type = getattr(entity, "type", "entity")
                            name = getattr(entity, "name", None) or getattr(entity, "detail", "") or ""
                            detail = getattr(entity, "detail", "") or ""

                        entity_lines.append(f"- {entity_type}: {name} {detail}".strip())
                    if [line for line in entity_lines if line.strip()]:
                        context_blocks.append("上一轮关联实体:\n" + "\n".join(entity_lines))

                if previous_answer.next_actions:
                    action_lines = "\n".join(f"- {action}" for action in previous_answer.next_actions[:5])
                    context_blocks.append("上一轮建议操作:\n" + action_lines)

                question_for_service = "\n\n".join(block for block in context_blocks if block)

            # 执行GraphRAG查询
            logger.info(
                "执行GraphRAG查询 {} (context: {}, hit: {}): {}",
                query_id,
                context_query_id_str,
                context_cache_hit,
                query_request.query[:50],
            )

            rag_result = await graph_rag_service.query(
                question_for_service,
                source_ids=[str(sid) for sid in query_request.source_ids] if query_request.source_ids else None,
                timeout_seconds=query_request.timeout_seconds,
                include_evidence=query_request.include_evidence,
                max_results=query_request.max_results,
            )

            processing_time_ms = int((dt.datetime.now() - start_time).total_seconds() * 1000)

            if not rag_result.answer.summary or rag_result.answer.summary.strip() == "":
                error_code = GraphRAGErrorCodes.PROCESSING_ERROR
                error_message = "未能生成有效回答，请稍后重试"

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
                        "context_query_id": context_query_id_str,
                        "context_cache_hit": context_cache_hit,
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

            answer_payload = GraphRAGAnswerPayload.model_validate(
                {
                    "summary": rag_result.answer.summary,
                    "related_entities": rag_result.answer.related_entities,
                    "evidence": rag_result.answer.evidence,
                    "next_actions": rag_result.answer.next_actions,
                }
            )

            evidence_anchors: List[EvidenceAnchor] = []
            for item in answer_payload.evidence:
                source_identifier = item.source_ref or item.id
                if not source_identifier:
                    continue
                try:
                    evidence_uuid = uuid.UUID(str(source_identifier))
                except Exception:
                    continue
                evidence_anchors.append(
                    EvidenceAnchor(
                        source_id=evidence_uuid,
                        source_name=item.source_ref or item.id or "未知来源",
                        content_snippet=item.snippet[:200],
                        relevance_score=item.score or 0.0,
                    )
                )

            response = GraphRAGQueryResponse(
                answer=answer_payload,
                confidence_score=rag_result.confidence_score,
                evidence_anchors=evidence_anchors,
                raw_messages=rag_result.raw_messages,
                sources_queried=rag_result.sources_queried,
                processing_time_ms=rag_result.processing_time_ms or processing_time_ms,
                query_id=rag_result.query_id or query_id,
                issues=rag_result.issues,
            )

            await graph_query_cache.set(str(response.query_id), response)

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
                    "evidence_count": len(response.answer.evidence),
                    "processing_time_ms": response.processing_time_ms,
                    "sources_queried_count": len(response.sources_queried),
                    "context_query_id": context_query_id_str,
                    "context_cache_hit": context_cache_hit,
                },
                ip_address=get_actor_info(user).get("ip_address"),
            )

            logger.info(
                "GraphRAG查询 {} 成功完成，耗时 {}ms（issues: {}）",
                query_id,
                response.processing_time_ms,
                response.issues,
            )
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
                "context_query_id": context_query_id_str,
                "context_cache_hit": context_cache_hit,
            },
            ip_address=get_actor_info(user).get("ip_address"),
        )

        logger.warning(
            "GraphRAG查询 {} 超时（context: {}, hit: {})",
            query_id,
            context_query_id_str,
            context_cache_hit,
        )
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
                "context_query_id": context_query_id_str,
                "context_cache_hit": context_cache_hit,
            },
            ip_address=get_actor_info(user).get("ip_address"),
        )

        logger.error(
            "GraphRAG查询 {} 发生内部错误 (context: {}, hit: {}): {}",
            query_id,
            context_query_id_str,
            context_cache_hit,
            e,
        )
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
        cached = await graph_query_cache.get(str(query_id))
        if not cached:
            raise HTTPException(status_code=404, detail="查询结果已过期或未命中缓存")

        return cached.model_dump(mode="json")

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
