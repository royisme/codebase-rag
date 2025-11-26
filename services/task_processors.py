"""
task processor module
define the specific execution logic for different types of tasks
"""

import asyncio
import datetime as dt
import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from loguru import logger

from .task_storage import TaskType, Task
from services.code_indexing import CodeIndexingPipeline
from services.source_service import get_source_service, update_job_with_new_session
from schemas import ParseJobUpdate

class TaskProcessor(ABC):
    """task processor base class"""
    
    @abstractmethod
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """abstract method to process tasks"""
        pass
    
    def _update_progress(self, progress_callback: Optional[Callable], progress: float, message: str = ""):
        """update task progress"""
        if progress_callback:
            # Convert percentage (0-100) to decimal (0.0-1.0) for task storage
            progress_callback(progress / 100.0, message)

class DocumentProcessingProcessor(TaskProcessor):
    """document processing task processor"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """process document processing task"""
        payload = task.payload
        
        try:
            logger.info(f"Task {task.id} - Starting document processing")
            self._update_progress(progress_callback, 10, "Starting document processing")
            
            # extract parameters from payload (parameters are nested under "kwargs")
            kwargs = payload.get("kwargs", {})
            document_content = kwargs.get("document_content")
            document_path = kwargs.get("document_path")
            document_type = kwargs.get("document_type", "text")
            temp_file_cleanup = kwargs.get("_temp_file", False)
            
            # Debug logging for large document issues
            logger.info(f"Task {task.id} - Content length: {len(document_content) if document_content else 'None'}")
            logger.info(f"Task {task.id} - Path provided: {document_path}")
            logger.info(f"Task {task.id} - Available kwargs keys: {list(kwargs.keys())}")
            logger.info(f"Task {task.id} - Full payload structure: task_name={payload.get('task_name')}, has_kwargs={bool(kwargs)}")
            
            if not document_content and not document_path:
                logger.error(f"Task {task.id} - Missing document content/path. Payload keys: {list(payload.keys())}")
                logger.error(f"Task {task.id} - Kwargs content: {kwargs}")
                logger.error(f"Task {task.id} - Document content type: {type(document_content)}, Path type: {type(document_path)}")
                raise ValueError("Either document_content or document_path must be provided")
            
            # if path is provided, read file content
            if document_path and not document_content:
                self._update_progress(progress_callback, 20, "Reading document file")
                document_path = Path(document_path)
                if not document_path.exists():
                    raise FileNotFoundError(f"Document file not found: {document_path}")
                
                with open(document_path, 'r', encoding='utf-8') as f:
                    document_content = f.read()
            
            self._update_progress(progress_callback, 30, "Processing document content")
            
            # use Neo4j service to process document
            if self.neo4j_service:
                result = await self._process_with_neo4j(
                    document_content, document_type, progress_callback
                )
            else:
                # simulate processing
                result = await self._simulate_processing(
                    document_content, document_type, progress_callback
                )
            
            self._update_progress(progress_callback, 100, "Document processing completed")
            
            return {
                "status": "success",
                "message": "Document processed successfully",
                "result": result,
                "document_type": document_type,
                "content_length": len(document_content) if document_content else 0
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise
        finally:
            # Clean up temporary file if it was created
            if temp_file_cleanup and document_path:
                try:
                    import os
                    if os.path.exists(document_path):
                        os.unlink(document_path)
                        logger.info(f"Cleaned up temporary file: {document_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file {document_path}: {cleanup_error}")
    
    async def _process_with_neo4j(self, content: str, doc_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """use Neo4j service to process document"""
        try:
            self._update_progress(progress_callback, 40, "Analyzing document structure")
            
            # call Neo4j service's add_document method
            result = await self.neo4j_service.add_document(content, doc_type)
            
            self._update_progress(progress_callback, 80, "Storing in knowledge graph")
            
            return {
                "nodes_created": result.get("nodes_created", 0),
                "relationships_created": result.get("relationships_created", 0),
                "processing_time": result.get("processing_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Neo4j processing failed: {e}")
            raise
    
    async def _simulate_processing(self, content: str, doc_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """simulate document processing (for testing)"""
        self._update_progress(progress_callback, 50, "Simulating document analysis")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 70, "Simulating knowledge extraction")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 90, "Simulating graph construction")
        await asyncio.sleep(0.5)
        
        return {
            "nodes_created": len(content.split()) // 10,  # simulate node count
            "relationships_created": len(content.split()) // 20,  # simulate relationship count
            "processing_time": 2.5,
            "simulated": True
        }

class SchemaParsingProcessor(TaskProcessor):
    """database schema parsing task processor"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """process database schema parsing task"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting schema parsing")
            
            # extract parameters from payload (parameters are nested under "kwargs")
            kwargs = payload.get("kwargs", {})
            schema_content = kwargs.get("schema_content")
            schema_path = kwargs.get("schema_path")
            schema_type = kwargs.get("schema_type", "sql")
            
            if not schema_content and not schema_path:
                raise ValueError("Either schema_content or schema_path must be provided")
            
            # if path is provided, read file content
            if schema_path and not schema_content:
                self._update_progress(progress_callback, 20, "Reading schema file")
                schema_path = Path(schema_path)
                if not schema_path.exists():
                    raise FileNotFoundError(f"Schema file not found: {schema_path}")
                
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_content = f.read()
            
            self._update_progress(progress_callback, 30, "Parsing schema structure")
            
            # use Neo4j service to process schema
            if self.neo4j_service:
                result = await self._process_schema_with_neo4j(
                    schema_content, schema_type, progress_callback
                )
            else:
                # simulate processing
                result = await self._simulate_schema_processing(
                    schema_content, schema_type, progress_callback
                )
            
            self._update_progress(progress_callback, 100, "Schema parsing completed")
            
            return {
                "status": "success",
                "message": "Schema parsed successfully",
                "result": result,
                "schema_type": schema_type,
                "content_length": len(schema_content) if schema_content else 0
            }
            
        except Exception as e:
            logger.error(f"Schema parsing failed: {e}")
            raise
    
    async def _process_schema_with_neo4j(self, content: str, schema_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """use Neo4j service to process schema"""
        try:
            self._update_progress(progress_callback, 40, "Analyzing schema structure")
            
            # call Neo4j service's corresponding method
            if hasattr(self.neo4j_service, 'parse_schema'):
                result = await self.neo4j_service.parse_schema(content, schema_type)
            else:
                # use generic document processing method
                result = await self.neo4j_service.add_document(content, f"schema_{schema_type}")
            
            self._update_progress(progress_callback, 80, "Building schema graph")
            
            return result
            
        except Exception as e:
            logger.error(f"Neo4j schema processing failed: {e}")
            raise
    
    async def _simulate_schema_processing(self, content: str, schema_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """simulate schema processing (for testing)"""
        self._update_progress(progress_callback, 50, "Simulating schema analysis")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 70, "Simulating table extraction")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 90, "Simulating relationship mapping")
        await asyncio.sleep(0.5)
        
        # simple SQL table count simulation
        table_count = content.upper().count("CREATE TABLE")
        
        return {
            "tables_parsed": table_count,
            "relationships_found": table_count * 2,  # simulate relationship count
            "processing_time": 2.5,
            "schema_type": schema_type,
            "simulated": True
        }

