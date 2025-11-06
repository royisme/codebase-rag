"""
主应用入口文件

ARCHITECTURE (Two-Port Setup):
  - Port 8000: MCP SSE Service (PRIMARY)
  - Port 8080: Web UI + REST API (SECONDARY)
"""

import asyncio
import uvicorn
from loguru import logger
from multiprocessing import Process

from config import settings
from core.app import create_app
from core.logging import setup_logging
from core.mcp_sse import create_mcp_sse_app

# setup logging
setup_logging()

# create apps
app = create_app()  # Web UI + REST API
mcp_app = create_mcp_sse_app()  # MCP SSE

# start server (legacy - single port)
def start_server_legacy():
    """start server (legacy mode - all services on one port)"""
    logger.info(f"Starting server on {settings.host}:{settings.port}")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=settings.debug
    )

# start MCP SSE server
def start_mcp_server():
    """Start MCP SSE server"""
    logger.info("="*70)
    logger.info("STARTING PRIMARY SERVICE: MCP SSE")
    logger.info("="*70)
    logger.info(f"MCP SSE Server: http://{settings.host}:{settings.mcp_port}/sse")
    logger.info(f"MCP Messages: http://{settings.host}:{settings.mcp_port}/messages/")
    logger.info("="*70)

    uvicorn.run(
        "main:mcp_app",
        host=settings.host,
        port=settings.mcp_port,  # From config: MCP_PORT (default 8000)
        log_level="info" if not settings.debug else "debug",
        access_log=False  # Reduce noise
    )

# start Web UI + REST API server
def start_web_server():
    """Start Web UI + REST API server"""
    logger.info("="*70)
    logger.info("STARTING SECONDARY SERVICE: Web UI + REST API")
    logger.info("="*70)
    logger.info(f"Web UI: http://{settings.host}:{settings.web_ui_port}/")
    logger.info(f"REST API: http://{settings.host}:{settings.web_ui_port}/api/v1/")
    logger.info(f"Metrics: http://{settings.host}:{settings.web_ui_port}/metrics")
    logger.info("="*70)

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.web_ui_port,  # From config: WEB_UI_PORT (default 8080)
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=settings.debug
    )

def start_server():
    """Start both servers (two-port mode)"""
    logger.info("\n" + "="*70)
    logger.info("CODE GRAPH KNOWLEDGE SYSTEM")
    logger.info("="*70)
    logger.info("Architecture: Two-Port Setup")
    logger.info(f"  PRIMARY:   MCP SSE Service       → Port {settings.mcp_port} (MCP_PORT)")
    logger.info(f"  SECONDARY: Web UI + REST API     → Port {settings.web_ui_port} (WEB_UI_PORT)")
    logger.info("")
    logger.info("Environment Variables (optional):")
    logger.info("  MCP_PORT=8000      # MCP SSE service port")
    logger.info("  WEB_UI_PORT=8080   # Web UI + REST API port")
    logger.info("="*70 + "\n")

    # Create processes for both servers
    mcp_process = Process(target=start_mcp_server, name="MCP-SSE-Server")
    web_process = Process(target=start_web_server, name="Web-UI-Server")

    try:
        # Start both servers
        mcp_process.start()
        web_process.start()

        # Wait for both
        mcp_process.join()
        web_process.join()

    except KeyboardInterrupt:
        logger.info("\nShutting down servers...")
        mcp_process.terminate()
        web_process.terminate()
        mcp_process.join()
        web_process.join()
        logger.info("Servers stopped")

if __name__ == "__main__":
    start_server() 