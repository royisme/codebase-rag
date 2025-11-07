"""
MCP Server entry point for Codebase RAG.

This module provides the MCP (Model Context Protocol) server implementation.
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


def main():
    """Main entry point for MCP server"""
    try:
        logger.info("=" * 70)
        logger.info("MCP Server - Codebase RAG")
        logger.info("=" * 70)
        logger.info(f"Python: {sys.version}")
        logger.info(f"Working directory: {Path.cwd()}")

        # Import and run the server from mcp/server.py
        from codebase_rag.mcp.server import main as server_main

        logger.info("Starting MCP server...")
        asyncio.run(server_main())

    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
