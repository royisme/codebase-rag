#!/usr/bin/env python3
"""
Code Graph Knowledge Service - Web Server Entry Point

This is a thin wrapper for backward compatibility.
The actual implementation is in src.codebase_rag.server.web
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.codebase_rag.config import (
    settings,
    validate_neo4j_connection,
    validate_ollama_connection,
    validate_openrouter_connection,
    get_current_model_info,
)
from src.codebase_rag.server.cli import (
    check_dependencies,
    wait_for_services,
    print_startup_info,
)
from loguru import logger


def main():
    """Main function"""
    print_startup_info()

    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)

    # Check environment variables
    logger.info("Checking environment configuration...")

    # Optional: wait for services to start (useful in development)
    if not settings.debug or input("Skip service dependency check? (y/N): ").lower().startswith('y'):
        logger.info("Skipping service dependency check")
    else:
        if not wait_for_services():
            logger.error("Service dependency check failed, continuing startup may encounter problems")
            if not input("Continue startup? (y/N): ").lower().startswith('y'):
                sys.exit(1)

    # Start application
    logger.info("Starting FastAPI application...")

    try:
        from src.codebase_rag.server.web import start_server
        start_server()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Start failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
