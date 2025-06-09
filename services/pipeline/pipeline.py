from typing import List, Dict, Any, Optional
import asyncio
from loguru import logger

from .base import (
    DataSource, ProcessingResult, DataSourceType, 
    detect_data_source_type, extract_file_metadata
)
from .loaders import loader_registry
from .transformers import transformer_registry
from .embeddings import get_default_embedding_generator
from .storers import storer_registry, setup_default_storers

class KnowledgePipeline:
    """知识库构建流水线"""
    
    def __init__(self, 
                 embedding_generator=None,
                 default_storer="hybrid",
                 chunk_size: int = 512,
                 chunk_overlap: int = 50):
        self.embedding_generator = embedding_generator or get_default_embedding_generator()
        self.default_storer = default_storer
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 处理统计
        self.stats = {
            "total_sources": 0,
            "successful_sources": 0,
            "failed_sources": 0,
            "total_chunks": 0,
            "total_relations": 0
        }
    
    async def process_file(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理单个文件"""
        # 检测文件类型和创建数据源
        data_source_type = detect_data_source_type(file_path)
        metadata = extract_file_metadata(file_path)
        
        data_source = DataSource(
            name=metadata["filename"],
            type=data_source_type,
            source_path=file_path,
            metadata=metadata
        )
        
        return await self.process_data_source(data_source, **kwargs)
    
    async def process_content(self, 
                            content: str, 
                            name: str,
                            source_type: DataSourceType = DataSourceType.DOCUMENT,
                            metadata: Dict[str, Any] = None,
                            **kwargs) -> ProcessingResult:
        """处理直接提供的内容"""
        data_source = DataSource(
            name=name,
            type=source_type,
            content=content,
            metadata=metadata or {}
        )
        
        return await self.process_data_source(data_source, **kwargs)
    
    async def process_data_source(self, 
                                data_source: DataSource,
                                storer_name: Optional[str] = None,
                                generate_embeddings: bool = True,
                                **kwargs) -> ProcessingResult:
        """处理单个数据源 - 核心ETL流程"""
        
        self.stats["total_sources"] += 1
        
        try:
            logger.info(f"Processing data source: {data_source.name} (type: {data_source.type.value})")
            
            # Step 1: Load/Extract - 加载数据
            logger.debug(f"Step 1: Loading data for {data_source.name}")
            loader = loader_registry.get_loader(data_source)
            content = await loader.load(data_source)
            
            if not content.strip():
                raise ValueError("Empty content after loading")
            
            logger.info(f"Loaded {len(content)} characters from {data_source.name}")
            
            # Step 2: Transform/Chunk - 转换和切分
            logger.debug(f"Step 2: Transforming data for {data_source.name}")
            transformer = transformer_registry.get_transformer(data_source)
            processing_result = await transformer.transform(data_source, content)
            
            if not processing_result.success:
                raise Exception(processing_result.error_message or "Transformation failed")
            
            logger.info(f"Generated {len(processing_result.chunks)} chunks and {len(processing_result.relations)} relations")
            
            # Step 3: Generate Embeddings - 生成嵌入向量
            if generate_embeddings:
                logger.debug(f"Step 3: Generating embeddings for {data_source.name}")
                await self._generate_embeddings_for_chunks(processing_result.chunks)
                logger.info(f"Generated embeddings for {len(processing_result.chunks)} chunks")
            
            # Step 4: Store - 存储数据
            logger.debug(f"Step 4: Storing data for {data_source.name}")
            storer_name = storer_name or self.default_storer
            storer = storer_registry.get_storer(storer_name)
            
            # 并行存储chunks和relations
            store_chunks_task = storer.store_chunks(processing_result.chunks)
            store_relations_task = storer.store_relations(processing_result.relations)
            
            chunks_result, relations_result = await asyncio.gather(
                store_chunks_task, 
                store_relations_task,
                return_exceptions=True
            )
            
            # 处理存储结果
            storage_success = True
            storage_errors = []
            
            if isinstance(chunks_result, Exception):
                storage_success = False
                storage_errors.append(f"Chunks storage failed: {chunks_result}")
            elif not chunks_result.get("success", False):
                storage_success = False
                storage_errors.append(f"Chunks storage failed: {chunks_result.get('error', 'Unknown error')}")
            
            if isinstance(relations_result, Exception):
                storage_success = False
                storage_errors.append(f"Relations storage failed: {relations_result}")
            elif not relations_result.get("success", False):
                storage_success = False
                storage_errors.append(f"Relations storage failed: {relations_result.get('error', 'Unknown error')}")
            
            # 更新统计信息
            if storage_success:
                self.stats["successful_sources"] += 1
                self.stats["total_chunks"] += len(processing_result.chunks)
                self.stats["total_relations"] += len(processing_result.relations)
            else:
                self.stats["failed_sources"] += 1
            
            # 更新处理结果
            processing_result.metadata.update({
                "pipeline_stats": self.stats.copy(),
                "storage_chunks_result": chunks_result if not isinstance(chunks_result, Exception) else str(chunks_result),
                "storage_relations_result": relations_result if not isinstance(relations_result, Exception) else str(relations_result),
                "storage_success": storage_success,
                "storage_errors": storage_errors
            })
            
            if not storage_success:
                processing_result.success = False
                processing_result.error_message = "; ".join(storage_errors)
            
            logger.info(f"Successfully processed {data_source.name}: {len(processing_result.chunks)} chunks, {len(processing_result.relations)} relations")
            
            return processing_result
            
        except Exception as e:
            self.stats["failed_sources"] += 1
            logger.error(f"Failed to process data source {data_source.name}: {e}")
            
            return ProcessingResult(
                source_id=data_source.id,
                success=False,
                error_message=str(e),
                metadata={"pipeline_stats": self.stats.copy()}
            )
    
    async def process_batch(self, 
                          data_sources: List[DataSource],
                          storer_name: Optional[str] = None,
                          generate_embeddings: bool = True,
                          max_concurrency: int = 5) -> List[ProcessingResult]:
        """批量处理数据源"""
        
        logger.info(f"Starting batch processing of {len(data_sources)} data sources")
        
        # 创建信号量来限制并发数
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_with_semaphore(data_source: DataSource) -> ProcessingResult:
            async with semaphore:
                return await self.process_data_source(
                    data_source, 
                    storer_name=storer_name,
                    generate_embeddings=generate_embeddings
                )
        
        # 并行处理所有数据源
        tasks = [process_with_semaphore(ds) for ds in data_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessingResult(
                    source_id=data_sources[i].id,
                    success=False,
                    error_message=str(result),
                    metadata={"pipeline_stats": self.stats.copy()}
                ))
            else:
                processed_results.append(result)
        
        logger.info(f"Batch processing completed: {self.stats['successful_sources']} successful, {self.stats['failed_sources']} failed")
        
        return processed_results
    
    async def process_directory(self,
                              directory_path: str,
                              recursive: bool = True,
                              file_patterns: List[str] = None,
                              exclude_patterns: List[str] = None,
                              **kwargs) -> List[ProcessingResult]:
        """处理目录中的所有文件"""
        import os
        import fnmatch
        from pathlib import Path
        
        # 默认文件模式
        if file_patterns is None:
            file_patterns = [
                "*.md", "*.txt", "*.pdf", "*.docx", "*.doc",  # 文档
                "*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.h",  # 代码
                "*.sql", "*.ddl",  # SQL
                "*.json", "*.yaml", "*.yml"  # 配置
            ]
        
        if exclude_patterns is None:
            exclude_patterns = [
                ".*", "node_modules/*", "__pycache__/*", "*.pyc", "*.log"
            ]
        
        # 收集文件
        files_to_process = []
        
        for root, dirs, files in os.walk(directory_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory_path)
                
                # 检查文件模式
                if any(fnmatch.fnmatch(file, pattern) for pattern in file_patterns):
                    # 检查排除模式
                    if not any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_patterns):
                        files_to_process.append(file_path)
            
            if not recursive:
                break
        
        logger.info(f"Found {len(files_to_process)} files to process in {directory_path}")
        
        # 创建数据源
        data_sources = []
        for file_path in files_to_process:
            try:
                data_source_type = detect_data_source_type(file_path)
                metadata = extract_file_metadata(file_path)
                
                data_source = DataSource(
                    name=metadata["filename"],
                    type=data_source_type,
                    source_path=file_path,
                    metadata=metadata
                )
                data_sources.append(data_source)
                
            except Exception as e:
                logger.warning(f"Failed to create data source for {file_path}: {e}")
        
        # 批量处理
        return await self.process_batch(data_sources, **kwargs)
    
    async def _generate_embeddings_for_chunks(self, chunks):
        """为chunks生成嵌入向量"""
        if not chunks:
            return
        
        # 批量生成嵌入向量
        texts = [chunk.content for chunk in chunks]
        
        try:
            embeddings = await self.embedding_generator.generate_embeddings(texts)
            
            # 将嵌入向量分配给对应的chunk
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
                
        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
            # 如果批量生成失败，尝试逐个生成
            for chunk in chunks:
                try:
                    embedding = await self.embedding_generator.generate_embedding(chunk.content)
                    chunk.embedding = embedding
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for chunk {chunk.id}: {e}")
                    chunk.embedding = None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_sources": 0,
            "successful_sources": 0,
            "failed_sources": 0,
            "total_chunks": 0,
            "total_relations": 0
        }

# 工厂函数
def create_pipeline(vector_service, graph_service, **config) -> KnowledgePipeline:
    """创建知识库构建流水线"""
    from .embeddings import EmbeddingGeneratorFactory
    from .storers import setup_default_storers
    
    # 设置默认存储器
    setup_default_storers(vector_service, graph_service)
    
    # 创建嵌入生成器
    embedding_config = config.get("embedding", {})
    embedding_generator = None
    
    if embedding_config:
        try:
            embedding_generator = EmbeddingGeneratorFactory.create_generator(embedding_config)
            logger.info(f"Created embedding generator: {embedding_config.get('provider', 'default')}")
        except Exception as e:
            logger.warning(f"Failed to create embedding generator: {e}, using default")
    
    # 创建流水线
    pipeline = KnowledgePipeline(
        embedding_generator=embedding_generator,
        default_storer=config.get("default_storer", "hybrid"),
        chunk_size=config.get("chunk_size", 512),
        chunk_overlap=config.get("chunk_overlap", 50)
    )
    
    logger.info("Knowledge pipeline created successfully")
    return pipeline 