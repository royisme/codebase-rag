"""
FastAPI dependencies (v0.2)
"""
from fastapi import Depends
from backend.app.services.graph.neo4j_service import get_neo4j_service, Neo4jService


def get_db() -> Neo4jService:
    """Get Neo4j service dependency"""
    return get_neo4j_service()
