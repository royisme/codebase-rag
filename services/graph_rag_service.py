"""高层 GraphRAG 查询编排服务。"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from services.graph_context_builder import GraphContext, GraphContextBuilder, GraphQueryIntent
from services.neo4j_knowledge_service import Neo4jKnowledgeService, neo4j_knowledge_service
from config import settings
from pathlib import Path
import json


@dataclass
class GraphRAGAnswer:
    summary: str
    related_entities: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)


@dataclass
class GraphRAGResult:
    answer: GraphRAGAnswer
    confidence_score: float
    raw_messages: Optional[List[Dict[str, Any]]] = None
    sources_queried: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    query_id: Optional[str] = None
    issues: List[str] = field(default_factory=list)


class GraphRAGTimeoutError(Exception):
    """Downstream LLM 调用超时。"""

    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


class GraphRAGQueryError(Exception):
    """Downstream LLM/Graph 查询失败。"""

    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


class GraphRAGService:
    """组合图谱上下文、向量检索与 LLM，生成结构化回答。"""

    def __init__(
        self,
        context_builder: GraphContextBuilder | None = None,
        knowledge_service: Neo4jKnowledgeService | None = None,
    ) -> None:
        # Prefer shared singleton instance to avoid repeated initialization
        if knowledge_service is not None:
            self.knowledge_service = knowledge_service
        else:
            self.knowledge_service = neo4j_knowledge_service or Neo4jKnowledgeService()

        if context_builder is not None:
            self.context_builder = context_builder
        else:
            self.context_builder = GraphContextBuilder(knowledge_service=self.knowledge_service)
        self._init_lock = asyncio.Lock()

    async def query(
        self,
        question: str,
        *,
        source_ids: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        include_evidence: bool = True,
        max_results: int = 10,
    ) -> GraphRAGResult:
        context = await self.context_builder.build(question)
        llm_payload = await self._run_llm_query(
            question,
            source_ids=source_ids,
            timeout_seconds=timeout_seconds,
            include_evidence=include_evidence,
        )

        if not llm_payload.get("success", True):
            error_code = llm_payload.get("error") or "UNKNOWN_ERROR"
            if error_code == "TIMEOUT":
                raise GraphRAGTimeoutError(
                    llm_payload.get("message") or "LLM 请求超时。",
                    llm_payload,
                )
            raise GraphRAGQueryError(
                llm_payload.get("message") or error_code,
                llm_payload,
            )

        answer = self._compose_answer(
            llm_payload=llm_payload,
            context=context,
            max_results=max_results,
        )

        confidence = llm_payload.get("confidence_score")
        if confidence is None:
            confidence = self._estimate_confidence(answer, context)

        return GraphRAGResult(
            answer=answer,
            confidence_score=float(confidence),
            raw_messages=llm_payload.get("source_nodes"),
            sources_queried=[
                str(s) for s in (llm_payload.get("sources_queried") or source_ids or [])
            ],
            processing_time_ms=llm_payload.get("processing_time_ms", 0),
            query_id=llm_payload.get("query_id"),
            issues=context.issues,
        )

    async def _run_llm_query(
        self,
        question: str,
        *,
        source_ids: Optional[List[str]],
        timeout_seconds: int,
        include_evidence: bool,
    ) -> Dict[str, Any]:
        # Demo fallback
        if settings.graphrag_use_demo:
            try:
                demo = self._demo_query(question, source_ids=source_ids, include_evidence=include_evidence)
                demo.setdefault("success", True)
                return demo
            except Exception as exc:  # pragma: no cover
                logger.warning("Demo provider failed: {}", exc)
        try:
            if not self.knowledge_service._initialized:  # noqa: SLF001 - guard
                async with self._init_lock:
                    if not self.knowledge_service._initialized:  # noqa: SLF001
                        await self.knowledge_service.initialize()

            result = await self.knowledge_service.query(
                question=question,
                mode="hybrid",
                max_results=10,
                include_evidence=include_evidence,
                source_ids=source_ids,
            )
            result.setdefault("success", True)
            if not result.get("success", True):
                error_code = result.get("error") or "UNKNOWN_ERROR"
                if error_code == "TIMEOUT":
                    raise GraphRAGTimeoutError(
                        result.get("message") or "LLM 请求超时。",
                        result,
                    )
                raise GraphRAGQueryError(
                    result.get("message") or error_code,
                    result,
                )
            return result
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("LLM 查询失败: {}", exc)
            return {
                "success": False,
                "answer": "抱歉，目前无法获取答案，请稍后再试。",
                "error": str(exc),
                "evidence": [],
                "sources_queried": source_ids or [],
                "processing_time_ms": 0,
            }

    def _compose_answer(
        self,
        *,
        llm_payload: Dict[str, Any],
        context: GraphContext,
        max_results: int,
    ) -> GraphRAGAnswer:
        summary = llm_payload.get("answer") or "暂时没有找到相关信息。"
        entities = self._build_related_entities(context, max_results=max_results)
        evidence = self._build_evidence(llm_payload, context, max_results=max_results)
        next_actions = self._suggest_next_actions(context)

        if not evidence and context.evidence_snippets:
            next_actions.append("尝试换个提问角度或提供更具体的关键字。")

        return GraphRAGAnswer(
            summary=summary.strip(),
            related_entities=entities,
            evidence=evidence,
            next_actions=list(dict.fromkeys(next_actions)),
        )

    async def stream_query(
        self,
        question: str,
        *,
        source_ids: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        include_evidence: bool = True,
        max_results: int = 10,
        session_id: Optional[str] = None,
    ):
        """Stream GraphRAG query with true token-level streaming.
        
        Yields events with type: text_delta, status, entity, metadata, done, error
        """
        import datetime as dt
        import time
        
        # 性能监控：记录各阶段耗时
        perf_start = time.perf_counter()
        stage_times = {}
        
        start_time = dt.datetime.now(dt.timezone.utc)
        accumulated_summary = ""
        entities_collected = []
        
        logger.info(f"[PERF] Stream query started: {question[:50]}...")
        
        # Status: building context
        yield {
            "type": "status",
            "stage": "context",
            "message": "正在构建查询上下文…",
        }
        
        try:
            # Build context
            context_start = time.perf_counter()
            logger.debug(f"[PERF] Starting context building...")
            
            context = await self.context_builder.build(question)
            
            context_time = time.perf_counter() - context_start
            stage_times['context_build'] = context_time
            logger.info(f"[PERF] Context built in {context_time:.2f}s (nodes={len(context.graph_data.get('nodes', []))}, edges={len(context.graph_data.get('edges', []))})")
            
            # Status: querying LLM
            yield {
                "type": "status",
                "stage": "llm",
                "message": "正在生成回答…",
            }
            
            # Ensure service is initialized
            init_start = time.perf_counter()
            if not self.knowledge_service._initialized:  # noqa: SLF001
                logger.debug(f"[PERF] Knowledge service not initialized, initializing...")
                async with self._init_lock:
                    if not self.knowledge_service._initialized:  # noqa: SLF001
                        await self.knowledge_service.initialize()
                init_time = time.perf_counter() - init_start
                stage_times['service_init'] = init_time
                logger.info(f"[PERF] Service initialized in {init_time:.2f}s")
            
            # Stream from knowledge service
            stream_start = time.perf_counter()
            first_token_received = False
            token_count = 0
            
            logger.debug(f"[PERF] Starting LLM stream...")
            
            async for event in self.knowledge_service.stream_query(
                question,
                mode="hybrid",
                max_results=max_results,
                include_evidence=include_evidence,
                source_ids=[uuid.UUID(sid) for sid in source_ids] if source_ids else None,
            ):
                event_type = event.get("type")
                
                if event_type == "text_delta":
                    # 记录首包时间
                    if not first_token_received:
                        first_token_time = time.perf_counter() - stream_start
                        stage_times['first_token'] = first_token_time
                        logger.info(f"[PERF] First token received in {first_token_time:.2f}s")
                        first_token_received = True
                    
                    token_count += 1
                    # Forward text delta directly
                    accumulated_summary += event.get("content", "")
                    yield {
                        "type": "text_delta",
                        "content": event.get("content", ""),
                    }
                
                elif event_type == "metadata":
                    # Forward metadata
                    yield {
                        "type": "metadata",
                        "confidence_score": event.get("confidence_score"),
                        "execution_time_ms": event.get("execution_time_ms"),
                        "sources_queried": event.get("sources_queried", []),
                        "retrieval_mode": event.get("retrieval_mode"),
                    }
                
                elif event_type == "evidence":
                    # Store evidence for entity extraction (simplified)
                    pass
                
                elif event_type == "error":
                    # Forward error
                    yield event
                    return
                
                elif event_type == "done":
                    # 记录总耗时
                    total_time = time.perf_counter() - perf_start
                    stage_times['total'] = total_time
                    stage_times['llm_streaming'] = time.perf_counter() - stream_start
                    stage_times['token_count'] = token_count
                    
                    # 输出性能摘要
                    logger.info(f"[PERF] Stream query completed in {total_time:.2f}s")
                    logger.info(f"[PERF] Performance breakdown:")
                    logger.info(f"  - Context build: {stage_times.get('context_build', 0):.2f}s")
                    logger.info(f"  - Service init: {stage_times.get('service_init', 0):.2f}s")
                    logger.info(f"  - First token: {stage_times.get('first_token', 0):.2f}s")
                    logger.info(f"  - LLM streaming: {stage_times.get('llm_streaming', 0):.2f}s")
                    logger.info(f"  - Tokens received: {token_count}")
                    if token_count > 0 and stage_times.get('llm_streaming', 0) > 0:
                        tokens_per_sec = token_count / stage_times['llm_streaming']
                        logger.info(f"  - Streaming rate: {tokens_per_sec:.1f} tokens/s")
                    
                    # Extract entities from context after streaming
                    entity_start = time.perf_counter()
                    entities_collected = self._build_related_entities(
                        context, max_results=max_results
                    )
                    entity_time = time.perf_counter() - entity_start
                    logger.debug(f"[PERF] Entity extraction took {entity_time:.2f}s")
                    
                    # Emit entities
                    for entity_dict in entities_collected:
                        yield {
                            "type": "entity",
                            "entity": entity_dict,
                        }
                    
                    # Generate next actions
                    next_actions = self._suggest_next_actions(context)
                    
                    # Calculate final processing time
                    processing_time_ms = int(
                        (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds() * 1000
                    )
                    
                    # Emit done event
                    yield {
                        "type": "done",
                        "query_id": event.get("query_id") or str(uuid.uuid4()),
                        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "summary": accumulated_summary,
                        "next_actions": next_actions,
                        "confidence_score": event.get("confidence_score"),
                        "sources_queried": event.get("sources_queried", []),
                        "processing_time_ms": processing_time_ms,
                    }
                    return
        
        except asyncio.TimeoutError:
            processing_time_ms = int(
                (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds() * 1000
            )
            yield {
                "type": "error",
                "message": "查询超时，请尝试简化问题或增加超时时间。",
                "code": "TIMEOUT",
                "processing_time_ms": processing_time_ms,
            }
        except Exception as exc:
            processing_time_ms = int(
                (dt.datetime.now(dt.timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"Stream query failed: {exc}")
            yield {
                "type": "error",
                "message": str(exc),
                "code": "PROCESSING_ERROR",
                "processing_time_ms": processing_time_ms,
            }

    def _demo_query(self, question: str, *, source_ids: Optional[List[str]], include_evidence: bool) -> Dict[str, Any]:
        base = Path(settings.graphrag_demo_answers_path)
        files = []
        if source_ids:
            for sid in source_ids:
                files.append(base / f"{sid}.json")
        files.append(base / "default.json")
        for fp in files:
            try:
                if fp.is_file():
                    payload = json.loads(fp.read_text(encoding="utf-8"))
                    answer = payload.get("answer") or payload.get("summary") or "这是一个演示回答。"
                    evidence = payload.get("evidence", []) if include_evidence else []
                    return {
                        "success": True,
                        "answer": answer,
                        "source_nodes": [],
                        "query_mode": "demo",
                        "confidence_score": float(payload.get("confidence", 0.75)),
                        "evidence": evidence,
                        "sources_queried": source_ids or [],
                        "processing_time_ms": int(payload.get("processing_time_ms", 50)),
                    }
            except Exception:
                continue
        return {
            "success": True,
            "answer": "这是一个演示回答（无匹配 demo 数据）。",
            "source_nodes": [],
            "query_mode": "demo",
            "confidence_score": 0.6,
            "evidence": [] if not include_evidence else [],
            "sources_queried": source_ids or [],
            "processing_time_ms": 30,
        }

    def _build_related_entities(
        self, context: GraphContext, *, max_results: int
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        for file_entry in context.graph_data.get("files", [])[:max_results]:
            file_path = file_entry.get("path")
            
            # 跳过没有路径的文件
            if not file_path or file_path == "-":
                continue
                
            entities.append(
                {
                    "type": "file",
                    "name": file_path,
                    "importance": "high" if file_entry.get("commits") else "medium",
                    "detail": file_entry.get("description") or "",
                    "link": None,
                }
            )

        for commit in context.graph_data.get("commits", [])[:max_results]:
            commit_id = commit.get("id")
            commit_message = commit.get("message") or ""
            
            # 跳过没有 ID 或消息的 commit
            if not commit_id or not commit_message or commit_message == "-":
                continue
                
            entities.append(
                {
                    "type": "commit",
                    "name": commit_id,
                    "importance": "high",
                    "detail": commit_message,
                    "author": commit.get("author"),
                    "link": None,
                }
            )

        for module in context.graph_data.get("modules", [])[:max_results]:
            if isinstance(module, dict):
                module_name = module.get("name") or module.get("entity")
                
                # 跳过没有名称的模块
                if not module_name or module_name == "-":
                    continue
                    
                entities.append(
                    {
                        "type": "module",
                        "name": module_name,
                        "importance": "medium",
                        "detail": ", ".join(
                            owner.get("person", "")
                            for owner in module.get("owners", [])
                            if owner.get("person")
                        ),
                        "link": None,
                    }
                )
            elif isinstance(module, str):
                # 跳过空字符串或 "-"
                if not module or module == "-":
                    continue
                    
                entities.append(
                    {
                        "type": "module",
                        "name": module,
                        "importance": "medium",
                        "detail": "",
                        "link": None,
                    }
                )

        for person in context.graph_data.get("people", [])[:max_results]:
            entities.append(
                {
                    "type": "person",
                    "name": person,
                    "importance": "medium",
                    "detail": "相关负责人",
                    "link": None,
                }
            )

        for dependency in context.graph_data.get("dependencies", [])[:max_results]:
            entities.append(
                {
                    "type": "dependency",
                    "name": f"{dependency.get('from')} -> {dependency.get('to')}",
                    "importance": "medium",
                    "detail": f"关系: {dependency.get('relationship')}",
                    "link": None,
                }
            )

        return entities

    def _build_evidence(
        self,
        llm_payload: Dict[str, Any],
        context: GraphContext,
        *,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []

        for item in llm_payload.get("evidence", [])[:max_results]:
            evidence.append(
                {
                    "id": item.get("id") or item.get("source_id"),
                    "snippet": item.get("content_snippet") or item.get("content"),
                    "source_type": item.get("source_type") or "graph",
                    "source_ref": item.get("source_id"),
                    "score": item.get("relevance_score"),
                }
            )

        if evidence:
            return evidence

        for idx, snippet in enumerate(context.evidence_snippets[:max_results], start=1):
            evidence.append(
                {
                    "id": snippet.get("id") or f"E{idx}",
                    "snippet": snippet.get("text"),
                    "source_type": snippet.get("metadata", {}).get("source_type", "vector"),
                    "source_ref": snippet.get("metadata", {}).get("source_ref"),
                    "score": snippet.get("score"),
                }
            )

        return evidence

    def _suggest_next_actions(self, context: GraphContext) -> List[str]:
        suggestions: List[str] = []
        if context.intent is GraphQueryIntent.RECENT_CHANGES:
            suggestions.append("查看这些文件最近的提交详情。")
            suggestions.append("继续询问与相关模块或人员的最新讨论。")
        elif context.intent is GraphQueryIntent.DEPENDENCY:
            suggestions.append("深入了解依赖链上游/下游模块的状态。")
            suggestions.append("确认依赖变更是否需要额外测试。")
        elif context.intent is GraphQueryIntent.OWNERSHIP:
            suggestions.append("联系相关负责人确认变更计划。")
        else:
            suggestions.append("尝试给出更具体的函数或文件名以获取精准结果。")

        if context.evidence_snippets:
            suggestions.append("读取证据片段，确认回答是否符合预期。")

        return suggestions

    def _estimate_confidence(self, answer: GraphRAGAnswer, context: GraphContext) -> float:
        if context.evidence_snippets:
            top_score = context.evidence_snippets[0].get("score")
            if isinstance(top_score, (int, float)):
                return max(0.0, min(1.0, float(top_score)))
        if answer.related_entities:
            return 0.7
        return 0.3
