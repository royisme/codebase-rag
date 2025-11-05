from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from enum import Enum
import uuid
from pathlib import Path

class DataSourceType(str, Enum):
    """data source type enum"""
    DOCUMENT = "document"      # document type (markdown, pdf, word, txt)
    CODE = "code"             # code type (python, javascript, java, etc.)
    SQL = "sql"               # SQL database structure
    API = "api"               # API document
    CONFIG = "config"         # configuration file (json, yaml, toml)
    WEB = "web"               # web content
    UNKNOWN = "unknown"       # unknown type

class ChunkType(str, Enum):
    """data chunk type"""
    TEXT = "text"             # pure text chunk
    CODE_FUNCTION = "code_function"  # code function
    CODE_CLASS = "code_class"        # code class
    CODE_MODULE = "code_module"      # code module
    SQL_TABLE = "sql_table"          # SQL table structure
    SQL_SCHEMA = "sql_schema"        # SQL schema
    API_ENDPOINT = "api_endpoint"    # API endpoint
    DOCUMENT_SECTION = "document_section"  # document section

class DataSource(BaseModel):
    """data source model"""
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
    """processed data chunk"""
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
    """extracted relation information"""
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
    """processing result"""
    source_id: str
    success: bool
    chunks: List[ProcessedChunk] = []
    relations: List[ExtractedRelation] = []
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

# abstract base class definition

class DataLoader(ABC):
    """data loader abstract base class"""
    
    @abstractmethod
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        pass
    
    @abstractmethod
    async def load(self, data_source: DataSource) -> str:
        """load data source content"""
        pass

class DataTransformer(ABC):
    """data transformer abstract base class"""
    
    @abstractmethod
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        pass
    
    @abstractmethod
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """transform data to chunks and relations"""
        pass

class DataStorer(ABC):
    """data storer abstract base class"""
    
    @abstractmethod
    async def store_chunks(self, chunks: List[ProcessedChunk]) -> Dict[str, Any]:
        """store data chunks to vector database"""
        pass
    
    @abstractmethod
    async def store_relations(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """store relations to graph database"""
        pass

class EmbeddingGenerator(ABC):
    """embedding generator abstract base class"""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """generate text embedding vector"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """batch generate embedding vectors"""
        pass

# helper functions

def detect_data_source_type(file_path: str) -> DataSourceType:
    """detect data source type based on file path"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    # document type
    if suffix in ['.md', '.markdown', '.txt', '.pdf', '.docx', '.doc', '.rtf']:
        return DataSourceType.DOCUMENT
    
    # code type
    elif suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb']:
        return DataSourceType.CODE
    
    # SQL type
    elif suffix in ['.sql', '.ddl']:
        return DataSourceType.SQL
    
    # config type
    elif suffix in ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']:
        return DataSourceType.CONFIG
    
    # API document
    elif suffix in ['.openapi', '.swagger'] or 'api' in path.name.lower():
        return DataSourceType.API
    
    else:
        return DataSourceType.UNKNOWN

def extract_file_metadata(file_path: str) -> Dict[str, Any]:
    """extract file metadata"""
    path = Path(file_path)
    
    metadata = {
        "filename": path.name,
        "file_size": path.stat().st_size if path.exists() else 0,
        "file_extension": path.suffix,
        "file_stem": path.stem,
        "created_time": path.stat().st_ctime if path.exists() else None,
        "modified_time": path.stat().st_mtime if path.exists() else None,
    }
    
    # code file specific metadata
    if path.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php']:
        metadata["language"] = get_language_from_extension(path.suffix)
    
    return metadata

def get_language_from_extension(extension: str) -> str:
    """get programming language from file extension"""
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