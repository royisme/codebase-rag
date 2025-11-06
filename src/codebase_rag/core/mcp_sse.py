"""
MCP SSE Transport Integration
Provides Server-Sent Events transport for MCP in Docker/production environments
"""

from typing import Any
from fastapi import Request
from fastapi.responses import Response
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from loguru import logger

from mcp.server.sse import SseServerTransport
from mcp_server import server as mcp_server, ensure_service_initialized


# Create SSE transport with /messages/ endpoint
sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request) -> Response:
    """
    Handle SSE connection endpoint

    This is the main MCP connection endpoint that clients connect to.
    Clients will:
    1. GET /mcp/sse - Establish SSE connection
    2. POST /mcp/messages/ - Send messages to server
    """
    logger.info(f"MCP SSE connection requested from {request.client.host}")

    try:
        # Ensure services are initialized before handling connection
        await ensure_service_initialized()

        # Connect SSE and run MCP server
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send  # type: ignore
        ) as streams:
            logger.info("MCP SSE connection established")

            # Run MCP server with the connected streams
            await mcp_server.run(
                streams[0],  # read stream
                streams[1],  # write stream
                mcp_server.create_initialization_options()
            )

        logger.info("MCP SSE connection closed")

    except Exception as e:
        logger.error(f"MCP SSE connection error: {e}", exc_info=True)
        raise

    # Return empty response (connection handled by SSE)
    return Response()


def create_mcp_sse_app() -> Starlette:
    """
    Create standalone Starlette app for MCP SSE transport

    This creates a minimal Starlette application that handles:
    - GET /sse - SSE connection endpoint
    - POST /messages/ - Message receiving endpoint

    Returns:
        Starlette app for MCP SSE
    """
    routes = [
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ]

    logger.info("MCP SSE transport initialized")
    logger.info("  - SSE endpoint: GET /mcp/sse")
    logger.info("  - Message endpoint: POST /mcp/messages/")

    return Starlette(routes=routes)
