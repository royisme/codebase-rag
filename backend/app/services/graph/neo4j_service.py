"""
Neo4j service for graph operations (v0.2)
Handles connection, schema initialization, and basic queries
"""
from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver, Session
from loguru import logger
import os


class Neo4jService:
    """Neo4j database service"""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j service"""
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            self._connected = False
            logger.info("Neo4j connection closed")
    
    def initialize_schema(self) -> bool:
        """Initialize Neo4j schema from schema.cypher file"""
        try:
            schema_file = os.path.join(
                os.path.dirname(__file__),
                "schema.cypher"
            )
            
            with open(schema_file, 'r') as f:
                schema_commands = f.read()
            
            # Split by semicolon and filter out comments
            commands = [
                cmd.strip() 
                for cmd in schema_commands.split(';')
                if cmd.strip() and not cmd.strip().startswith('//')
            ]
            
            with self.driver.session(database=self.database) as session:
                for command in commands:
                    if command:
                        try:
                            session.run(command)
                            logger.debug(f"Executed: {command[:50]}...")
                        except Exception as e:
                            logger.warning(f"Schema command failed (may already exist): {e}")
            
            logger.info("Neo4j schema initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False
    
    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a write query"""
        if not self._connected:
            return {"success": False, "error": "Not connected to Neo4j"}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                summary = result.consume()
                return {
                    "success": True,
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                    "properties_set": summary.counters.properties_set
                }
        except Exception as e:
            logger.error(f"Write query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a read query"""
        if not self._connected:
            return {"success": False, "error": "Not connected to Neo4j"}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
                return {
                    "success": True,
                    "records": records,
                    "count": len(records)
                }
        except Exception as e:
            logger.error(f"Read query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_repo(self, repo_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a repository node"""
        query = """
        MERGE (r:Repo {id: $repo_id})
        SET r += $metadata
        RETURN r
        """
        return self.execute_write(query, {
            "repo_id": repo_id,
            "metadata": metadata or {}
        })
    
    def create_file(
        self,
        repo_id: str,
        path: str,
        lang: str,
        size: int,
        content: Optional[str] = None,
        sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a file node and link to repo"""
        query = """
        MATCH (r:Repo {id: $repo_id})
        MERGE (f:File {repoId: $repo_id, path: $path})
        SET f.lang = $lang,
            f.size = $size,
            f.content = $content,
            f.sha = $sha,
            f.updated = datetime()
        MERGE (f)-[:IN_REPO]->(r)
        RETURN f
        """
        return self.execute_write(query, {
            "repo_id": repo_id,
            "path": path,
            "lang": lang,
            "size": size,
            "content": content,
            "sha": sha
        })
    
    def fulltext_search(
        self,
        query_text: str,
        repo_id: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Fulltext search on files"""
        cypher_query = """
        CALL db.index.fulltext.queryNodes('file_text', $query_text)
        YIELD node, score
        WHERE node.repoId = $repo_id OR $repo_id IS NULL
        RETURN node.path as path,
               node.lang as lang,
               node.size as size,
               node.repoId as repoId,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        result = self.execute_read(cypher_query, {
            "query_text": query_text,
            "repo_id": repo_id,
            "limit": limit
        })
        
        if result.get("success"):
            return result.get("records", [])
        return []
    
    def get_repo_stats(self, repo_id: str) -> Dict[str, Any]:
        """Get repository statistics"""
        query = """
        MATCH (r:Repo {id: $repo_id})
        OPTIONAL MATCH (f:File)-[:IN_REPO]->(r)
        RETURN r.id as repo_id,
               count(f) as file_count
        """
        result = self.execute_read(query, {"repo_id": repo_id})
        if result.get("success") and result.get("records"):
            return result["records"][0]
        return {}


# Global Neo4j service instance
neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """Get global Neo4j service instance"""
    global neo4j_service
    
    if neo4j_service is None:
        # Import settings here to avoid circular dependency
        from config import settings
        
        neo4j_service = Neo4jService(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database
        )
        
        # Connect and initialize schema
        if neo4j_service.connect():
            neo4j_service.initialize_schema()
    
    return neo4j_service
