"""知识查询和GraphRAG相关的API路由。"""

from __future__ import annotations

import asyncio
import uuid
import datetime as dt
import json
import re
from typing import Dict, Any, Optional, List, Iterable

from fastapi import APIRouter, HTTPException, Depends, Query, status, Body
from fastapi.responses import JSONResponse, StreamingResponse

from database import async_session_factory
from services.neo4j_knowledge_service import neo4j_knowledge_service
from services.source_service import get_source_service
from services.graph_rag_service import (
    GraphRAGService,
    GraphRAGTimeoutError,
    GraphRAGQueryError,
)
from services.graph_query_cache import graph_query_cache
from security.casbin_enforcer import require_permission
from security.auth import current_active_user
from schemas import (
    GraphRAGQueryRequest,
    GraphRAGQueryResponse,
    GraphRAGErrorResponse,
    EvidenceAnchor,
    GraphRAGAnswerPayload,
    StreamQueryRequest,
)
from config import settings
from loguru import logger

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge-query"])
graph_rag_service = GraphRAGService(knowledge_service=neo4j_knowledge_service)


async def persist_successful_query(
    *,
    user,
    question: str,
    source_ids: Optional[List[str]],
    response: GraphRAGQueryResponse,
    processing_time_ms: int,
    mode: str,
) -> None:
    """持久化成功的知识查询记录。"""

    try:
        from database.models import KnowledgeQuery as _KQ

        async with async_session_factory() as session:
            record = _KQ(
                user_id=getattr(user, "id", None),
                source_id=(source_ids[0] if source_ids else None),
                question=question,
                answer_summary=response.answer.summary,
                code_snippets=None,
                mode=mode,
                duration_ms=processing_time_ms,
                status="success",
                error_message=None,
            )
            session.add(record)
            await session.commit()
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("记录知识查询历史失败: {}", exc)


async def cache_query_response(response: GraphRAGQueryResponse) -> None:
    """缓存查询结果，忽略缓存过程中的错误。"""

    if not response.query_id:
        return

    try:
        await graph_query_cache.set(str(response.query_id), response)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("缓存知识查询结果失败: {}", exc)


def build_evidence_anchors(answer_payload: GraphRAGAnswerPayload) -> List[EvidenceAnchor]:
    """根据回答证据生成 EvidenceAnchor 列表。"""

    anchors: List[EvidenceAnchor] = []
    for item in answer_payload.evidence:
        source_identifier = item.source_ref or item.id
        if not source_identifier:
            continue
        try:
            evidence_uuid = uuid.UUID(str(source_identifier))
        except Exception:
            continue
        anchors.append(
            EvidenceAnchor(
                source_id=evidence_uuid,
                source_name=item.source_ref or item.id or "未知来源",
                content_snippet=item.snippet[:200],
                relevance_score=item.score or 0.0,
            )
        )
    return anchors


class GraphRAGErrorCodes:
    """GraphRAG查询错误代码。"""

    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_QUERY = "INVALID_QUERY"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def build_error_payload(
    *,
    error_code: str,
    error_message: str,
    query_id: uuid.UUID,
    processing_time_ms: int,
) -> Dict[str, Any]:
    payload = GraphRAGErrorResponse(
        error_code=error_code,
        error_message=error_message,
        query_id=query_id,
        processing_time_ms=processing_time_ms,
    ).model_dump(mode="json")
    payload["code"] = payload["error_code"]
    payload["message"] = payload["error_message"]
    return payload


def _chunk_summary_text(summary: str, *, min_chunk_len: int = 32) -> Iterable[str]:
    """将回答摘要拆分为流式输出的块。"""

    if not summary:
        return []

    buffer = ""
    for token in re.split(r"(\s+)", summary):
        buffer += token
        if not token.strip():
            continue
        if len(buffer) >= min_chunk_len or re.search(r"[。！？.!?]$", token):
            yield buffer
            buffer = ""

    if buffer:
        yield buffer


