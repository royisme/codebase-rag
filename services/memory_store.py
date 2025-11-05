"""
Memory Store Service - Project Knowledge Persistence System

Provides long-term project memory for AI agents to maintain:
- Design decisions and rationale
- Team preferences and conventions
- Experiences (problems and solutions)
- Future plans and todos

Supports both manual curation and automatic extraction (future).
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from loguru import logger

from neo4j import AsyncGraphDatabase
from config import settings


class MemoryStore:
    """
    Store and retrieve project memories in Neo4j.

    Memory Types:
    - decision: Architecture choices, tech stack selection
    - preference: Coding style, tool preferences
    - experience: Problems encountered and solutions
    - convention: Team rules, naming conventions
    - plan: Future improvements, todos
    - note: Other important information
    """

    MemoryType = Literal["decision", "preference", "experience", "convention", "plan", "note"]

    def __init__(self):
        self.driver = None
        self._initialized = False
        self.connection_timeout = settings.connection_timeout
        self.operation_timeout = settings.operation_timeout

    async def initialize(self) -> bool:
        """Initialize Neo4j connection and create constraints/indexes"""
        try:
            logger.info("Initializing Memory Store...")

            # Create Neo4j driver
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password)
            )

            # Test connection
            await self.driver.verify_connectivity()

            # Create constraints and indexes
            await self._create_schema()

            self._initialized = True
            logger.success("Memory Store initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Memory Store: {e}")
            return False

    async def _create_schema(self):
        """Create Neo4j constraints and indexes for Memory nodes"""
        async with self.driver.session(database=settings.neo4j_database) as session:
            # Create constraint for Memory.id
            try:
                await session.run(
                    "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS "
                    "FOR (m:Memory) REQUIRE m.id IS UNIQUE"
                )
            except Exception:
                pass  # Constraint may already exist

            # Create constraint for Project.id
            try:
                await session.run(
                    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS "
                    "FOR (p:Project) REQUIRE p.id IS UNIQUE"
                )
            except Exception:
                pass

            # Create fulltext index for memory search
            try:
                await session.run(
                    "CREATE FULLTEXT INDEX memory_search IF NOT EXISTS "
                    "FOR (m:Memory) ON EACH [m.title, m.content, m.reason, m.tags]"
                )
            except Exception:
                pass

            logger.info("Memory Store schema created/verified")

    async def add_memory(
        self,
        project_id: str,
        memory_type: MemoryType,
        title: str,
        content: str,
        reason: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        related_refs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a new memory to the project knowledge base.

        Args:
            project_id: Project identifier
            memory_type: Type of memory (decision/preference/experience/convention/plan/note)
            title: Short title/summary
            content: Detailed content
            reason: Rationale or explanation (optional)
            tags: Tags for categorization (optional)
            importance: Importance score 0-1 (default 0.5)
            related_refs: List of ref:// handles this memory relates to (optional)
            metadata: Additional metadata (optional)

        Returns:
            Result dict with success status and memory_id
        """
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            memory_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # Ensure project exists
            await self._ensure_project_exists(project_id)

            async with self.driver.session(database=settings.neo4j_database) as session:
                # Create Memory node and link to Project
                result = await session.run(
                    """
                    MATCH (p:Project {id: $project_id})
                    CREATE (m:Memory {
                        id: $memory_id,
                        type: $memory_type,
                        title: $title,
                        content: $content,
                        reason: $reason,
                        tags: $tags,
                        importance: $importance,
                        created_at: $created_at,
                        updated_at: $updated_at,
                        metadata: $metadata
                    })
                    CREATE (m)-[:BELONGS_TO]->(p)
                    RETURN m.id as id
                    """,
                    project_id=project_id,
                    memory_id=memory_id,
                    memory_type=memory_type,
                    title=title,
                    content=content,
                    reason=reason,
                    tags=tags or [],
                    importance=importance,
                    created_at=now,
                    updated_at=now,
                    metadata=metadata or {}
                )

                # Link to related code references if provided
                if related_refs:
                    await self._link_related_refs(memory_id, related_refs)

                logger.info(f"Added memory '{title}' (type: {memory_type}, id: {memory_id})")

                return {
                    "success": True,
                    "memory_id": memory_id,
                    "type": memory_type,
                    "title": title
                }

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _ensure_project_exists(self, project_id: str):
        """Ensure project node exists, create if not"""
        async with self.driver.session(database=settings.neo4j_database) as session:
            await session.run(
                """
                MERGE (p:Project {id: $project_id})
                ON CREATE SET p.created_at = $created_at,
                              p.name = $project_id
                """,
                project_id=project_id,
                created_at=datetime.utcnow().isoformat()
            )

    async def _link_related_refs(self, memory_id: str, refs: List[str]):
        """Link memory to related code references (ref:// handles)"""
        async with self.driver.session(database=settings.neo4j_database) as session:
            for ref in refs:
                # Parse ref:// handle to extract node information
                # ref://file/path/to/file.py or ref://symbol/function_name
                if ref.startswith("ref://file/"):
                    file_path = ref.replace("ref://file/", "").split("#")[0]
                    await session.run(
                        """
                        MATCH (m:Memory {id: $memory_id})
                        MATCH (f:File {path: $file_path})
                        MERGE (m)-[:RELATES_TO]->(f)
                        """,
                        memory_id=memory_id,
                        file_path=file_path
                    )
                elif ref.startswith("ref://symbol/"):
                    symbol_name = ref.replace("ref://symbol/", "").split("#")[0]
                    await session.run(
                        """
                        MATCH (m:Memory {id: $memory_id})
                        MATCH (s:Symbol {name: $symbol_name})
                        MERGE (m)-[:RELATES_TO]->(s)
                        """,
                        memory_id=memory_id,
                        symbol_name=symbol_name
                    )

    async def search_memories(
        self,
        project_id: str,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_importance: float = 0.0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search memories with various filters.

        Args:
            project_id: Project identifier
            query: Search query (searches title, content, reason, tags)
            memory_type: Filter by memory type
            tags: Filter by tags (any match)
            min_importance: Minimum importance score
            limit: Maximum number of results

        Returns:
            Result dict with memories list
        """
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            async with self.driver.session(database=settings.neo4j_database) as session:
                # Build query dynamically based on filters
                where_clauses = ["(m)-[:BELONGS_TO]->(:Project {id: $project_id})"]
                params = {
                    "project_id": project_id,
                    "min_importance": min_importance,
                    "limit": limit
                }

                if memory_type:
                    where_clauses.append("m.type = $memory_type")
                    params["memory_type"] = memory_type

                if tags:
                    where_clauses.append("ANY(tag IN $tags WHERE tag IN m.tags)")
                    params["tags"] = tags

                where_clause = " AND ".join(where_clauses)

                # Use fulltext search if query provided, otherwise simple filter
                if query:
                    cypher = f"""
                    CALL db.index.fulltext.queryNodes('memory_search', $query)
                    YIELD node as m, score
                    WHERE {where_clause} AND m.importance >= $min_importance
                    RETURN m, score
                    ORDER BY score DESC, m.importance DESC, m.created_at DESC
                    LIMIT $limit
                    """
                    params["query"] = query
                else:
                    cypher = f"""
                    MATCH (m:Memory)
                    WHERE {where_clause} AND m.importance >= $min_importance
                    RETURN m, 1.0 as score
                    ORDER BY m.importance DESC, m.created_at DESC
                    LIMIT $limit
                    """

                result = await session.run(cypher, **params)
                records = await result.data()

                memories = []
                for record in records:
                    m = record['m']
                    memories.append({
                        "id": m['id'],
                        "type": m['type'],
                        "title": m['title'],
                        "content": m['content'],
                        "reason": m.get('reason'),
                        "tags": m.get('tags', []),
                        "importance": m.get('importance', 0.5),
                        "created_at": m.get('created_at'),
                        "updated_at": m.get('updated_at'),
                        "search_score": record.get('score', 1.0)
                    })

                logger.info(f"Found {len(memories)} memories for query: {query}")

                return {
                    "success": True,
                    "memories": memories,
                    "total_count": len(memories)
                }

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """Get a specific memory by ID with related references"""
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run(
                    """
                    MATCH (m:Memory {id: $memory_id})
                    OPTIONAL MATCH (m)-[:RELATES_TO]->(related)
                    RETURN m,
                           collect(DISTINCT {type: labels(related)[0],
                                            path: related.path,
                                            name: related.name}) as related_refs
                    """,
                    memory_id=memory_id
                )

                record = await result.single()
                if not record:
                    return {
                        "success": False,
                        "error": "Memory not found"
                    }

                m = record['m']
                related_refs = [r for r in record['related_refs'] if r.get('path') or r.get('name')]

                return {
                    "success": True,
                    "memory": {
                        "id": m['id'],
                        "type": m['type'],
                        "title": m['title'],
                        "content": m['content'],
                        "reason": m.get('reason'),
                        "tags": m.get('tags', []),
                        "importance": m.get('importance', 0.5),
                        "created_at": m.get('created_at'),
                        "updated_at": m.get('updated_at'),
                        "metadata": m.get('metadata', {}),
                        "related_refs": related_refs
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_memory(
        self,
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        reason: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update an existing memory"""
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            # Build SET clause dynamically
            updates = []
            params = {"memory_id": memory_id, "updated_at": datetime.utcnow().isoformat()}

            if title is not None:
                updates.append("m.title = $title")
                params["title"] = title
            if content is not None:
                updates.append("m.content = $content")
                params["content"] = content
            if reason is not None:
                updates.append("m.reason = $reason")
                params["reason"] = reason
            if tags is not None:
                updates.append("m.tags = $tags")
                params["tags"] = tags
            if importance is not None:
                updates.append("m.importance = $importance")
                params["importance"] = importance

            if not updates:
                return {
                    "success": False,
                    "error": "No updates provided"
                }

            updates.append("m.updated_at = $updated_at")
            set_clause = ", ".join(updates)

            async with self.driver.session(database=settings.neo4j_database) as session:
                await session.run(
                    f"MATCH (m:Memory {{id: $memory_id}}) SET {set_clause}",
                    **params
                )

                logger.info(f"Updated memory {memory_id}")

                return {
                    "success": True,
                    "memory_id": memory_id
                }

        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory (hard delete - permanently removes from database)"""
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            async with self.driver.session(database=settings.neo4j_database) as session:
                # Hard delete: permanently remove the node and all its relationships
                result = await session.run(
                    """
                    MATCH (m:Memory {id: $memory_id})
                    DETACH DELETE m
                    RETURN count(m) as deleted_count
                    """,
                    memory_id=memory_id
                )

                record = await result.single()
                if not record or record["deleted_count"] == 0:
                    return {
                        "success": False,
                        "error": "Memory not found"
                    }

                logger.info(f"Hard deleted memory {memory_id}")

                return {
                    "success": True,
                    "memory_id": memory_id
                }

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def supersede_memory(
        self,
        old_memory_id: str,
        new_memory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new memory that supersedes an old one.
        Useful when a decision is changed or improved.
        """
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            # Get old memory to inherit project_id
            old_result = await self.get_memory(old_memory_id)
            if not old_result.get("success"):
                return old_result

            # Get project_id from old memory
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run(
                    """
                    MATCH (old:Memory {id: $old_id})-[:BELONGS_TO]->(p:Project)
                    RETURN p.id as project_id
                    """,
                    old_id=old_memory_id
                )
                record = await result.single()
                project_id = record['project_id']

            # Create new memory
            new_result = await self.add_memory(
                project_id=project_id,
                **new_memory_data
            )

            if not new_result.get("success"):
                return new_result

            new_memory_id = new_result['memory_id']

            # Create SUPERSEDES relationship
            async with self.driver.session(database=settings.neo4j_database) as session:
                await session.run(
                    """
                    MATCH (new:Memory {id: $new_id})
                    MATCH (old:Memory {id: $old_id})
                    CREATE (new)-[:SUPERSEDES]->(old)
                    SET old.superseded_by = $new_id,
                        old.superseded_at = $superseded_at
                    """,
                    new_id=new_memory_id,
                    old_id=old_memory_id,
                    superseded_at=datetime.utcnow().isoformat()
                )

            logger.info(f"Memory {new_memory_id} supersedes {old_memory_id}")

            return {
                "success": True,
                "new_memory_id": new_memory_id,
                "old_memory_id": old_memory_id
            }

        except Exception as e:
            logger.error(f"Failed to supersede memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """Get a summary of all memories for a project, organized by type"""
        if not self._initialized:
            raise Exception("Memory Store not initialized")

        try:
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run(
                    """
                    MATCH (m:Memory)-[:BELONGS_TO]->(p:Project {id: $project_id})
                    RETURN m.type as type, count(*) as count,
                           collect({id: m.id, title: m.title, importance: m.importance}) as memories
                    ORDER BY type
                    """,
                    project_id=project_id
                )

                records = await result.data()

                summary = {
                    "project_id": project_id,
                    "total_memories": sum(r['count'] for r in records),
                    "by_type": {}
                }

                for record in records:
                    memory_type = record['type']
                    summary["by_type"][memory_type] = {
                        "count": record['count'],
                        "top_memories": sorted(
                            record['memories'],
                            key=lambda x: x.get('importance', 0.5),
                            reverse=True
                        )[:5]  # Top 5 by importance
                    }

                return {
                    "success": True,
                    "summary": summary
                }

        except Exception as e:
            logger.error(f"Failed to get project summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Memory Store closed")


# Global instance (singleton pattern)
memory_store = MemoryStore()
