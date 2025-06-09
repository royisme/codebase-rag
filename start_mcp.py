#!/usr/bin/env python3
"""
MCP服务器启动脚本
提供知识图谱查询服务给AI使用
"""

import sys
import asyncio
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """检查必要的依赖"""
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
    """检查必要的服务"""
    from config import validate_neo4j_connection, validate_ollama_connection
    
    logger.info("Checking service connections...")
    
    # 检查Neo4j连接
    if validate_neo4j_connection():
        logger.info("✓ Neo4j connection successful")
    else:
        logger.error("✗ Neo4j connection failed")
        logger.error("Please ensure Neo4j is running and accessible")
        return False
    
    # 检查Ollama连接
    if validate_ollama_connection():
        logger.info("✓ Ollama connection successful")
    else:
        logger.error("✗ Ollama connection failed")
        logger.error("Please ensure Ollama is running and accessible")
        return False
    
    return True

def print_mcp_info():
    """打印MCP服务器信息"""
    from config import settings
    
    logger.info("=" * 60)
    logger.info("Knowledge Graph MCP Server")
    logger.info("=" * 60)
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
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
    """主函数"""
    logger.info("Starting Knowledge Graph MCP Server...")
    
    # 检查依赖
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # 检查服务
    if not check_services():
        logger.error("Service check failed. Exiting.")
        sys.exit(1)
    
    # 打印服务信息
    print_mcp_info()
    
    # 启动MCP服务器
    try:
        logger.info("Starting MCP server...")
        logger.info("The server will run in STDIO mode for MCP client connections")
        logger.info("To test the server, run: python test_mcp_client.py")
        logger.info("Press Ctrl+C to stop the server")
        
        # 导入并运行MCP服务器
        from mcp_server import mcp
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 