def _encode_sse(event: str, payload: Dict[str, Any]) -> bytes:
    """格式化 SSE 事件."""

    body = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


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
                                detail=f"指定的知识源 {source_id} 不存在",
                            )
                        if not source.is_active:
                            raise HTTPException(
                                status_code=400,
                                detail=f"知识源 {source.name} 未激活，无法查询",
                            )

            # 构造带上下文的问题
            question_for_service = query_request.query.strip()
            if cached_context:
                previous_answer = cached_context.answer
                context_blocks: List[str] = [question_for_service]

                if previous_answer.summary:
                    context_blocks.append(
                        f"上一轮摘要: {previous_answer.summary.strip()}"
                    )

                if previous_answer.related_entities:
                    entity_lines: List[str] = []
                    for entity in previous_answer.related_entities[:8]:
                        if isinstance(entity, dict):
                            entity_type = entity.get("type", "entity")
                            name = entity.get("name") or entity.get("detail") or ""
                            detail = entity.get("detail") or ""
                        else:
                            entity_type = getattr(entity, "type", "entity")
                            name = (
                                getattr(entity, "name", None)
                                or getattr(entity, "detail", "")
                                or ""
                            )
                            detail = getattr(entity, "detail", "") or ""

                        entity_lines.append(f"- {entity_type}: {name} {detail}".strip())
                    if [line for line in entity_lines if line.strip()]:
                        context_blocks.append(
                            "上一轮关联实体:\n" + "\n".join(entity_lines)
                        )

                if previous_answer.next_actions:
                    action_lines = "\n".join(
                        f"- {action}" for action in previous_answer.next_actions[:5]
                    )
                    context_blocks.append("上一轮建议操作:\n" + action_lines)

                question_for_service = "\n\n".join(
                    block for block in context_blocks if block
                )

            # 执行GraphRAG查询
            logger.info(
                "执行GraphRAG查询 {} (context: {}, hit: {}): {}",
                query_id,
                context_query_id_str,
                context_cache_hit,
                query_request.query[:50],
            )

            try:
                rag_result = await graph_rag_service.query(
                    question_for_service,
                    source_ids=[str(sid) for sid in query_request.source_ids]
                    if query_request.source_ids
                    else None,
                    timeout_seconds=query_request.timeout_seconds,
                    include_evidence=query_request.include_evidence,
                    max_results=query_request.max_results,
                )
            except GraphRAGTimeoutError as timeout_exc:
                processing_time_ms = int(
                    (dt.datetime.now() - start_time).total_seconds() * 1000
                )
                return JSONResponse(
                    status_code=504,
                    content=build_error_payload(
                        error_code=GraphRAGErrorCodes.TIMEOUT,
                        error_message=str(timeout_exc),
                        query_id=timeout_exc.payload.get("query_id")
                        if timeout_exc.payload
                        else query_id,
                        processing_time_ms=processing_time_ms,
                    ),
                )
            except GraphRAGQueryError as query_exc:
                processing_time_ms = int(
                    (dt.datetime.now() - start_time).total_seconds() * 1000
                )
                return JSONResponse(
                    status_code=502,
                    content=build_error_payload(
                        error_code=GraphRAGErrorCodes.PROCESSING_ERROR,
                        error_message=str(query_exc),
                        query_id=query_exc.payload.get("query_id")
                        if query_exc.payload
                        else query_id,
                        processing_time_ms=processing_time_ms,
                    ),
                )

            processing_time_ms = int(
                (dt.datetime.now() - start_time).total_seconds() * 1000
            )

            if not rag_result.answer.summary or rag_result.answer.summary.strip() == "":
                error_code = GraphRAGErrorCodes.PROCESSING_ERROR
                error_message = "未能生成有效回答，请稍后重试"
                return JSONResponse(
                    status_code=400,
                    content=build_error_payload(
                        error_code=error_code,
                        error_message=error_message,
                        query_id=query_id,
                        processing_time_ms=processing_time_ms,
                    ),
                )

            answer_payload = GraphRAGAnswerPayload.model_validate(
                {
                    "summary": rag_result.answer.summary,
                    "related_entities": rag_result.answer.related_entities,
                    "evidence": rag_result.answer.evidence,
                    "next_actions": rag_result.answer.next_actions,
                }
            )

            evidence_anchors = build_evidence_anchors(answer_payload)

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

            await cache_query_response(response)
            await persist_successful_query(
                user=user,
                question=query_request.query,
                source_ids=query_request.source_ids,
                response=response,
                processing_time_ms=processing_time_ms,
                mode=query_request.retrieval_mode or "hybrid",
            )

            logger.info(
                "GraphRAG查询 {} 成功完成，耗时 {}ms（issues: {}）",
                query_id,
                response.processing_time_ms,
                response.issues,
            )
            return response

    except asyncio.TimeoutError:
        processing_time_ms = int(
            (dt.datetime.now() - start_time).total_seconds() * 1000
        )

        logger.warning(
            "GraphRAG查询 {} 超时（context: {}, hit: {})",
            query_id,
            context_query_id_str,
            context_cache_hit,
        )
        return JSONResponse(
            status_code=408,
            content=build_error_payload(
                error_code=GraphRAGErrorCodes.TIMEOUT,
                error_message="查询超时，请尝试简化查询或增加超时时间",
                query_id=query_id,
                processing_time_ms=processing_time_ms,
            ),
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        processing_time_ms = int(
            (dt.datetime.now() - start_time).total_seconds() * 1000
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
            content=build_error_payload(
                error_code=GraphRAGErrorCodes.INTERNAL_ERROR,
                error_message="内部服务器错误，请稍后重试",
                query_id=query_id,
                processing_time_ms=processing_time_ms,
            ),
        )


@router.post(
    "/query/stream",
    response_class=StreamingResponse,
    summary="流式执行 GraphRAG 查询（Token-Level Streaming）",
    description=(
        "通过 Server-Sent Events (SSE) 实时返回 GraphRAG 查询进度，"
        "支持真正的 token-level streaming，显著降低首帧延迟。"
        "事件类型: text_delta, status, entity, metadata, done, error"
    ),
)
async def stream_knowledge_graph(
    stream_request: StreamQueryRequest,
    user=Depends(require_permission("/knowledge/query", "POST")),
):
    """以 SSE 形式返回 GraphRAG 查询结果（支持真正的 token streaming）。"""

    question = stream_request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题内容不能为空")

    validated_source_ids: List[uuid.UUID] = []
    if stream_request.source_ids:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            for raw_source in stream_request.source_ids:
                try:
                    source_uuid = uuid.UUID(str(raw_source))
                except Exception as exc:  # noqa: BLE001 - 返回更友好的提示
                    raise HTTPException(
                        status_code=400,
                        detail=f"知识源 ID {raw_source} 不是有效的 UUID",
                    ) from exc

                source = await source_service.get_source_by_id(source_uuid)
                if not source:
                    raise HTTPException(
                        status_code=404,
                        detail=f"指定的知识源 {raw_source} 不存在",
                    )
                if not source.is_active:
                    raise HTTPException(
                        status_code=400,
                        detail=f"知识源 {source.name} 未激活，无法查询",
                    )
                validated_source_ids.append(source_uuid)

    timeout_seconds = stream_request.timeout or 120  # 默认 2 分钟
    retrieval_mode = stream_request.retrieval_mode or "hybrid"
    max_results = stream_request.top_k or 8
    session_id = stream_request.session_id

    async def event_generator():
        query_uuid = uuid.uuid4()
        start_time = dt.datetime.now(dt.timezone.utc)
        accumulated_summary = ""
        result_query_id: Optional[uuid.UUID] = None
        final_confidence: Optional[float] = None
        final_sources: List[str] = []
        final_next_actions: List[str] = []
        final_processing_time: Optional[int] = None

        def _clamp_confidence(raw: Optional[Any]) -> float:
            if raw is None:
                return 0.0
            try:
                value = float(raw)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                return 0.0
            if value < 0.0:
                return 0.0
            if value > 1.0:
                return 1.0
            return value

        try:
            async with asyncio.timeout(timeout_seconds):
                async for event in graph_rag_service.stream_query(
                    question,
                    source_ids=[str(sid) for sid in validated_source_ids] if validated_source_ids else None,
                    timeout_seconds=timeout_seconds,
                    include_evidence=True,
                    max_results=max_results,
                    session_id=session_id,
                ):
                    event_type = event.get("type")
                    
                    if event_type == "text_delta":
                        # SSE: text_delta event
                        accumulated_summary += event.get("content", "")
                        yield _encode_sse("text_delta", {"content": event.get("content", "")})
                    
                    elif event_type == "status":
                        # SSE: status event
                        yield _encode_sse("status", {
                            "stage": event.get("stage"),
                            "message": event.get("message"),
                        })
                    
                    elif event_type == "entity":
                        # SSE: entity event
                        yield _encode_sse("entity", {"entity": event.get("entity")})
                    
                    elif event_type == "metadata":
                        # SSE: metadata event
                        final_confidence = _clamp_confidence(event.get("confidence_score"))
                        final_sources = event.get("sources_queried", [])
                        final_processing_time = event.get("execution_time_ms")
                        
                        yield _encode_sse("metadata", {
                            "confidence_score": final_confidence,
                            "execution_time_ms": final_processing_time,
                            "sources_queried": final_sources,
                            "retrieval_mode": retrieval_mode,
                        })
                    
                    elif event_type == "done":
                        # SSE: done event
                        result_query_id = uuid.UUID(event.get("query_id")) if event.get("query_id") else query_uuid
                        final_next_actions = event.get("next_actions", [])
                        final_confidence = _clamp_confidence(event.get("confidence_score", final_confidence))
                        final_sources = event.get("sources_queried", final_sources)
                        final_processing_time = event.get("processing_time_ms", final_processing_time)
                        
                        # Cache and persist the response
                        try:
                            answer_payload = GraphRAGAnswerPayload.model_validate({
                                "summary": accumulated_summary,
                                "related_entities": [],  # Already sent as entity events
                                "evidence": [],
                                "next_actions": final_next_actions,
                            })
                            
                            response = GraphRAGQueryResponse(
                                answer=answer_payload,
                                confidence_score=_clamp_confidence(final_confidence),
                                evidence_anchors=[],
                                raw_messages=None,
                                sources_queried=final_sources,
                                processing_time_ms=final_processing_time or 0,
                                query_id=result_query_id,
                                issues=[],
                            )
                            
                            await cache_query_response(response)
                            await persist_successful_query(
                                user=user,
                                question=question,
                                source_ids=validated_source_ids if validated_source_ids else None,
                                response=response,
                                processing_time_ms=final_processing_time or 0,
                                mode=retrieval_mode,
                            )
                        except Exception as cache_exc:
                            logger.warning(f"Failed to cache/persist query: {cache_exc}")
                        
                        yield _encode_sse("done", {
                            "query_id": str(result_query_id),
                            "timestamp": event.get("timestamp") or dt.datetime.now(dt.timezone.utc).isoformat(),
                            "summary": accumulated_summary,
                            "next_actions": final_next_actions,
                            "confidence_score": final_confidence,
                            "sources_queried": final_sources,
                            "processing_time_ms": final_processing_time,
                        })
                        return
                    
                    elif event_type == "error":
                        # SSE: error event
                        logger.warning(
                            "GraphRAG 流式查询 {} 失败: {}",
                            query_uuid,
                            event.get("message"),
                        )
                        yield _encode_sse("error", {
                            "message": event.get("message"),
                            "code": event.get("code"),
                            "processing_time_ms": event.get("processing_time_ms"),
                        })
                        return

        except asyncio.TimeoutError:
            processing_time_ms = int(
                (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.warning("GraphRAG 流式查询 {} 超时", query_uuid)
            yield _encode_sse("error", {
                "message": "查询超时，请尝试简化问题或增加超时时间。",
                "code": GraphRAGErrorCodes.TIMEOUT,
                "processing_time_ms": processing_time_ms,
            })
        except asyncio.CancelledError:
            logger.info("GraphRAG 流式查询 {} 被客户端中断", query_uuid)
            raise
        except Exception as exc:
            processing_time_ms = int(
                (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.exception("GraphRAG 流式查询 {} 发生未知错误: {}", query_uuid, exc)
            yield _encode_sse("error", {
                "message": "内部服务器错误，请稍后重试。",
                "code": GraphRAGErrorCodes.INTERNAL_ERROR,
                "processing_time_ms": processing_time_ms,
            })

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


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
    user=Depends(current_active_user),
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
            from datetime import datetime, timedelta, timezone

            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            # prefetch query counts
            try:
                from sqlalchemy import select, func
                from database import async_session_factory as _factory
                from database.models import KnowledgeQuery as _KQ

                async with _factory() as _s:
                    rows = await _s.execute(
                        select(_KQ.source_id, func.count(_KQ.id))
                        .where(_KQ.created_at >= seven_days_ago)
                        .group_by(_KQ.source_id)
                    )
                    counts = {str(k or ""): int(v) for k, v in rows.all()}
            except Exception:
                counts = {}

            for source in sources:
                meta = getattr(source, "source_metadata", None) or {}
                available_sources.append(
                    {
                        "id": str(source.id),
                        "name": source.name,
                        "alias": meta.get("alias") or source.name,
                        "description": meta.get("description")
                        or source.description
                        or "",
                        "branch": meta.get("branch") or "main",
                        "language": meta.get("language") or "Unknown",
                        "tags": meta.get("tags") or [],
                        "status": meta.get("status") or "healthy",
                        "lastFullIndex": meta.get("last_full_index"),
                        "lastIncremental": meta.get("last_incremental"),
                        "maintainers": meta.get("maintainers") or [],
                        "recommendedQuestions": meta.get("recommended_questions") or [],
                        "isActive": source.is_active,
                        "queryCount7d": counts.get(str(source.id), 0),
                        "nodeCount": meta.get("node_count"),
                        "relationCount": meta.get("relation_count"),
                    }
                )

            return available_sources

    except Exception as e:
        logger.error(f"获取可用知识源列表失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post(
    "/query/stream",
    summary="流式返回 GraphRAG 查询结果",
    description="以 Server-Sent Events 形式逐步推送查询上下文、状态与最终回答。",
)
async def stream_knowledge_query(
    request: StreamQueryRequest = Body(...),
    user=Depends(require_permission("/knowledge/query", "POST")),
):
    """
    流式查询端点，将后端事件转换为前端期望的 SSE 格式。

    前端期望的事件类型：
    - text: 文本块
    - entity: 关联实体
    - metadata: 元数据
    - done: 完成
    - error: 错误
    """

    async def event_generator():
        import time

        start_time = time.time()
        query_uuid = uuid.uuid4()
        query_id_str = str(query_uuid)
        persisted = False

        def _clamp_confidence(raw: Optional[Any]) -> float:
            if raw is None:
                return 0.0
            try:
                value = float(raw)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                return 0.0
            if value < 0.0:
                return 0.0
            if value > 1.0:
                return 1.0
            return value

        try:
            # 转换前端请求参数到后端格式
            source_uuids = None
            if request.source_ids:
                try:
                    source_uuids = [uuid.UUID(sid) for sid in request.source_ids]
                except ValueError:
                    error_event = {"message": "Invalid source_id format"}
                    yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                    return

            # 执行流式查询
            async for chunk in graph_rag_service.stream_query(
                request.question,
                source_ids=[str(sid) for sid in source_uuids] if source_uuids else None,
                timeout_seconds=request.timeout or 30,
                include_evidence=True,
                max_results=request.top_k or 10,
            ):
                chunk_type = chunk.get("type")

                # 处理不同类型的后端事件
                if chunk_type == "result":
                    # 后端返回最终结果，拆分为文本块
                    payload = chunk.get("payload", {})
                    answer = payload.get("answer", {})
                    summary = answer.get("summary", "")
                    related_entities = answer.get("related_entities", [])
                    evidence_list = answer.get("evidence", [])
                    next_actions = answer.get("next_actions", [])

                    # 将摘要分块发送
                    if summary:
                        words = summary.split()
                        chunk_size = 10
                        for i in range(0, len(words), chunk_size):
                            chunk_words = words[i : i + chunk_size]
                            text_chunk = " ".join(chunk_words)
                            if i + chunk_size < len(words):
                                text_chunk += " "

                            text_event = {"content": text_chunk}
                            yield f"event: text\ndata: {json.dumps(text_event, ensure_ascii=False)}\n\n"

                    # 发送关联实体
                    for entity_data in related_entities:
                        entity = {
                            "type": entity_data.get("type", "file"),
                            "name": entity_data.get("name", ""),
                            "importance": entity_data.get("importance", "medium"),
                            "detail": entity_data.get("detail", ""),
                            "link": entity_data.get("link"),
                        }
                        entity_event = {"entity": entity}
                        yield f"event: entity\ndata: {json.dumps(entity_event, ensure_ascii=False)}\n\n"
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    metadata_payload = {
                        "execution_time_ms": execution_time_ms,
                        "sources_queried": request.source_ids,
                        "confidence_score": _clamp_confidence(payload.get("confidence_score", 0.0)),
                        "retrieval_mode": request.retrieval_mode or "hybrid",
                        "from_cache": False,
                    }

                    metadata_event = {"data": metadata_payload}
                    yield f"event: metadata\ndata: {json.dumps(metadata_event, ensure_ascii=False)}\n\n"

                    if not persisted:
                        answer_payload = GraphRAGAnswerPayload.model_validate(
                            {
                                "summary": summary,
                                "related_entities": related_entities,
                                "evidence": evidence_list,
                                "next_actions": next_actions,
                            }
                        )

                        evidence_anchors = build_evidence_anchors(answer_payload)
                        response_model = GraphRAGQueryResponse(
                            answer=answer_payload,
                            confidence_score=_clamp_confidence(payload.get("confidence_score", 0.0)),
                            evidence_anchors=evidence_anchors,
                            raw_messages=payload.get("raw_messages"),
                            sources_queried=payload.get("sources_queried")
                            or request.source_ids
                            or [],
                            processing_time_ms=payload.get("processing_time_ms")
                            or execution_time_ms,
                            query_id=payload.get("query_id") or query_id_str,
                            issues=payload.get("issues"),
                        )

                        await cache_query_response(response_model)
                        await persist_successful_query(
                            user=user,
                            question=request.question,
                            source_ids=request.source_ids,
                            response=response_model,
                            processing_time_ms=response_model.processing_time_ms,
                            mode=request.retrieval_mode or "hybrid",
                        )
                        persisted = True

                    # 发送完成事件
                    done_event = {
                        "query_id": payload.get("query_id") or query_id_str,
                        "timestamp": dt.datetime.now().isoformat(),
                    }
                    yield f"event: done\ndata: {json.dumps(done_event, ensure_ascii=False)}\n\n"

                elif chunk_type == "error":
                    # 后端错误
                    error_event = {"message": chunk.get("message", "Unknown error")}
                    yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

                elif chunk_type == "timeout":
                    # 超时错误
                    error_event = {
                        "message": chunk.get("message", "Query timeout"),
                        "code": "TIMEOUT",
                    }
                    yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            logger.error(f"流式查询错误: {exc}")
            error_event = {"message": str(exc), "code": "QUERY_ERROR"}
            yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sessions",
    summary="最近提问记录",
    description="返回最近提问摘要列表。",
)
async def recent_sessions(
    user=Depends(require_permission("/knowledge/sessions", "GET")),
):
    try:
        from database import async_session_factory as _factory
        from sqlalchemy import select
        from database.models import KnowledgeQuery as _KQ

        async with _factory() as _s:
            result = await _s.execute(
                select(_KQ).order_by(_KQ.created_at.desc()).limit(20)
            )
            items = list(result.scalars().all())
            return [
                {
                    "query_id": str(i.id),
                    "source_id": str(i.source_id) if i.source_id else None,
                    "question": i.question,
                    "answer_summary": i.answer_summary,
                    "created_at": i.created_at.isoformat(),
                }
                for i in items
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    "/sources/{source_id}",
    summary="知识源详情",
    description="返回更详细的知识源信息。",
)
async def get_source_detail(source_id: uuid.UUID, user=Depends(current_active_user)):
    try:
        async with async_session_factory() as session:
            source_service = get_source_service(session)
            source = await source_service.get_source_by_id(source_id, include_jobs=True)
            if not source:
                raise HTTPException(status_code=404, detail="知识源不存在")
            meta = getattr(source, "source_metadata", None) or {}
            jobs = source.parse_jobs[:10] if getattr(source, "parse_jobs", None) else []
            return {
                "id": str(source.id),
                "name": source.name,
                "alias": meta.get("alias"),
                "branch": meta.get("branch"),
                "language": meta.get("language"),
                "tags": meta.get("tags"),
                "status": meta.get("status"),
                "isActive": source.is_active,
                "lastFullIndex": meta.get("last_full_index"),
                "lastIncremental": meta.get("last_incremental"),
                "recommendedQuestions": meta.get("recommended_questions"),
                "maintainers": meta.get("maintainers"),
                "recentJobs": [
                    {
                        "id": str(j.id),
                        "status": j.status,
                        "createdAt": j.created_at.isoformat() if j.created_at else None,
                        "completedAt": j.completed_at.isoformat()
                        if j.completed_at
                        else None,
                    }
                    for j in jobs
                ],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识源详情失败: {e}")
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
        # 获取基础统计信息
        stats = await neo4j_knowledge_service.get_statistics()

        # 添加额外的统计信息
        async with async_session_factory() as session:
            source_service = get_source_service(session)

            # 获取知识源统计
            sources, _ = await source_service.list_sources(page=1, size=1)
            active_sources = [s for s in sources if s.is_active]

            stats.update(
                {
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
                }
            )

        return stats

    except Exception as e:
        logger.error(f"获取知识图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
