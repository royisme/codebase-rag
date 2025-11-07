from typing import List
import asyncio
from loguru import logger

from .base import EmbeddingGenerator

class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """OpenAI embedding generator"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model
        self.client = None
    
    async def _get_client(self):
        """get OpenAI client"""
        if self.client is None:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self.client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """generate single text embedding vector"""
        client = await self._get_client()
        
        try:
            response = await client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embedding: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """batch generate embedding vectors"""
        client = await self._get_client()
        
        try:
            response = await client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embeddings: {e}")
            raise

class OllamaEmbeddingGenerator(EmbeddingGenerator):
    """Ollama local embedding generator"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.host = host.rstrip('/')
        self.model = model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """generate single text embedding vector"""
        import aiohttp
        
        url = f"{self.host}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["embedding"]
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Failed to generate Ollama embedding: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """batch generate embedding vectors"""
        # Ollama usually needs to make individual requests, we use concurrency to improve performance
        tasks = [self.generate_embedding(text) for text in texts]
        
        try:
            embeddings = await asyncio.gather(*tasks)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate Ollama embeddings: {e}")
            raise

class OpenRouterEmbeddingGenerator(EmbeddingGenerator):
    """OpenRouter embedding generator"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model
        self.client = None
    
    async def _get_client(self):
        """get OpenRouter client (which is the same as OpenAI client)"""
        if self.client is None:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                    # OpenRouter requires the HTTP referer header to be set
                    # We set the referer to the application's name, or use a default
                    default_headers={
                        "HTTP-Referer": "CodeGraphKnowledgeService",
                        "X-Title": "CodeGraph Knowledge Service"
                    }
                )
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self.client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """generate single text embedding vector"""
        client = await self._get_client()
        
        try:
            response = await client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate OpenRouter embedding: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """batch generate embedding vectors"""
        client = await self._get_client()
        
        try:
            response = await client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"Failed to generate OpenRouter embeddings: {e}")
            raise

class EmbeddingGeneratorFactory:
    """embedding generator factory"""

    @staticmethod
    def create_generator(config: dict) -> EmbeddingGenerator:
        """create embedding generator based on configuration"""
        provider = config.get("provider", "ollama").lower()

        if provider == "openai":
            api_key = config.get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            model = config.get("model", "text-embedding-ada-002")
            return OpenAIEmbeddingGenerator(api_key=api_key, model=model)

        elif provider == "ollama":
            host = config.get("host", "http://localhost:11434")
            model = config.get("model", "nomic-embed-text")
            return OllamaEmbeddingGenerator(host=host, model=model)

        elif provider == "openrouter":
            api_key = config.get("api_key")
            if not api_key:
                raise ValueError("OpenRouter API key is required")
            model = config.get("model", "text-embedding-ada-002")
            return OpenRouterEmbeddingGenerator(api_key=api_key, model=model)

        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

# default embedding generator (can be modified through configuration)
default_embedding_generator = None

def get_default_embedding_generator() -> EmbeddingGenerator:
    """get default embedding generator"""
    global default_embedding_generator

    if default_embedding_generator is None:
        # use Ollama as default choice
        default_embedding_generator = OllamaEmbeddingGenerator()

    return default_embedding_generator

def set_default_embedding_generator(generator: EmbeddingGenerator):
    """set default embedding generator"""
    global default_embedding_generator
    default_embedding_generator = generator 
