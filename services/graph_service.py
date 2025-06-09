from neo4j import GraphDatabase, basic_auth
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel
from loguru import logger
from config import settings
import json

class GraphNode(BaseModel):
    """graph node model"""
    id: str
    labels: List[str]
    properties: Dict[str, Any] = {}

class GraphRelationship(BaseModel):
    """graph relationship model"""
    id: Optional[str] = None
    start_node: str
    end_node: str
    type: str
    properties: Dict[str, Any] = {}

class GraphQueryResult(BaseModel):
    """graph query result model"""
    nodes: List[GraphNode] = []
    relationships: List[GraphRelationship] = []
    paths: List[Dict[str, Any]] = []
    raw_result: Optional[Any] = None

class Neo4jGraphService:
    """Neo4j graph database service"""
    
    def __init__(self):
        self.driver = None
        self._connected = False
    
    async def connect(self) -> bool:
        """connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=basic_auth(settings.neo4j_username, settings.neo4j_password)
            )
            
            # test connection
            with self.driver.session(database=settings.neo4j_database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            self._connected = True
            logger.info(f"Successfully connected to Neo4j at {settings.neo4j_uri}")
            
            # create indexes and constraints
            await self._setup_schema()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    async def _setup_schema(self):
        """set database schema, indexes and constraints"""
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                # create unique constraints
                constraints = [
                    "CREATE CONSTRAINT code_entity_id IF NOT EXISTS FOR (n:CodeEntity) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (n:Function) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (n:Class) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (n:File) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT table_id IF NOT EXISTS FOR (n:Table) REQUIRE n.id IS UNIQUE",
                ]
                
                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Failed to create constraint: {e}")
                
                # create indexes
                indexes = [
                    "CREATE INDEX code_entity_name IF NOT EXISTS FOR (n:CodeEntity) ON (n.name)",
                    "CREATE INDEX function_name IF NOT EXISTS FOR (n:Function) ON (n.name)",
                    "CREATE INDEX class_name IF NOT EXISTS FOR (n:Class) ON (n.name)",
                    "CREATE INDEX file_path IF NOT EXISTS FOR (n:File) ON (n.path)",
                    "CREATE INDEX table_name IF NOT EXISTS FOR (n:Table) ON (n.name)",
                ]
                
                for index in indexes:
                    try:
                        session.run(index)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Failed to create index: {e}")
            
            logger.info("Schema setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
    
    async def create_node(self, node: GraphNode) -> Dict[str, Any]:
        """create graph node"""
        if not self._connected:
            raise Exception("Not connected to Neo4j")
        
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                # build Cypher query to create node
                labels_str = ":".join(node.labels)
                query = f"""
                CREATE (n:{labels_str} {{id: $id}})
                SET n += $properties
                RETURN n
                """
                
                result = session.run(query, {
                    "id": node.id,
                    "properties": node.properties
                })
                
                created_node = result.single()
                logger.info(f"Successfully created node: {node.id}")
                
                return {
                    "success": True,
                    "node_id": node.id,
                    "labels": node.labels
                }
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_relationship(self, relationship: GraphRelationship) -> Dict[str, Any]:
        """create graph relationship"""
        if not self._connected:
            raise Exception("Not connected to Neo4j")
        
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                query = f"""
                MATCH (a {{id: $start_node}}), (b {{id: $end_node}})
                CREATE (a)-[r:{relationship.type}]->(b)
                SET r += $properties
                RETURN r
                """
                
                result = session.run(query, {
                    "start_node": relationship.start_node,
                    "end_node": relationship.end_node,
                    "properties": relationship.properties
                })
                
                created_rel = result.single()
                logger.info(f"Successfully created relationship: {relationship.start_node} -> {relationship.end_node}")
                
                return {
                    "success": True,
                    "start_node": relationship.start_node,
                    "end_node": relationship.end_node,
                    "type": relationship.type
                }
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> GraphQueryResult:
        """execute Cypher query"""
        if not self._connected:
            raise Exception("Not connected to Neo4j")
        
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                result = session.run(query, parameters)
                
                # process result
                nodes = []
                relationships = []
                paths = []
                raw_results = []
                
                for record in result:
                    raw_results.append(dict(record))
                    
                    # extract nodes
                    for key, value in record.items():
                        if hasattr(value, 'labels'):  # Neo4j Node
                            node = GraphNode(
                                id=value.get('id', str(value.id)),
                                labels=list(value.labels),
                                properties=dict(value)
                            )
                            nodes.append(node)
                        elif hasattr(value, 'type'):  # Neo4j Relationship
                            rel = GraphRelationship(
                                id=str(value.id),
                                start_node=str(value.start_node.id),
                                end_node=str(value.end_node.id),
                                type=value.type,
                                properties=dict(value)
                            )
                            relationships.append(rel)
                        elif hasattr(value, 'nodes'):  # Neo4j Path
                            path_info = {
                                "nodes": [dict(n) for n in value.nodes],
                                "relationships": [dict(r) for r in value.relationships],
                                "length": len(value.relationships)
                            }
                            paths.append(path_info)
                
                return GraphQueryResult(
                    nodes=nodes,
                    relationships=relationships,
                    paths=paths,
                    raw_result=raw_results
                )
                
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {e}")
            return GraphQueryResult(raw_result={"error": str(e)})
    
    async def find_nodes_by_label(self, label: str, limit: int = 100) -> List[GraphNode]:
        """find nodes by label"""
        query = f"MATCH (n:{label}) RETURN n LIMIT {limit}"
        result = await self.execute_cypher(query)
        return result.nodes
    
    async def find_relationships_by_type(self, rel_type: str, limit: int = 100) -> List[GraphRelationship]:
        """find relationships by type"""
        query = f"MATCH ()-[r:{rel_type}]->() RETURN r LIMIT {limit}"
        result = await self.execute_cypher(query)
        return result.relationships
    
    async def find_connected_nodes(self, node_id: str, depth: int = 1) -> GraphQueryResult:
        """find connected nodes"""
        query = f"""
        MATCH (start {{id: $node_id}})-[*1..{depth}]-(connected)
        RETURN start, connected, relationships()
        """
        return await self.execute_cypher(query, {"node_id": node_id})
    
    async def find_shortest_path(self, start_id: str, end_id: str) -> GraphQueryResult:
        """find shortest path"""
        query = """
        MATCH (start {id: $start_id}), (end {id: $end_id})
        MATCH path = shortestPath((start)-[*]-(end))
        RETURN path
        """
        return await self.execute_cypher(query, {
            "start_id": start_id,
            "end_id": end_id
        })
    
    async def get_node_degree(self, node_id: str) -> Dict[str, int]:
        """get node degree"""
        query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[out_rel]->()
        OPTIONAL MATCH (n)<-[in_rel]-()
        RETURN count(DISTINCT out_rel) as out_degree, 
               count(DISTINCT in_rel) as in_degree
        """
        result = await self.execute_cypher(query, {"node_id": node_id})
        
        if result.raw_result and len(result.raw_result) > 0:
            data = result.raw_result[0]
            return {
                "out_degree": data.get("out_degree", 0),
                "in_degree": data.get("in_degree", 0),
                "total_degree": data.get("out_degree", 0) + data.get("in_degree", 0)
            }
        return {"out_degree": 0, "in_degree": 0, "total_degree": 0}
    
    async def delete_node(self, node_id: str) -> Dict[str, Any]:
        """delete node and its relationships"""
        if not self._connected:
            raise Exception("Not connected to Neo4j")
        
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                query = """
                MATCH (n {id: $node_id})
                DETACH DELETE n
                """
                result = session.run(query, {"node_id": node_id})
                summary = result.consume()
                
                return {
                    "success": True,
                    "deleted_node": node_id,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_deleted": summary.counters.relationships_deleted
                }
        except Exception as e:
            logger.error(f"Failed to delete node: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """get database stats"""
        try:
            stats_queries = [
                ("total_nodes", "MATCH (n) RETURN count(n) as count"),
                ("total_relationships", "MATCH ()-[r]->() RETURN count(r) as count"),
                ("node_labels", "CALL db.labels() YIELD label RETURN collect(label) as labels"),
                ("relationship_types", "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types")
            ]
            
            stats = {}
            for stat_name, query in stats_queries:
                result = await self.execute_cypher(query)
                if result.raw_result and len(result.raw_result) > 0:
                    if stat_name in ["total_nodes", "total_relationships"]:
                        stats[stat_name] = result.raw_result[0].get("count", 0)
                    else:
                        stats[stat_name] = result.raw_result[0].get(stat_name.split("_")[1], [])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}
    
    async def batch_create_nodes(self, nodes: List[GraphNode]) -> Dict[str, Any]:
        """batch create nodes"""
        if not self._connected:
            raise Exception("Not connected to Neo4j")
        
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                # prepare batch data
                node_data = []
                for node in nodes:
                    node_data.append({
                        "id": node.id,
                        "labels": node.labels,
                        "properties": node.properties
                    })
                
                query = """
                UNWIND $nodes as nodeData
                CALL apoc.create.node(nodeData.labels, {id: nodeData.id} + nodeData.properties) YIELD node
                RETURN count(node) as created_count
                """
                
                result = session.run(query, {"nodes": node_data})
                summary = result.single()
                
                return {
                    "success": True,
                    "created_count": summary.get("created_count", len(nodes))
                }
        except Exception as e:
            # if APOC is not available, use standard method
            logger.warning(f"APOC not available, using standard method: {e}")
            return await self._batch_create_nodes_standard(nodes)
    
    async def _batch_create_nodes_standard(self, nodes: List[GraphNode]) -> Dict[str, Any]:
        """use standard method to batch create nodes"""
        created_count = 0
        errors = []
        
        for node in nodes:
            result = await self.create_node(node)
            if result.get("success"):
                created_count += 1
            else:
                errors.append(result.get("error"))
        
        return {
            "success": True,
            "created_count": created_count,
            "errors": errors
        }
    
    async def close(self):
        """close database connection"""
        try:
            if self.driver:
                self.driver.close()
                self._connected = False
                logger.info("Disconnected from Neo4j")
        except Exception as e:
            logger.error(f"Failed to close Neo4j connection: {e}")

# global graph service instance
graph_service = Neo4jGraphService() 