class KnowledgeGraphConstructionProcessor(TaskProcessor):
    """knowledge graph construction task processor"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """process knowledge graph construction task"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting knowledge graph construction")
            
            # extract parameters from payload (parameters are nested under "kwargs")
            kwargs = payload.get("kwargs", {})
            data_sources = kwargs.get("data_sources", [])
            construction_type = kwargs.get("construction_type", "full")
            
            if not data_sources:
                raise ValueError("No data sources provided for knowledge graph construction")
            
            self._update_progress(progress_callback, 20, "Processing data sources")
            
            total_sources = len(data_sources)
            results = []
            
            for i, source in enumerate(data_sources):
                source_progress = 20 + (60 * i / total_sources)
                self._update_progress(
                    progress_callback, 
                    source_progress, 
                    f"Processing source {i+1}/{total_sources}"
                )
                
                # process single data source
                source_result = await self._process_data_source(source, progress_callback)
                results.append(source_result)
            
            self._update_progress(progress_callback, 80, "Integrating knowledge graph")
            
            # integrate results
            final_result = await self._integrate_results(results, progress_callback)
            
            self._update_progress(progress_callback, 100, "Knowledge graph construction completed")
            
            return {
                "status": "success",
                "message": "Knowledge graph constructed successfully",
                "result": final_result,
                "sources_processed": total_sources,
                "construction_type": construction_type
            }
            
        except Exception as e:
            logger.error(f"Knowledge graph construction failed: {e}")
            raise
    
    async def _process_data_source(self, source: Dict[str, Any], progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """process single data source"""
        source_type = source.get("type", "unknown")
        source_path = source.get("path")
        source_content = source.get("content")
        
        if self.neo4j_service:
            if source_content:
                return await self.neo4j_service.add_document(source_content, source_type)
            elif source_path:
                # read file and process
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return await self.neo4j_service.add_document(content, source_type)
        
        # simulate processing
        await asyncio.sleep(0.5)
        return {
            "nodes_created": 10,
            "relationships_created": 5,
            "source_type": source_type,
            "simulated": True
        }
    
    async def _integrate_results(self, results: list, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """integrate processing results"""
        total_nodes = sum(r.get("nodes_created", 0) for r in results)
        total_relationships = sum(r.get("relationships_created", 0) for r in results)
        
        # simulate integration process
        await asyncio.sleep(1)
        
        return {
            "total_nodes_created": total_nodes,
            "total_relationships_created": total_relationships,
            "sources_integrated": len(results),
            "integration_time": 1.0
        }

class BatchProcessingProcessor(TaskProcessor):
    """batch processing task processor"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """process batch processing task"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting batch processing")
            
            # extract parameters from payload (parameters are nested under "kwargs")
            kwargs = payload.get("kwargs", {})
            directory_path = kwargs.get("directory_path")
            file_patterns = kwargs.get("file_patterns", ["*.txt", "*.md", "*.sql"])
            batch_size = kwargs.get("batch_size", 10)
            
            if not directory_path:
                raise ValueError("Directory path is required for batch processing")
            
            directory = Path(directory_path)
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            self._update_progress(progress_callback, 20, "Scanning directory for files")
            
            # collect all matching files
            files_to_process = []
            for pattern in file_patterns:
                files_to_process.extend(directory.glob(pattern))
            
            if not files_to_process:
                return {
                    "status": "success",
                    "message": "No files found to process",
                    "files_processed": 0
                }
            
            self._update_progress(progress_callback, 30, f"Found {len(files_to_process)} files to process")
            
            # batch process files
            results = []
            total_files = len(files_to_process)
            
            for i in range(0, total_files, batch_size):
                batch = files_to_process[i:i + batch_size]
                batch_progress = 30 + (60 * i / total_files)
                
                self._update_progress(
                    progress_callback, 
                    batch_progress, 
                    f"Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size}"
                )
                
                batch_result = await self._process_file_batch(batch, progress_callback)
                results.extend(batch_result)
            
            self._update_progress(progress_callback, 90, "Finalizing batch processing")
            
            # summarize results
            summary = self._summarize_batch_results(results)
            
            self._update_progress(progress_callback, 100, "Batch processing completed")
            
            return {
                "status": "success",
                "message": "Batch processing completed successfully",
                "result": summary,
                "files_processed": len(results),
                "directory_path": str(directory_path)
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
    
    async def _process_file_batch(self, files: list, progress_callback: Optional[Callable]) -> list:
        """process a batch of files"""
        results = []
        
        for file_path in files:
            try:
                # read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # determine file type
                file_type = file_path.suffix.lower().lstrip('.')
                
                # process file
                if self.neo4j_service:
                    result = await self.neo4j_service.add_document(content, file_type)
                else:
                    # simulate processing
                    await asyncio.sleep(0.1)
                    result = {
                        "nodes_created": len(content.split()) // 20,
                        "relationships_created": len(content.split()) // 40,
                        "simulated": True
                    }
                
                results.append({
                    "file_path": str(file_path),
                    "file_type": file_type,
                    "file_size": len(content),
                    "result": result,
                    "status": "success"
                })
                
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")
                results.append({
                    "file_path": str(file_path),
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _summarize_batch_results(self, results: list) -> Dict[str, Any]:
        """summarize batch processing results"""
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "failed"]
        
        total_nodes = sum(
            r.get("result", {}).get("nodes_created", 0) 
            for r in successful
        )
        total_relationships = sum(
            r.get("result", {}).get("relationships_created", 0) 
            for r in successful
        )
        total_size = sum(r.get("file_size", 0) for r in successful)
        
        return {
            "total_files": len(results),
            "successful_files": len(successful),
            "failed_files": len(failed),
            "total_nodes_created": total_nodes,
            "total_relationships_created": total_relationships,
            "total_content_size": total_size,
            "failed_file_paths": [r["file_path"] for r in failed]
        }

class TaskProcessorRegistry:
    """task processor registry"""
    
    def __init__(self):
        self._processors: Dict[TaskType, TaskProcessor] = {}
    
    def register_processor(self, task_type: TaskType, processor: TaskProcessor):
        """register task processor"""
        self._processors[task_type] = processor
        logger.info(f"Registered processor for task type: {task_type.value}")
    
    def get_processor(self, task_type: TaskType) -> Optional[TaskProcessor]:
        """get task processor"""
        return self._processors.get(task_type)
    
    def initialize_default_processors(self, knowledge_service=None, graph_service_obj=None):
        """initialize default task processors"""
        self.register_processor(
            TaskType.DOCUMENT_PROCESSING, 
            DocumentProcessingProcessor(knowledge_service)
        )
        self.register_processor(
            TaskType.SCHEMA_PARSING, 
            SchemaParsingProcessor(knowledge_service)
        )
        self.register_processor(
            TaskType.KNOWLEDGE_GRAPH_CONSTRUCTION, 
            KnowledgeGraphConstructionProcessor(knowledge_service)
        )
        self.register_processor(
            TaskType.BATCH_PROCESSING,
            BatchProcessingProcessor(knowledge_service)
        )
        self.register_processor(
            TaskType.KNOWLEDGE_SOURCE_SYNC,
            KnowledgeSourceSyncProcessor(neo4j_service=knowledge_service, graph_service=graph_service_obj)
        )

        logger.info("Initialized all default task processors")

class KnowledgeSourceSyncProcessor(TaskProcessor):
    """知识源同步任务处理器"""

    def __init__(self, source_service=None, neo4j_service=None, graph_service=None):
        self.source_service = source_service
        self.neo4j_service = neo4j_service
        self.graph_service = graph_service

    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理知识源同步任务"""
        payload = task.payload

        try:
            self._update_progress(progress_callback, 10, "开始知识源同步")

            # 从载荷中提取参数
            kwargs = payload.get("kwargs", {})
            source_id = kwargs.get("source_id")
            job_id = kwargs.get("job_id")
            sync_config = kwargs.get("sync_config", {})

            if not source_id:
                raise ValueError("缺少知识源ID")

            self._update_progress(progress_callback, 20, "验证知识源配置")

            # 使用数据库会话和源服务
            from database import async_session_factory
            from database.models import ParseStatus

            async with async_session_factory() as session:
                source_service = get_source_service(session)

                # 获取知识源
                source = await source_service.get_source_by_id(source_id)
                if not source:
                    raise ValueError(f"知识源 {source_id} 不存在")

                if not source.is_active:
                    raise ValueError(f"知识源 {source.name} 未激活")

                # 更新任务状态为运行中
                if job_id:
                    await update_job_with_new_session(
                        job_id,
                        ParseJobUpdate(status=ParseStatus.RUNNING),
                    )

                self._update_progress(progress_callback, 30, f"开始同步知识源: {source.name}")

                # 根据源类型执行不同的同步逻辑
                result = await self._sync_by_source_type(
                    source,
                    sync_config,
                    progress_callback,
                    job_id=job_id,
                    session=session,
                    source_service=source_service,
                )

                self._update_progress(progress_callback, 90, "完成同步后处理")

                # Pipeline 已经更新了 source.source_metadata 和 source.last_synced_at
                # 这里只需要提交会话即可
                await session.commit()
                logger.info(f"知识源 {source.id} 同步完成，已提交更改")
                logger.debug(f"最终元数据: {source.source_metadata}")

                # 更新任务状态为完成
                if job_id:
                    await update_job_with_new_session(
                        job_id,
                        ParseJobUpdate(
                            status=ParseStatus.COMPLETED,
                            progress_percentage=100,
                            result_summary=result,
                        ),
                    )

                self._update_progress(progress_callback, 100, "知识源同步完成")

                return {
                    "status": "success",
                    "message": f"知识源 {source.name} 同步成功",
                    "source_id": str(source.id),
                    "source_name": source.name,
                    "source_type": source.source_type,
                    "sync_result": result,
                    "sync_time": dt.datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"知识源同步失败: {e}")

            # 更新任务状态为失败
            if job_id:
                try:
                    from database.models import ParseStatus

                    await update_job_with_new_session(
                        job_id,
                        ParseJobUpdate(
                            status=ParseStatus.FAILED,
                            error_message=str(e),
                        ),
                    )
                except Exception as update_error:
                    logger.error(f"更新任务状态失败: {update_error}")

            raise

    async def _sync_by_source_type(
        self,
        source,
        sync_config: Dict[str, Any],
        progress_callback: Optional[Callable],
        *,
        job_id: Optional[str],
        session,
        source_service,
    ) -> Dict[str, Any]:
        """根据知识源类型执行同步"""
        source_type = source.source_type

        if source_type == "database":
            return await self._sync_database_source(source, sync_config, progress_callback)
        elif source_type == "api":
            return await self._sync_api_source(source, sync_config, progress_callback)
        elif source_type == "website":
            return await self._sync_website_source(source, sync_config, progress_callback)
        elif source_type == "document":
            return await self._sync_document_source(source, sync_config, progress_callback)
        elif source_type == "code":
            return await self._sync_code_source(
                source,
                sync_config,
                progress_callback,
                job_id=job_id,
                session=session,
                source_service=source_service,
            )
        else:
            # 默认处理
            return await self._sync_generic_source(source, sync_config, progress_callback)

    async def _sync_database_source(self, source, sync_config, progress_callback) -> Dict[str, Any]:
        """同步数据库知识源"""
        self._update_progress(progress_callback, 40, "连接数据库")

        connection_config = source.connection_config or {}

        # 这里应该实现具体的数据库连接和schema提取逻辑
        # 暂时返回模拟结果
        await asyncio.sleep(1)
        self._update_progress(progress_callback, 60, "提取数据库schema")

        await asyncio.sleep(1)
        self._update_progress(progress_callback, 80, "存储schema到知识图谱")

        # 如果有Neo4j服务，实际处理
        if self.neo4j_service:
            # 实际的处理逻辑
            pass

        return {
            "tables_found": 10,
            "relationships_found": 15,
            "nodes_created": 25,
            "processing_time": 2.0
        }

    async def _sync_api_source(self, source, sync_config, progress_callback) -> Dict[str, Any]:
        """同步API知识源"""
        self._update_progress(progress_callback, 40, "调用API端点")

        await asyncio.sleep(0.5)
        self._update_progress(progress_callback, 70, "处理API响应数据")

        await asyncio.sleep(0.5)
        self._update_progress(progress_callback, 90, "构建知识图谱")

        return {
            "endpoints_called": 5,
            "records_processed": 100,
            "nodes_created": 50,
            "processing_time": 1.5
        }

    async def _sync_website_source(self, source, sync_config, progress_callback) -> Dict[str, Any]:
        """同步网站知识源"""
        self._update_progress(progress_callback, 40, "爬取网站内容")

        await asyncio.sleep(1)
        self._update_progress(progress_callback, 70, "解析网页结构")

        await asyncio.sleep(1)
        self._update_progress(progress_callback, 90, "提取知识实体")

        return {
            "pages_crawled": 8,
            "content_extracted": "15KB",
            "nodes_created": 30,
            "processing_time": 2.5
        }

    async def _sync_document_source(self, source, sync_config, progress_callback) -> Dict[str, Any]:
        """同步文档知识源"""
        self._update_progress(progress_callback, 40, "解析文档内容")

        await asyncio.sleep(0.8)
        self._update_progress(progress_callback, 70, "提取文档结构")

        await asyncio.sleep(0.8)
        self._update_progress(progress_callback, 90, "构建文档图谱")

        return {
            "documents_processed": 3,
            "chapters_found": 12,
            "nodes_created": 40,
            "processing_time": 2.0
        }

    async def _sync_code_source(
        self,
        source,
        sync_config,
        progress_callback,
        *,
        job_id: Optional[str],
        session,
        source_service,
    ) -> Dict[str, Any]:
        """同步代码知识源"""

        pipeline = CodeIndexingPipeline(
            source_service=source_service,
            session=session,
            graph_service=self.graph_service,
        )

        result = await pipeline.run(
            source=source,
            job_id=job_id,
            sync_config=sync_config,
            progress_callback=None,
            task_progress_callback=progress_callback,
        )

        return asdict(result)

    async def _sync_generic_source(self, source, sync_config, progress_callback) -> Dict[str, Any]:
        """同步通用知识源"""
        self._update_progress(progress_callback, 50, "处理通用数据源")

        await asyncio.sleep(1)
        self._update_progress(progress_callback, 80, "构建知识图谱")

        return {
            "items_processed": 20,
            "nodes_created": 35,
            "processing_time": 1.8
        }

# 全局处理器注册表
processor_registry = TaskProcessorRegistry()

# convenience function for API routing
async def process_document_task(**kwargs):
    """document processing task convenience function"""
    # this function will be called by task queue, actual processing is done in TaskQueue._execute_task_by_type
    pass

async def process_schema_parsing_task(**kwargs):
    """schema parsing task convenience function"""
    # this function will be called by task queue, actual processing is done in TaskQueue._execute_task_by_type
    pass

async def process_knowledge_graph_task(**kwargs):
    """knowledge graph construction task convenience function"""
    # this function will be called by task queue, actual processing is done in TaskQueue._execute_task_by_type
    pass

async def process_batch_task(**kwargs):
    """batch processing task convenience function"""
    # this function will be called by task queue, actual processing is done in TaskQueue._execute_task_by_type
    pass 
