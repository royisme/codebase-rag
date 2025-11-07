"""
Validation functions for configuration settings.

This module provides functions to validate connections to various services
like Neo4j, Ollama, OpenAI, Gemini, and OpenRouter.
"""

from codebase_rag.config.settings import settings


def validate_neo4j_connection() -> bool:
    """Validate Neo4j connection parameters"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return True
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        return False


def validate_ollama_connection() -> bool:
    """Validate Ollama service connection"""
    try:
        import httpx
        response = httpx.get(f"{settings.ollama_base_url}/api/tags")
        return response.status_code == 200
    except Exception as e:
        print(f"Ollama connection failed: {e}")
        return False


def validate_openai_connection() -> bool:
    """Validate OpenAI API connection"""
    if not settings.openai_api_key:
        print("OpenAI API key not provided")
        return False
    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        # Test with a simple completion
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        print(f"OpenAI connection failed: {e}")
        return False


def validate_gemini_connection() -> bool:
    """Validate Google Gemini API connection"""
    if not settings.google_api_key:
        print("Google API key not provided")
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        # Test with a simple generation
        response = model.generate_content("test")
        return True
    except Exception as e:
        print(f"Gemini connection failed: {e}")
        return False


def validate_openrouter_connection() -> bool:
    """Validate OpenRouter API connection"""
    if not settings.openrouter_api_key:
        print("OpenRouter API key not provided")
        return False
    try:
        import httpx
        # We'll use the models endpoint to check the connection
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            # OpenRouter requires these headers for identification
            "HTTP-Referer": "CodeGraphKnowledgeService",
            "X-Title": "CodeGraph Knowledge Service"
        }
        response = httpx.get("https://openrouter.ai/api/v1/models", headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"OpenRouter connection failed: {e}")
        return False


def get_current_model_info() -> dict:
    """Get information about currently configured models"""
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": {
            "ollama": settings.ollama_model,
            "openai": settings.openai_model,
            "gemini": settings.gemini_model,
            "openrouter": settings.openrouter_model
        }.get(settings.llm_provider),
        "embedding_provider": settings.embedding_provider,
        "embedding_model": {
            "ollama": settings.ollama_embedding_model,
            "openai": settings.openai_embedding_model,
            "gemini": settings.gemini_embedding_model,
            "huggingface": settings.huggingface_embedding_model,
            "openrouter": settings.openrouter_embedding_model
        }.get(settings.embedding_provider)
    }
