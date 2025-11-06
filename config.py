from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal

class Settings(BaseSettings):
    # Application Settings
    app_name: str = "Code Graph Knowledge Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server Settings (Two-Port Architecture)
    host: str = Field(default="0.0.0.0", description="Host for all services", alias="HOST")

    # Port configuration
    port: int = Field(default=8123, description="Legacy port (deprecated)", alias="PORT")
    mcp_port: int = Field(default=8000, description="MCP SSE service port (PRIMARY)", alias="MCP_PORT")
    web_ui_port: int = Field(default=8080, description="Web UI + REST API port (SECONDARY)", alias="WEB_UI_PORT")

    # Vector Search Settings (using Neo4j built-in vector index)
    vector_index_name: str = Field(default="knowledge_vectors", description="Neo4j vector index name")
    vector_dimension: int = Field(default=384, description="Vector embedding dimension")
    
    # Neo4j Graph Database
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI", alias="NEO4J_URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", description="Neo4j password", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
    
    # LLM Provider Configuration
    llm_provider: Literal["ollama", "openai", "gemini", "openrouter"] = Field(
        default="ollama", 
        description="LLM provider to use", 
        alias="LLM_PROVIDER"
    )
    
    # Ollama LLM Service
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama service URL", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama2", description="Ollama model name", alias="OLLAMA_MODEL")
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model name", alias="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI API base URL", alias="OPENAI_BASE_URL")
    
    # Google Gemini Configuration
    google_api_key: Optional[str] = Field(default=None, description="Google API key", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-pro", description="Gemini model name", alias="GEMINI_MODEL")
    
    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API key", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API base URL", alias="OPENROUTER_BASE_URL")
    openrouter_model: Optional[str] = Field(default="openai/gpt-3.5-turbo", description="OpenRouter model", alias="OPENROUTER_MODEL")
    openrouter_max_tokens: int = Field(default=2048, description="OpenRouter max tokens for completion", alias="OPENROUTER_MAX_TOKENS")
    
    # Embedding Provider Configuration
    embedding_provider: Literal["ollama", "openai", "gemini", "huggingface", "openrouter"] = Field(
        default="ollama", 
        description="Embedding provider to use", 
        alias="EMBEDDING_PROVIDER"
    )
    
    # Ollama Embedding
    ollama_embedding_model: str = Field(default="nomic-embed-text", description="Ollama embedding model", alias="OLLAMA_EMBEDDING_MODEL")
    
    # OpenAI Embedding
    openai_embedding_model: str = Field(default="text-embedding-ada-002", description="OpenAI embedding model", alias="OPENAI_EMBEDDING_MODEL")
    
    # Gemini Embedding
    gemini_embedding_model: str = Field(default="models/embedding-001", description="Gemini embedding model", alias="GEMINI_EMBEDDING_MODEL")
    
    # HuggingFace Embedding
    huggingface_embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", description="HuggingFace embedding model", alias="HF_EMBEDDING_MODEL")
    
    # OpenRouter Embedding
    openrouter_embedding_model: str = Field(default="text-embedding-ada-002", description="OpenRouter embedding model", alias="OPENROUTER_EMBEDDING_MODEL")
    
    # Model Parameters
    temperature: float = Field(default=0.1, description="LLM temperature")
    max_tokens: int = Field(default=2048, description="Maximum tokens for LLM response")
    
    # RAG Settings
    chunk_size: int = Field(default=512, description="Text chunk size for processing")
    chunk_overlap: int = Field(default=50, description="Chunk overlap size")
    top_k: int = Field(default=5, description="Top K results for retrieval")
    
    # Timeout Settings
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    operation_timeout: int = Field(default=120, description="Operation timeout in seconds")
    large_document_timeout: int = Field(default=300, description="Large document processing timeout in seconds")
    
    # Document Processing Settings
    max_document_size: int = Field(default=10 * 1024 * 1024, description="Maximum document size in bytes (10MB)")
    max_payload_size: int = Field(default=50 * 1024 * 1024, description="Maximum task payload size for storage (50MB)")
    
    # API Settings
    cors_origins: list = Field(default=["*"], description="CORS allowed origins")
    api_key: Optional[str] = Field(default=None, description="API authentication key")
    
    # logging
    log_file: Optional[str] = Field(default="app.log", description="Log file path")
    log_level: str = Field(default="INFO", description="Log level")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的字段，避免验证错误

# Global settings instance
settings = Settings()

# Validation functions

def validate_neo4j_connection():
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

def validate_ollama_connection():
    """Validate Ollama service connection"""
    try:
        import httpx
        response = httpx.get(f"{settings.ollama_base_url}/api/tags")
        return response.status_code == 200
    except Exception as e:
        print(f"Ollama connection failed: {e}")
        return False

def validate_openai_connection():
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

def validate_gemini_connection():
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

def validate_openrouter_connection():
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

def get_current_model_info():
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
