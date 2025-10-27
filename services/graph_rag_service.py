"""高层 GraphRAG 查询编排服务。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from services.graph_context_builder import GraphContext, GraphContextBuilder, GraphQueryIntent
from services.neo4j_knowledge_service import Neo4jKnowledgeService


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


class GraphRAGService:
    """组合图谱上下文、向量检索与 LLM，生成结构化回答。"""

    def __init__(
        self,
        context_builder: GraphContextBuilder | None = None,
        knowledge_service: Neo4jKnowledgeService | None = None,
    ) -> None:
        self.context_builder = context_builder or GraphContextBuilder()
        self.knowledge_service = knowledge_service or self.context_builder.knowledge_service
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

    def _build_related_entities(
        self, context: GraphContext, *, max_results: int
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        for file_entry in context.graph_data.get("files", [])[:max_results]:
            entities.append(
                {
                    "type": "file",
                    "name": file_entry.get("path"),
                    "importance": "high" if file_entry.get("commits") else "medium",
                    "detail": file_entry.get("description") or "",
                    "link": None,
                }
            )

        for commit in context.graph_data.get("commits", [])[:max_results]:
            entities.append(
                {
                    "type": "commit",
                    "name": commit.get("id"),
                    "importance": "high",
                    "detail": commit.get("message") or "",
                    "author": commit.get("author"),
                    "link": None,
                }
            )

        for module in context.graph_data.get("modules", [])[:max_results]:
            if isinstance(module, dict):
                entities.append(
                    {
                        "type": "module",
                        "name": module.get("name") or module.get("entity"),
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
