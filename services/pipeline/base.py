from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from enum import Enum
import uuid
from pathlib import Path

class DataSourceType(str, Enum):
    """数据源类型枚举"""
    DOCUMENT = "document"      # 文档类型 (markdown, pdf, word, txt)
    CODE = "code"             # 代码类型 (python, javascript, java, etc.)
    SQL = "sql"               # SQL数据库结构
    API = "api"               # API文档
    CONFIG = "config"         # 配置文件 (json, yaml, toml)
    WEB = "web"               # 网页内容
    UNKNOWN = "unknown"       # 未知类型

class ChunkType(str, Enum):
    """数据块类型"""
    TEXT = "text"             # 纯文本块
    CODE_FUNCTION = "code_function"  # 代码函数
    CODE_CLASS = "code_class"        # 代码类
    CODE_MODULE = "code_module"      # 代码模块
    SQL_TABLE = "sql_table"          # SQL表结构
    SQL_SCHEMA = "sql_schema"        # SQL模式
    API_ENDPOINT = "api_endpoint"    # API端点
    DOCUMENT_SECTION = "document_section"  # 文档章节

class DataSource(BaseModel):
    """数据源模型"""
    id: str
    name: str
    type: DataSourceType
    source_path: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

class ProcessedChunk(BaseModel):
    """处理后的数据块"""
    id: str
    source_id: str
    chunk_type: ChunkType
    content: str
    title: Optional[str] = None
    summary: Optional[str] = None
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    
    def __init__(self, **data):
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

class ExtractedRelation(BaseModel):
    """提取的关系信息"""
    id: str
    source_id: str
    from_entity: str
    to_entity: str
    relation_type: str
    properties: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

class ProcessingResult(BaseModel):
    """处理结果"""
    source_id: str
    success: bool
    chunks: List[ProcessedChunk] = []
    relations: List[ExtractedRelation] = []
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

# 抽象基类定义

class DataLoader(ABC):
    """数据加载器抽象基类"""
    
    @abstractmethod
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        pass
    
    @abstractmethod
    async def load(self, data_source: DataSource) -> str:
        """加载数据源内容"""
        pass

class DataTransformer(ABC):
    """数据转换器抽象基类"""
    
    @abstractmethod
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        pass
    
    @abstractmethod
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换数据为chunks和relations"""
        pass

class DataStorer(ABC):
    """数据存储器抽象基类"""
    
    @abstractmethod
    async def store_chunks(self, chunks: List[ProcessedChunk]) -> Dict[str, Any]:
        """存储数据块到向量数据库"""
        pass
    
    @abstractmethod
    async def store_relations(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """存储关系到图数据库"""
        pass

class EmbeddingGenerator(ABC):
    """嵌入生成器抽象基类"""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        pass

# 辅助函数

def detect_data_source_type(file_path: str) -> DataSourceType:
    """根据文件路径检测数据源类型"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    # 文档类型
    if suffix in ['.md', '.markdown', '.txt', '.pdf', '.docx', '.doc', '.rtf']:
        return DataSourceType.DOCUMENT
    
    # 代码类型
    elif suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb']:
        return DataSourceType.CODE
    
    # SQL类型
    elif suffix in ['.sql', '.ddl']:
        return DataSourceType.SQL
    
    # 配置类型
    elif suffix in ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']:
        return DataSourceType.CONFIG
    
    # API文档
    elif suffix in ['.openapi', '.swagger'] or 'api' in path.name.lower():
        return DataSourceType.API
    
    else:
        return DataSourceType.UNKNOWN

def extract_file_metadata(file_path: str) -> Dict[str, Any]:
    """提取文件元数据"""
    path = Path(file_path)
    
    metadata = {
        "filename": path.name,
        "file_size": path.stat().st_size if path.exists() else 0,
        "file_extension": path.suffix,
        "file_stem": path.stem,
        "created_time": path.stat().st_ctime if path.exists() else None,
        "modified_time": path.stat().st_mtime if path.exists() else None,
    }
    
    # 代码文件特有的元数据
    if path.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs']:
        metadata["language"] = get_language_from_extension(path.suffix)
    
    return metadata

def get_language_from_extension(extension: str) -> str:
    """根据文件扩展名获取编程语言"""
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.sql': 'sql',
    }
    return language_map.get(extension.lower(), 'unknown') 