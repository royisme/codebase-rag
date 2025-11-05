#!/usr/bin/env python3
"""
MCP server for knowledge graph
Provide knowledge graph query service for AI
"""

import sys
from pathlib import Path
from loguru import logger
from config import settings,get_current_model_info

# add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """check necessary dependencies"""
    required_packages = [
        "fastmcp",
        "neo4j", 
        "ollama",
        "loguru"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package} is available")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} is missing")
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.error("Please install missing packages:")
        logger.error(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_services():
    """check necessary services"""
    from config import validate_neo4j_connection, validate_ollama_connection, validate_openrouter_connection, settings
    
    logger.info("Checking service connections...")
    
    # check Neo4j connection
    if validate_neo4j_connection():
        logger.info("✓ Neo4j connection successful")
    else:
        logger.error("✗ Neo4j connection failed")
        logger.error("Please ensure Neo4j is running and accessible")
        return False
    
    # Conditionally check LLM provider connections
    if settings.llm_provider == "ollama" or settings.embedding_provider == "ollama":
        if validate_ollama_connection():
            logger.info("✓ Ollama connection successful")
        else:
            logger.error("✗ Ollama connection failed")
            logger.error("Please ensure Ollama is running and accessible")
            return False
    
    if settings.llm_provider == "openrouter" or settings.embedding_provider == "openrouter":
        if validate_openrouter_connection():
            logger.info("✓ OpenRouter connection successful")
        else:
            logger.error("✗ OpenRouter connection failed")
            logger.error("Please ensure OpenRouter API key is configured correctly")
            return False
    
    return True

def print_mcp_info():
    """print MCP server info"""
    from config import settings
    
    logger.info("=" * 60)
    logger.info("Knowledge Graph MCP Server")
    logger.info("=" * 60)
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Model: {get_current_model_info()}")
    logger.info("=" * 60)
    
    logger.info("Available MCP Tools:")
    tools = [
        "query_knowledge - Query the knowledge base with RAG",
        "search_documents - Search for documents",
        "search_code - Search for code snippets", 
        "search_relations - Search for relationships",
        "add_document - Add a document to knowledge base",
        "add_file - Add a file to knowledge base",
        "add_directory - Add directory contents to knowledge base",
        "get_statistics - Get knowledge base statistics"
    ]
    
    for tool in tools:
        logger.info(f"  • {tool}")
    
    logger.info("\nAvailable MCP Resources:")
    resources = [
        "knowledge://config - System configuration",
        "knowledge://status - System status and health",
        "knowledge://recent-documents/{limit} - Recent documents"
    ]
    
    for resource in resources:
        logger.info(f"  • {resource}")
    
    logger.info("\nAvailable MCP Prompts:")
    prompts = [
        "suggest_queries - Generate query suggestions for different domains"
    ]
    
    for prompt in prompts:
        logger.info(f"  • {prompt}")
    
    logger.info("=" * 60)

def main():
    """main function"""
    logger.info("Starting Knowledge Graph MCP Server...")
    
    # check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # check services
    if not check_services():
        logger.error("Service check failed. Exiting.")
        sys.exit(1)
    
    # print service info
    print_mcp_info()
    
    # start MCP server
    try:
        logger.info("Starting MCP server...")
        logger.info("The server will run in STDIO mode for MCP client connections")
        logger.info("To test the server, run: python test_mcp_client.py")
        logger.info("Press Ctrl+C to stop the server")
        
        # import and run MCP server
        from mcp_server import mcp
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 