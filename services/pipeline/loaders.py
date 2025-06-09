from typing import Dict, Any
import aiofiles
from pathlib import Path
from loguru import logger

from .base import DataLoader, DataSource, DataSourceType

class FileLoader(DataLoader):
    """通用文件加载器"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        return data_source.source_path is not None
    
    async def load(self, data_source: DataSource) -> str:
        """加载文件内容"""
        if not data_source.source_path:
            raise ValueError("source_path is required for FileLoader")
        
        try:
            async with aiofiles.open(data_source.source_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                logger.info(f"Successfully loaded file: {data_source.source_path}")
                return content
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                async with aiofiles.open(data_source.source_path, 'r', encoding='gbk') as file:
                    content = await file.read()
                    logger.info(f"Successfully loaded file with GBK encoding: {data_source.source_path}")
                    return content
            except Exception as e:
                logger.error(f"Failed to load file with multiple encodings: {e}")
                raise

class ContentLoader(DataLoader):
    """内容加载器（直接从内容字段加载）"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        return data_source.content is not None
    
    async def load(self, data_source: DataSource) -> str:
        """直接返回内容"""
        if not data_source.content:
            raise ValueError("content is required for ContentLoader")
        
        logger.info(f"Successfully loaded content for source: {data_source.name}")
        return data_source.content

class DocumentLoader(DataLoader):
    """文档加载器（支持PDF、Word等）"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        if data_source.type != DataSourceType.DOCUMENT:
            return False
        
        if not data_source.source_path:
            return False
            
        supported_extensions = ['.md', '.markdown', '.txt', '.pdf', '.docx', '.doc']
        path = Path(data_source.source_path)
        return path.suffix.lower() in supported_extensions
    
    async def load(self, data_source: DataSource) -> str:
        """加载文档内容"""
        path = Path(data_source.source_path)
        extension = path.suffix.lower()
        
        try:
            if extension in ['.md', '.markdown', '.txt']:
                # 纯文本文件
                return await self._load_text_file(data_source.source_path)
            elif extension == '.pdf':
                # PDF文件
                return await self._load_pdf_file(data_source.source_path)
            elif extension in ['.docx', '.doc']:
                # Word文件
                return await self._load_word_file(data_source.source_path)
            else:
                raise ValueError(f"Unsupported document type: {extension}")
                
        except Exception as e:
            logger.error(f"Failed to load document {data_source.source_path}: {e}")
            raise
    
    async def _load_text_file(self, file_path: str) -> str:
        """加载纯文本文件"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            return await file.read()
    
    async def _load_pdf_file(self, file_path: str) -> str:
        """加载PDF文件"""
        try:
            # 需要安装 PyPDF2 或 pdfplumber
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
        """加载Word文件"""
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
    """代码文件加载器"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        if data_source.type != DataSourceType.CODE:
            return False
            
        if not data_source.source_path:
            return False
            
        supported_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb']
        path = Path(data_source.source_path)
        return path.suffix.lower() in supported_extensions
    
    async def load(self, data_source: DataSource) -> str:
        """加载代码文件"""
        try:
            async with aiofiles.open(data_source.source_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                
            # 添加代码特有的元数据
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
        """根据文件扩展名检测编程语言"""
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
    """SQL文件加载器"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        if data_source.type != DataSourceType.SQL:
            return False
            
        if data_source.source_path:
            path = Path(data_source.source_path)
            return path.suffix.lower() in ['.sql', '.ddl']
        
        # 也可以处理直接的SQL内容
        return data_source.content is not None
    
    async def load(self, data_source: DataSource) -> str:
        """加载SQL文件或内容"""
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
    """加载器注册表"""
    
    def __init__(self):
        self.loaders = [
            DocumentLoader(),
            CodeLoader(),
            SQLLoader(),
            FileLoader(),      # 通用文件加载器作为后备
            ContentLoader(),   # 内容加载器作为最后的后备
        ]
    
    def get_loader(self, data_source: DataSource) -> DataLoader:
        """根据数据源获取合适的加载器"""
        for loader in self.loaders:
            if loader.can_handle(data_source):
                return loader
        
        raise ValueError(f"No suitable loader found for data source: {data_source.name}")
    
    def add_loader(self, loader: DataLoader):
        """添加自定义加载器"""
        self.loaders.insert(0, loader)  # 新加载器优先级最高

# 全局加载器注册表实例
loader_registry = LoaderRegistry() 