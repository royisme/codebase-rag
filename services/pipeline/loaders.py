from typing import Dict, Any
import aiofiles
from pathlib import Path
from loguru import logger

from .base import DataLoader, DataSource, DataSourceType

class FileLoader(DataLoader):
    """generic file loader"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        return data_source.source_path is not None
    
    async def load(self, data_source: DataSource) -> str:
        """load file content"""
        if not data_source.source_path:
            raise ValueError("source_path is required for FileLoader")
        
        try:
            async with aiofiles.open(data_source.source_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                logger.info(f"Successfully loaded file: {data_source.source_path}")
                return content
        except UnicodeDecodeError:
            # try other encodings
            try:
                async with aiofiles.open(data_source.source_path, 'r', encoding='gbk') as file:
                    content = await file.read()
                    logger.info(f"Successfully loaded file with GBK encoding: {data_source.source_path}")
                    return content
            except Exception as e:
                logger.error(f"Failed to load file with multiple encodings: {e}")
                raise

class ContentLoader(DataLoader):
    """content loader (load directly from content field)"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        return data_source.content is not None
    
    async def load(self, data_source: DataSource) -> str:
        """return content directly"""
        if not data_source.content:
            raise ValueError("content is required for ContentLoader")
        
        logger.info(f"Successfully loaded content for source: {data_source.name}")
        return data_source.content

class DocumentLoader(DataLoader):
    """document loader (supports PDF, Word, etc.)"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        if data_source.type != DataSourceType.DOCUMENT:
            return False
        
        if not data_source.source_path:
            return False
            
        supported_extensions = ['.md', '.markdown', '.txt', '.pdf', '.docx', '.doc']
        path = Path(data_source.source_path)
        return path.suffix.lower() in supported_extensions
    
    async def load(self, data_source: DataSource) -> str:
        """load document content"""
        path = Path(data_source.source_path)
        extension = path.suffix.lower()
        
        try:
            if extension in ['.md', '.markdown', '.txt']:
                # pure text file
                return await self._load_text_file(data_source.source_path)
            elif extension == '.pdf':
                # PDF file
                return await self._load_pdf_file(data_source.source_path)
            elif extension in ['.docx', '.doc']:
                # Word file
                return await self._load_word_file(data_source.source_path)
            else:
                raise ValueError(f"Unsupported document type: {extension}")
                
        except Exception as e:
            logger.error(f"Failed to load document {data_source.source_path}: {e}")
            raise
    
    async def _load_text_file(self, file_path: str) -> str:
        """load pure text file"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            return await file.read()
    
    async def _load_pdf_file(self, file_path: str) -> str:
        """load PDF file"""
        try:
            # need to install PyPDF2 or pdfplumber
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            logger.warning("PyPDF2 not installed, trying pdfplumber")
            try:
                import pdfplumber
                
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                raise ImportError("Please install PyPDF2 or pdfplumber to handle PDF files")
    
    async def _load_word_file(self, file_path: str) -> str:
        """load Word file"""
        try:
            import python_docx
            
            doc = python_docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            raise ImportError("Please install python-docx to handle Word files")

class CodeLoader(DataLoader):
    """code file loader"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        if data_source.type != DataSourceType.CODE:
            return False
            
        if not data_source.source_path:
            return False
            
        supported_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb']
        path = Path(data_source.source_path)
        return path.suffix.lower() in supported_extensions
    
    async def load(self, data_source: DataSource) -> str:
        """load code file"""
        try:
            async with aiofiles.open(data_source.source_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                
            # add code specific metadata
            path = Path(data_source.source_path)
            data_source.metadata.update({
                "language": self._detect_language(path.suffix),
                "file_size": len(content),
                "line_count": len(content.split('\n'))
            })
            
            logger.info(f"Successfully loaded code file: {data_source.source_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to load code file {data_source.source_path}: {e}")
            raise
    
    def _detect_language(self, extension: str) -> str:
        """detect programming language from file extension"""
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
        }
        return language_map.get(extension.lower(), 'unknown')

class SQLLoader(DataLoader):
    """SQL file loader"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        if data_source.type != DataSourceType.SQL:
            return False
            
        if data_source.source_path:
            path = Path(data_source.source_path)
            return path.suffix.lower() in ['.sql', '.ddl']
        
        # can also handle direct SQL content
        return data_source.content is not None
    
    async def load(self, data_source: DataSource) -> str:
        """load SQL file or content"""
        if data_source.source_path:
            try:
                async with aiofiles.open(data_source.source_path, 'r', encoding='utf-8') as file:
                    content = await file.read()
                    logger.info(f"Successfully loaded SQL file: {data_source.source_path}")
                    return content
            except Exception as e:
                logger.error(f"Failed to load SQL file {data_source.source_path}: {e}")
                raise
        elif data_source.content:
            logger.info(f"Successfully loaded SQL content for source: {data_source.name}")
            return data_source.content
        else:
            raise ValueError("Either source_path or content is required for SQLLoader")

class LoaderRegistry:
    """loader registry"""
    
    def __init__(self):
        self.loaders = [
            DocumentLoader(),
            CodeLoader(),
            SQLLoader(),
            FileLoader(),      # generic file loader as fallback
            ContentLoader(),   # content loader as last fallback
        ]
    
    def get_loader(self, data_source: DataSource) -> DataLoader:
        """get suitable loader based on data source"""
        for loader in self.loaders:
            if loader.can_handle(data_source):
                return loader
        
        raise ValueError(f"No suitable loader found for data source: {data_source.name}")
    
    def add_loader(self, loader: DataLoader):
        """add custom loader"""
        self.loaders.insert(0, loader)  # new loader has highest priority

# global loader registry instance
loader_registry = LoaderRegistry() 