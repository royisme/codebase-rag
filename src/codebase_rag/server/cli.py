"""
CLI utilities and helper functions for Codebase RAG servers.
"""

import sys
import time
from pathlib import Path
from loguru import logger

from codebase_rag.config import (
    settings,
    validate_neo4j_connection,
    validate_ollama_connection,
    validate_openrouter_connection,
    get_current_model_info,
)


def check_dependencies():
    """Check service dependencies"""
    logger.info("Checking service dependencies...")

    checks = [
        ("Neo4j", validate_neo4j_connection),
    ]

    # Conditionally add Ollama if it is the selected LLM or embedding provider
    if settings.llm_provider == "ollama" or settings.embedding_provider == "ollama":
        checks.append(("Ollama", validate_ollama_connection))

    # Conditionally add OpenRouter if it is the selected LLM or embedding provider
    if settings.llm_provider == "openrouter" or settings.embedding_provider == "openrouter":
        checks.append(("OpenRouter", validate_openrouter_connection))

    all_passed = True
    for service_name, check_func in checks:
        try:
            if check_func():
                logger.info(f"✓ {service_name} connection successful")
            else:
                logger.error(f"✗ {service_name} connection failed")
                all_passed = False
        except Exception as e:
            logger.error(f"✗ {service_name} check error: {e}")
            all_passed = False

    return all_passed


def wait_for_services(max_retries=30, retry_interval=2):
    """Wait for services to start"""
    logger.info("Waiting for services to start...")

    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}/{max_retries}...")

        if check_dependencies():
            logger.info("All services are ready!")
            return True

        if attempt < max_retries:
            logger.info(f"Waiting {retry_interval} seconds before retry...")
            time.sleep(retry_interval)

    logger.error("Service startup timeout!")
    return False


def print_startup_info():
    """Print startup information"""
    print("\n" + "="*60)
    print("Code Graph Knowledge Service")
    print("="*60)
    print(f"Version: {settings.app_version}")
    print(f"Host: {settings.host}:{settings.port}")
    print(f"Debug mode: {settings.debug}")
    print()
    print("Service configuration:")
    print(f"  Neo4j: {settings.neo4j_uri}")
    print(f"  Ollama: {settings.ollama_base_url}")
    print()
    model_info = get_current_model_info()
    print("Model configuration:")
    print(f"  LLM: {model_info['llm_model']}")
    print(f"  Embedding: {model_info['embedding_model']}")
    print("="*60)
    print()
