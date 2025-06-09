from typing import List
import asyncio
from loguru import logger

from .base import EmbeddingGenerator

class HuggingFaceEmbeddingGenerator(EmbeddingGenerator):
    """HuggingFace嵌入生成器"""
    
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._initialized = False
    
    async def _initialize(self):
        """延迟初始化模型"""
        if self._initialized:
            return
        
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            logger.info(f"Loading embedding model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.eval()
            
            self._initialized = True
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
            
        except ImportError:
            raise ImportError("Please install transformers and torch: pip install transformers torch")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
        await self._initialize()
        
        try:
            import torch
            
            # 文本预处理
            text = text.strip()
            if not text:
                raise ValueError("Empty text provided")
            
            # 分词
            inputs = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # 生成嵌入
            with torch.no_grad():
                outputs = self.model(**inputs)
                # 使用CLS token的输出作为句子嵌入
                embeddings = outputs.last_hidden_state[:, 0, :].squeeze()
                
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        await self._initialize()
        
        if not texts:
            return []
        
        try:
            import torch
            
            # 过滤空文本
            valid_texts = [text.strip() for text in texts if text.strip()]
            if not valid_texts:
                raise ValueError("No valid texts provided")
            
            # 批量分词
            inputs = self.tokenizer(
                valid_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # 生成嵌入
            with torch.no_grad():
                outputs = self.model(**inputs)
                # 使用CLS token的输出作为句子嵌入
                embeddings = outputs.last_hidden_state[:, 0, :]
                
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {len(texts)} texts: {e}")
            raise

class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """OpenAI嵌入生成器"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model
        self.client = None
    
    async def _get_client(self):
        """获取OpenAI客户端"""
        if self.client is None:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self.client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
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
        """批量生成嵌入向量"""
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
    """Ollama本地嵌入生成器"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.host = host.rstrip('/')
        self.model = model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
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
        """批量生成嵌入向量"""
        # Ollama通常需要逐个请求，我们使用并发来提高性能
        tasks = [self.generate_embedding(text) for text in texts]
        
        try:
            embeddings = await asyncio.gather(*tasks)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate Ollama embeddings: {e}")
            raise

class EmbeddingGeneratorFactory:
    """嵌入生成器工厂"""
    
    @staticmethod
    def create_generator(config: dict) -> EmbeddingGenerator:
        """根据配置创建嵌入生成器"""
        provider = config.get("provider", "huggingface").lower()
        
        if provider == "huggingface":
            model_name = config.get("model_name", "BAAI/bge-small-zh-v1.5")
            return HuggingFaceEmbeddingGenerator(model_name=model_name)
        
        elif provider == "openai":
            api_key = config.get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            model = config.get("model", "text-embedding-ada-002")
            return OpenAIEmbeddingGenerator(api_key=api_key, model=model)
        
        elif provider == "ollama":
            host = config.get("host", "http://localhost:11434")
            model = config.get("model", "nomic-embed-text")
            return OllamaEmbeddingGenerator(host=host, model=model)
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

# 默认嵌入生成器（可以通过配置修改）
default_embedding_generator = None

def get_default_embedding_generator() -> EmbeddingGenerator:
    """获取默认嵌入生成器"""
    global default_embedding_generator
    
    if default_embedding_generator is None:
        # 使用HuggingFace作为默认选择
        default_embedding_generator = HuggingFaceEmbeddingGenerator()
    
    return default_embedding_generator

def set_default_embedding_generator(generator: EmbeddingGenerator):
    """设置默认嵌入生成器"""
    global default_embedding_generator
    default_embedding_generator = generator 