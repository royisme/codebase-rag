import json
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Using a plain dict for model_config to avoid ConfigDict typing/overload issues
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Application Settings
    app_name: str = "Code Graph Knowledge Service"
    app_version: str = "1.0.0"
    debug: bool = False
    # server settings
    host: str = Field(default="0.0.0.0", description="Host", alias="HOST")
    port: int = Field(default=8123, description="Port", alias="PORT")

    # Database Settings
    db_path: str = Field(
        default="data/knowledge.db", description="SQLite database path", alias="DB_PATH"
    )
    db_driver_async: str = Field(
        default="sqlite+aiosqlite",
        description="SQLAlchemy async driver",
        alias="DB_DRIVER_ASYNC",
    )
    db_driver_sync: str = Field(
        default="sqlite", description="SQLAlchemy sync driver", alias="DB_DRIVER_SYNC"
    )
    db_host: Optional[str] = Field(
        default=None, description="Database host", alias="DB_HOST"
    )
    db_port: Optional[int] = Field(
        default=None, description="Database port", alias="DB_PORT"
    )
    db_user: Optional[str] = Field(
        default=None, description="Database user", alias="DB_USER"
    )
    db_password: Optional[str] = Field(
        default=None, description="Database password", alias="DB_PASSWORD"
    )
    db_name: Optional[str] = Field(
        default=None, description="Database name", alias="DB_NAME"
    )
    db_schema: Optional[str] = Field(
        default=None, description="Database schema/search_path", alias="DB_SCHEMA"
    )
    db_echo: bool = Field(
        default=False, description="Enable SQLAlchemy echo logging", alias="DB_ECHO"
    )
    sqlite_busy_timeout_seconds: int = Field(
        default=30,
        description="SQLite busy timeout (seconds) when the database is locked",
        alias="SQLITE_BUSY_TIMEOUT_SECONDS",
    )
    sqlite_journal_mode: str = Field(
        default="WAL",
        description="SQLite journal mode (e.g. DELETE, WAL, MEMORY)",
        alias="SQLITE_JOURNAL_MODE",
    )
    sqlite_synchronous: str = Field(
        default="NORMAL",
        description="SQLite synchronous setting (e.g. FULL, NORMAL, OFF)",
        alias="SQLITE_SYNCHRONOUS",
    )

    # Auth Settings
    auth_jwt_secret: str = Field(
        default="change-me", description="JWT signing secret", alias="AUTH_JWT_SECRET"
    )
    auth_access_token_lifetime: int = Field(
        default=3600,
        description="JWT access token lifetime in seconds",
        alias="AUTH_ACCESS_TOKEN_LIFETIME",
    )
    auth_reset_token_secret: str = Field(
        default="change-me-reset",
        description="Password reset token secret",
        alias="AUTH_RESET_TOKEN_SECRET",
    )
    auth_verification_token_secret: str = Field(
        default="change-me-verify",
        description="Email verification token secret",
        alias="AUTH_VERIFICATION_TOKEN_SECRET",
    )
    auth_superuser_email: str = Field(
        default="admin@example.com",
        description="Default superuser email",
        alias="AUTH_SUPERUSER_EMAIL",
    )
    auth_superuser_password: str = Field(
        default="Admin123!@#",
        description="Default superuser password",
        alias="AUTH_SUPERUSER_PASSWORD",
    )

    # Monitoring Settings
    enable_monitoring: bool = Field(
        default=True,
        description="Enable web-based monitoring interface",
        alias="ENABLE_MONITORING",
    )
    monitoring_path: str = Field(
        default="/ui",
        description="Base path for monitoring interface",
        alias="MONITORING_PATH",
    )

    # Vector Search Settings (using Neo4j built-in vector index)
    vector_index_name: str = Field(
        default="vector", description="Neo4j vector index name"
    )
    vector_dimension: int = Field(default=384, description="Vector embedding dimension")

    @field_validator("vector_dimension", mode="before")
    @classmethod
    def validate_vector_dimension(cls, value):
        """Allow empty strings to fall back to default and coerce to int."""
        if value is None:
            return 384
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 384
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError("vector_dimension must be an integer") from exc
        return value

    # Neo4j Graph Database
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
        alias="NEO4J_URI",
    )
    neo4j_username: str = Field(
        default="neo4j", description="Neo4j username", alias="NEO4J_USER"
    )
    neo4j_password: str = Field(
        default="password", description="Neo4j password", alias="NEO4J_PASSWORD"
    )
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # LLM Provider Configuration
    llm_provider: Literal["ollama", "openai", "gemini", "openrouter"] = Field(
        default="ollama", description="LLM provider to use", alias="LLM_PROVIDER"
    )

    # Ollama LLM Service
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama service URL",
        alias="OLLAMA_HOST",
    )
    ollama_model: str = Field(
        default="llama2", description="Ollama model name", alias="OLLAMA_MODEL"
    )

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key", alias="OPENAI_API_KEY"
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo", description="OpenAI model name", alias="OPENAI_MODEL"
    )
    openai_base_url: Optional[str] = Field(
        default=None, description="OpenAI API base URL", alias="OPENAI_BASE_URL"
    )

    # Google Gemini Configuration
    google_api_key: Optional[str] = Field(
        default=None, description="Google API key", alias="GOOGLE_API_KEY"
    )
    gemini_model: str = Field(
        default="gemini-pro", description="Gemini model name", alias="GEMINI_MODEL"
    )

    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(
        default=None, description="OpenRouter API key", alias="OPENROUTER_API_KEY"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_model: Optional[str] = Field(
        default="openai/gpt-3.5-turbo",
        description="OpenRouter model",
        alias="OPENROUTER_MODEL",
    )
    openrouter_max_tokens: int = Field(
        default=2048,
        description="OpenRouter max tokens for completion",
        alias="OPENROUTER_MAX_TOKENS",
    )

    # Embedding Provider Configuration
    embedding_provider: Literal[
        "ollama", "openai", "gemini", "huggingface", "openrouter"
    ] = Field(
        default="ollama",
        description="Embedding provider to use",
        alias="EMBEDDING_PROVIDER",
    )

    # Ollama Embedding
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model",
        alias="OLLAMA_EMBEDDING_MODEL",
    )

    # OpenAI Embedding
    openai_embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model",
        alias="OPENAI_EMBEDDING_MODEL",
    )

    # Gemini Embedding
    gemini_embedding_model: str = Field(
        default="models/embedding-001",
        description="Gemini embedding model",
        alias="GEMINI_EMBEDDING_MODEL",
    )

    # HuggingFace Embedding
    huggingface_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace embedding model",
        alias="HF_EMBEDDING_MODEL",
    )

    # OpenRouter Embedding
    openrouter_embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="OpenRouter embedding model",
        alias="OPENROUTER_EMBEDDING_MODEL",
    )

    # Model Parameters
    temperature: float = Field(default=0.1, description="LLM temperature")
    max_tokens: int = Field(default=2048, description="Maximum tokens for LLM response")

    # RAG Settings
    chunk_size: int = Field(default=512, description="Text chunk size for processing")
    chunk_overlap: int = Field(default=50, description="Chunk overlap size")
    top_k: int = Field(default=5, description="Top K results for retrieval")

    # Timeout Settings
    connection_timeout: int = Field(
        default=30, description="Connection timeout in seconds"
    )
    operation_timeout: int = Field(
        default=120, description="Operation timeout in seconds"
    )
    large_document_timeout: int = Field(
        default=300, description="Large document processing timeout in seconds"
    )

    # Document Processing Settings
    max_document_size: int = Field(
        default=10 * 1024 * 1024, description="Maximum document size in bytes (10MB)"
    )
    max_payload_size: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum task payload size for storage (50MB)",
    )

    # API Settings
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        description="CORS allowed origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None or value == "":
            return ["http://localhost:5173"]

        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        value = parsed
                    elif isinstance(parsed, str):
                        value = [parsed]
                    else:
                        raise ValueError(
                            "CORS origins must be a list or comma separated string"
                        )
                except json.JSONDecodeError as exc:
                    raise ValueError("Invalid JSON for CORS origins") from exc
            else:
                value = [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, list):
            origins = [str(item).strip() for item in value if str(item).strip()]
            if not origins or origins == ["*"]:
                return ["http://localhost:5173"]
            return origins

        raise ValueError("Unsupported CORS origins format")

    api_key: Optional[str] = Field(default=None, description="API authentication key")

    # logging
    log_file: Optional[str] = Field(default="app.log", description="Log file path")
    log_level: str = Field(default="INFO", description="Log level")
    casbin_auto_save: bool = Field(
        default=True, description="Enable Casbin auto-save", alias="CASBIN_AUTO_SAVE"
    )

    # Knowledge Source Processing Settings
    knowledge_sync_enabled: bool = Field(
        default=True,
        description="Enable automatic knowledge source synchronization",
        alias="KNOWLEDGE_SYNC_ENABLED",
    )
    knowledge_sync_interval_minutes: int = Field(
        default=60,
        description="Default sync interval for knowledge sources (minutes)",
        alias="KNOWLEDGE_SYNC_INTERVAL_MINUTES",
    )
    knowledge_max_concurrent_jobs: int = Field(
        default=3,
        description="Maximum concurrent knowledge source processing jobs",
        alias="KNOWLEDGE_MAX_CONCURRENT_JOBS",
    )
    knowledge_job_timeout_minutes: int = Field(
        default=30,
        description="Default timeout for knowledge source jobs (minutes)",
        alias="KNOWLEDGE_JOB_TIMEOUT_MINUTES",
    )
    knowledge_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed knowledge source jobs",
        alias="KNOWLEDGE_RETRY_ATTEMPTS",
    )

    # Code Repository Indexing Defaults
    code_repo_root: str = Field(
        default="data/repos",
        description="Root directory for cloning code repositories",
        alias="CODE_REPO_ROOT",
    )
    code_git_depth: int = Field(
        default=1,
        description="Default git clone depth for repository sync",
        alias="CODE_GIT_DEPTH",
    )
    code_include_patterns: list[str] = Field(
        default_factory=lambda: ["*.py", "*.ts", "*.js", "*.go"],
        description="Default include glob patterns when scanning repositories",
        alias="CODE_INCLUDE_PATTERNS",
    )
    code_exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "node_modules/*",
            "*.test.*",
            "tests/*",
            "__pycache__/*",
        ],
        description="Default exclude glob patterns when scanning repositories",
        alias="CODE_EXCLUDE_PATTERNS",
    )
    code_max_file_size_kb: int = Field(
        default=500,
        description="Maximum file size (KB) considered during repository scanning",
        alias="CODE_MAX_FILE_SIZE_KB",
    )
    code_max_concurrent_indexing: int = Field(
        default=2,
        description="Maximum number of concurrent repository indexing pipelines",
        alias="CODE_MAX_CONCURRENT_INDEXING",
    )
    code_job_timeout_seconds: int = Field(
        default=900,
        description="Timeout budget for a single repository indexing job in seconds",
        alias="CODE_JOB_TIMEOUT_SECONDS",
    )

    # GraphRAG Settings
    graphrag_query_timeout_seconds: int = Field(
        default=30,
        description="Default timeout for GraphRAG queries (seconds)",
        alias="GRAPHRAG_QUERY_TIMEOUT_SECONDS",
    )
    graphrag_max_results: int = Field(
        default=20,
        description="Maximum results for GraphRAG queries",
        alias="GRAPHRAG_MAX_RESULTS",
    )
    graphrag_enable_evidence: bool = Field(
        default=True,
        description="Enable evidence collection for GraphRAG queries",
        alias="GRAPHRAG_ENABLE_EVIDENCE",
    )
    graphrag_query_cache_ttl_seconds: int = Field(
        default=600,
        description="Cache TTL for GraphRAG query results (seconds)",
        alias="GRAPHRAG_QUERY_CACHE_TTL_SECONDS",
    )
    graphrag_use_demo: bool = Field(
        default=True,
        description="Use demo provider for GraphRAG if Neo4j/LLM not available",
        alias="GRAPHRAG_USE_DEMO",
    )
    graphrag_demo_answers_path: str = Field(
        default="data/demo_answers",
        description="Path to demo answers JSON files",
        alias="GRAPHRAG_DEMO_ANSWERS_PATH",
    )

    @property
    def database_dsn_async(self) -> str:
        driver = (self.db_driver_async or "sqlite+aiosqlite").lower()
        if driver.startswith("sqlite"):
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{driver}:///{db_path.as_posix()}"

        return self._build_sql_dsn(driver, async_driver=True)

    @property
    def database_dsn_sync(self) -> str:
        driver = (self.db_driver_sync or "sqlite").lower()
        if driver.startswith("sqlite"):
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{driver}:///{db_path.as_posix()}"

        return self._build_sql_dsn(driver, async_driver=False)

    def _build_sql_dsn(self, driver: str, *, async_driver: bool) -> str:
        # reference async_driver to avoid unused parameter diagnostics; kept for future behavior differences
        _ = async_driver

        host = self.db_host or "localhost"
        port = self.db_port or (5432 if "postgres" in driver else None)
        username = quote_plus(self.db_user) if self.db_user else ""
        password = quote_plus(self.db_password) if self.db_password else ""
        auth = ""
        if username:
            auth = username
            if password:
                auth += f":{password}"
            auth += "@"

        if port:
            host_part = f"{host}:{port}"
        else:
            host_part = host

        database = self.db_name or ""
        base = f"{driver}://{auth}{host_part}/{database}"

        return base

    @property
    def code_repo_root_path(self) -> Path:
        repo_root = Path(self.code_repo_root)
        repo_root.mkdir(parents=True, exist_ok=True)
        return repo_root


settings = Settings()

# Validation functions


def validate_neo4j_connection():
    """Validate Neo4j connection parameters"""
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password)
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
            api_key=settings.openai_api_key, base_url=settings.openai_base_url
        )
        # Test with a simple completion
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
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
            "X-Title": "CodeGraph Knowledge Service",
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
            "openrouter": settings.openrouter_model,
        }.get(settings.llm_provider),
        "embedding_provider": settings.embedding_provider,
        "embedding_model": {
            "ollama": settings.ollama_embedding_model,
            "openai": settings.openai_embedding_model,
            "gemini": settings.gemini_embedding_model,
            "huggingface": settings.huggingface_embedding_model,
            "openrouter": settings.openrouter_embedding_model,
        }.get(settings.embedding_provider),
    }
