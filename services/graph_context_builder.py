"""构建 GraphRAG 查询所需的结构化上下文。"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from loguru import logger
import jieba

from services.graph_service import Neo4jGraphService, graph_service
from services.neo4j_knowledge_service import Neo4jKnowledgeService, neo4j_knowledge_service


class GraphQueryIntent(str, Enum):
    """用户查询的意图分类。"""

    RECENT_CHANGES = "recent_changes"
    DEPENDENCY = "dependency_analysis"
    OWNERSHIP = "ownership"
    DEFAULT = "general"


INTENT_KEYWORDS = {
    GraphQueryIntent.RECENT_CHANGES: [
        "change",
        "changes",
        "修改",
        "变更",
        "最近",
        "commit",
        "update",
        "改动",
    ],
    GraphQueryIntent.DEPENDENCY: [
        "依赖",
        "dependency",
        "调用",
        "调用关系",
        "impact",
        "影响",
        "关系",
        "关联",
    ],
    GraphQueryIntent.OWNERSHIP: [
        "owner",
        "负责",
        "责任",
        "谁",
        "author",
        "maintainer",
        "负责人",
    ],
}


QUESTION_KEYWORD_REGEX = re.compile(r"[A-Za-z0-9_./-]+|[\u4e00-\u9fa5]+", re.UNICODE)


@dataclass
class GraphContext:
    """GraphRAG 所需的上下文封装。"""

    question: str
    intent: GraphQueryIntent
    graph_data: Dict[str, Any] = field(default_factory=dict)
    evidence_snippets: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


class GraphContextBuilder:
    """负责构建可供 LLM 使用的上下文数据。"""

    def __init__(
        self,
        graph_db: Neo4jGraphService | None = None,
        knowledge_service: Neo4jKnowledgeService | None = None,
    ) -> None:
        self.graph_db = graph_db or graph_service
        self.knowledge_service = knowledge_service or neo4j_knowledge_service or Neo4jKnowledgeService()
        self._graph_connected = asyncio.Lock()
        self._neo4j_ready = False

    async def build(self, question: str) -> GraphContext:
        intent = self._infer_intent(question)
        keywords = self._extract_keywords(question)

        context = GraphContext(question=question, intent=intent)

        graph_data, issues = await self._gather_graph_data(intent, keywords)
        context.graph_data = graph_data
        context.issues.extend(issues)

        snippets, snippet_issues = await self._gather_evidence_snippets(question, keywords)
        context.evidence_snippets = snippets
        context.issues.extend(snippet_issues)

        return context

    def _infer_intent(self, question: str) -> GraphQueryIntent:
        lowered = question.lower()
        for intent, tokens in INTENT_KEYWORDS.items():
            if any(token in lowered for token in tokens):
                return intent
        return GraphQueryIntent.DEFAULT

    def _extract_keywords(self, question: str) -> List[str]:
        # 优先使用 jieba 分词提取关键词，回退到正则方案
        keywords: List[str] = []
        try:
            segments = jieba.cut_for_search(question)
            for seg in segments:
                token = seg.strip()
                if len(token) < 2:
                    continue
                keywords.append(token.lower())
                if len(keywords) >= 5:
                    break
        except Exception as exc:
            logger.debug("jieba segmentation failed: {}", exc)

        if not keywords:
            candidates = QUESTION_KEYWORD_REGEX.findall(question)
            keywords = [kw.lower() for kw in candidates if len(kw) > 2][:5]

        return keywords

    async def _ensure_graph_ready(self) -> bool:
        if self._neo4j_ready:
            return True

        async with self._graph_connected:
            if self._neo4j_ready:
                return True
            try:
                connected = await self.graph_db.connect()
                self._neo4j_ready = connected
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Neo4j connection failed: {}", exc)
                self._neo4j_ready = False
        return self._neo4j_ready

    async def _gather_graph_data(
        self, intent: GraphQueryIntent, keywords: List[str]
    ) -> tuple[Dict[str, Any], List[str]]:
        issues: List[str] = []
        if not keywords:
            return {"files": [], "commits": [], "modules": [], "people": []}, [
                "无法从问题中提取关键词，图谱检索跳过。"
            ]

        ready = await self._ensure_graph_ready()
        if not ready:
            return {"files": [], "commits": [], "modules": [], "people": []}, [
                "Neo4j 未连接，返回空的图谱上下文。"
            ]

        try:
            if intent is GraphQueryIntent.RECENT_CHANGES:
                result = await self._query_recent_changes(keywords)
            elif intent is GraphQueryIntent.DEPENDENCY:
                result = await self._query_dependency_map(keywords)
            elif intent is GraphQueryIntent.OWNERSHIP:
                result = await self._query_ownership(keywords)
            else:
                result = await self._query_recent_changes(keywords)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Graph query failed: {}", exc)
            return {"files": [], "commits": [], "modules": [], "people": []}, [
                f"图谱查询失败: {exc}"
            ]

        return result, issues

    async def _query_recent_changes(
        self, keywords: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        query = """
        MATCH (f:File)
        WHERE ANY(keyword IN $keywords WHERE toLower(f.path) CONTAINS keyword OR toLower(coalesce(f.name, '')) CONTAINS keyword)
        OPTIONAL MATCH (f)<-[r:CHANGED_FILE|MODIFIED_FILE|UPDATED_FILE]-(c:Commit)
        OPTIONAL MATCH (c)-[:AUTHORED_BY]->(p:Person)
        OPTIONAL MATCH (f)<-[:OWNS_FILE|BELONGS_TO]-(m:Module)
        RETURN f.path AS file_path,
               coalesce(f.description, '') AS description,
               collect(DISTINCT {
                   id: coalesce(c.id, c.commit_id),
                   message: coalesce(c.message, ''),
                   timestamp: coalesce(c.timestamp, c.date, c.created_at, ''),
                   author: coalesce(p.name, p.email, '')
               })[0..5] AS commits,
               collect(DISTINCT coalesce(m.name, ''))[0..3] AS modules,
               collect(DISTINCT coalesce(p.name, p.email, ''))[0..3] AS people
        LIMIT 5
        """
        result = await self.graph_db.execute_cypher(query, {"keywords": keywords})
        data = []
        for record in result.raw_result or []:
            data.append(
                {
                    "path": record.get("file_path"),
                    "description": record.get("description") or "",
                    "commits": record.get("commits") or [],
                    "modules": [m for m in (record.get("modules") or []) if m],
                    "people": [p for p in (record.get("people") or []) if p],
                }
            )
        return {
            "files": data,
            "commits": [
                commit
                for file_entry in data
                for commit in file_entry.get("commits", [])
            ],
            "modules": list(
                {
                    module
                    for file_entry in data
                    for module in file_entry.get("modules", [])
                    if module
                }
            ),
            "people": list(
                {
                    person
                    for file_entry in data
                    for person in file_entry.get("people", [])
                    if person
                }
            ),
        }

    async def _query_dependency_map(
        self, keywords: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        query = """
        MATCH (source:File)-[rel:DEPENDS_ON|IMPORTS|USES]->(target:File)
        WHERE ANY(keyword IN $keywords WHERE toLower(source.path) CONTAINS keyword OR toLower(target.path) CONTAINS keyword)
        OPTIONAL MATCH (target)<-[:CHANGED_FILE|MODIFIED_FILE]-(c:Commit)
        RETURN source.path AS source_path,
               target.path AS target_path,
               type(rel) AS relationship,
               collect(DISTINCT {
                   id: coalesce(c.id, c.commit_id),
                   message: coalesce(c.message, '')
               })[0..3] AS commits
        LIMIT 10
        """
        result = await self.graph_db.execute_cypher(query, {"keywords": keywords})
        dependencies = []
        commits: List[Dict[str, Any]] = []
        for record in result.raw_result or []:
            dependencies.append(
                {
                    "from": record.get("source_path"),
                    "to": record.get("target_path"),
                    "relationship": record.get("relationship"),
                }
            )
            commits.extend(record.get("commits") or [])
        return {
            "files": [],
            "commits": commits[:5],
            "modules": [],
            "people": [],
            "dependencies": dependencies,
        }

    async def _query_ownership(
        self, keywords: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        query = """
        MATCH (p:Person)-[:OWNS|MAINTAINS|AUTHORED]->(n)
        WHERE ANY(keyword IN $keywords WHERE toLower(coalesce(n.name, '')) CONTAINS keyword OR toLower(coalesce(n.path, '')) CONTAINS keyword)
        RETURN coalesce(n.path, n.name) AS entity,
               labels(n) AS labels,
               collect(DISTINCT {
                   person: coalesce(p.name, p.email),
                   role: coalesce(p.role, '')
               })[0..5] AS owners
        LIMIT 10
        """
        result = await self.graph_db.execute_cypher(query, {"keywords": keywords})
        owners = []
        people: List[str] = []
        for record in result.raw_result or []:
            owners.append(
                {
                    "entity": record.get("entity"),
                    "labels": record.get("labels") or [],
                    "owners": record.get("owners") or [],
                }
            )
            for owner in record.get("owners") or []:
                if owner.get("person"):
                    people.append(owner["person"])

        return {
            "files": [],
            "commits": [],
            "modules": owners,
            "people": list(dict.fromkeys(people)),
        }

    async def _gather_evidence_snippets(
        self, question: str, keywords: List[str]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        issues: List[str] = []
        try:
            if not self.knowledge_service._initialized:  # noqa: SLF001 - internal guard
                await self.knowledge_service.initialize()

            search_result = await self.knowledge_service.search_similar_nodes(
                query=question,
                top_k=5,
            )
            if not search_result.get("success"):
                issues.append(
                    f"向量检索失败: {search_result.get('error', 'unknown error')}"
                )
                return [], issues

            snippets = []
            for item in search_result.get("results", []):
                snippets.append(
                    {
                        "id": item.get("node_id"),
                        "text": item.get("text"),
                        "metadata": item.get("metadata", {}),
                        "score": item.get("score"),
                    }
                )
            return snippets, issues
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Embedding retrieval failed: {}", exc)
            issues.append(f"证据片段检索失败: {exc}")
            return [], issues
