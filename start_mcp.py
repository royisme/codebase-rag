"""
MCP Server v2 Startup Script

Starts the official MCP SDK-based server with enhanced features:
- Session management
- Streaming responses (ready for future use)
- Multi-transport support
- Focus on Memory Store tools

Usage:
    python start_mcp_v2.py

Configuration:
    Add to Claude Desktop config:
    {
      "mcpServers": {
        "codebase-rag-memory-v2": {
          "command": "python",
          "args": ["/path/to/start_mcp_v2.py"],
          "env": {}
        }
      }
    }
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

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main entry point"""
    try:
        logger.info("=" * 70)
        logger.info("MCP Server v2 (Official SDK) - Memory Store")
        logger.info("=" * 70)
        logger.info(f"Python: {sys.version}")
        logger.info(f"Working directory: {Path.cwd()}")

        # Import and run the server
        from mcp_server_v2 import main as server_main

        logger.info("Starting server...")
        asyncio.run(server_main())

    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
