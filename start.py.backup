#!/usr/bin/env python3
"""
Code Graph Knowledge Service
"""

import asyncio
import sys
import time
from pathlib import Path

# add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings,  validate_neo4j_connection, validate_ollama_connection, validate_openrouter_connection, get_current_model_info
from loguru import logger

def check_dependencies():
    """check service dependencies"""
    logger.info("check service dependencies...")
    
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
    """wait for services to start"""
    logger.info("wait for services to start...")
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"try {attempt}/{max_retries}...")
        
        if check_dependencies():
            logger.info("all services are ready!")
            return True
        
        if attempt < max_retries:
            logger.info(f"wait {retry_interval} seconds and retry...")
            time.sleep(retry_interval)
    
    logger.error("service startup timeout!")
    return False

def print_startup_info():
    """print startup info"""
    print("\n" + "="*60)
    print("Code Graph Knowledge Service")
    print("="*60)
    print(f"version: {settings.app_version}")
    print(f"host: {settings.host}:{settings.port}")
    print(f"debug mode: {settings.debug}")
    print()
    print("service config:")
    print(f"  Neo4j: {settings.neo4j_uri}")
    print(f"  Ollama: {settings.ollama_base_url}")
    print()
    model_info = get_current_model_info()
    print("model config:")
    print(f"  LLM: {model_info['llm_model']}")
    print(f"  Embedding: {model_info['embedding_model']}")
    print("="*60)
    print()

def main():
    """main function"""
    print_startup_info()
    
    # check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    
    # check environment variables
    logger.info("check environment config...")
    
    # optional: wait for services to start (useful in development)
    if not settings.debug or input("skip service dependency check? (y/N): ").lower().startswith('y'):
        logger.info("skip service dependency check")
    else:
        if not wait_for_services():
            logger.error("service dependency check failed, continue startup may encounter problems")
            if not input("continue startup? (y/N): ").lower().startswith('y'):
                sys.exit(1)
    
    # start application
    logger.info("start FastAPI application...")
    
    try:
        from main import start_server
        start_server()
    except KeyboardInterrupt:
        logger.info("service interrupted by user")
    except Exception as e:
        logger.error(f"start failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
