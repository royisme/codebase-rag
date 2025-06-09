"""
任务处理器模块
定义不同类型任务的具体执行逻辑
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import json

from .task_storage import TaskType, Task

logger = logging.getLogger(__name__)

class TaskProcessor(ABC):
    """任务处理器基类"""
    
    @abstractmethod
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理任务的抽象方法"""
        pass
    
    def _update_progress(self, progress_callback: Optional[Callable], progress: float, message: str = ""):
        """更新任务进度"""
        if progress_callback:
            progress_callback(progress, message)

class DocumentProcessingProcessor(TaskProcessor):
    """文档处理任务处理器"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理文档处理任务"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting document processing")
            
            # 从载荷中提取参数
            document_content = payload.get("document_content")
            document_path = payload.get("document_path")
            document_type = payload.get("document_type", "text")
            
            if not document_content and not document_path:
                raise ValueError("Either document_content or document_path must be provided")
            
            # 如果提供了路径，读取文件内容
            if document_path and not document_content:
                self._update_progress(progress_callback, 20, "Reading document file")
                document_path = Path(document_path)
                if not document_path.exists():
                    raise FileNotFoundError(f"Document file not found: {document_path}")
                
                with open(document_path, 'r', encoding='utf-8') as f:
                    document_content = f.read()
            
            self._update_progress(progress_callback, 30, "Processing document content")
            
            # 使用Neo4j服务处理文档
            if self.neo4j_service:
                result = await self._process_with_neo4j(
                    document_content, document_type, progress_callback
                )
            else:
                # 模拟处理
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
    
    async def _process_with_neo4j(self, content: str, doc_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """使用Neo4j服务处理文档"""
        try:
            self._update_progress(progress_callback, 40, "Analyzing document structure")
            
            # 调用Neo4j服务的add_document方法
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
        """模拟文档处理（用于测试）"""
        self._update_progress(progress_callback, 50, "Simulating document analysis")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 70, "Simulating knowledge extraction")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 90, "Simulating graph construction")
        await asyncio.sleep(0.5)
        
        return {
            "nodes_created": len(content.split()) // 10,  # 模拟节点数
            "relationships_created": len(content.split()) // 20,  # 模拟关系数
            "processing_time": 2.5,
            "simulated": True
        }

class SchemaParsingProcessor(TaskProcessor):
    """数据库模式解析任务处理器"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理数据库模式解析任务"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting schema parsing")
            
            # 从载荷中提取参数
            schema_content = payload.get("schema_content")
            schema_path = payload.get("schema_path")
            schema_type = payload.get("schema_type", "sql")
            
            if not schema_content and not schema_path:
                raise ValueError("Either schema_content or schema_path must be provided")
            
            # 如果提供了路径，读取文件内容
            if schema_path and not schema_content:
                self._update_progress(progress_callback, 20, "Reading schema file")
                schema_path = Path(schema_path)
                if not schema_path.exists():
                    raise FileNotFoundError(f"Schema file not found: {schema_path}")
                
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_content = f.read()
            
            self._update_progress(progress_callback, 30, "Parsing schema structure")
            
            # 使用Neo4j服务处理模式
            if self.neo4j_service:
                result = await self._process_schema_with_neo4j(
                    schema_content, schema_type, progress_callback
                )
            else:
                # 模拟处理
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
        """使用Neo4j服务处理模式"""
        try:
            self._update_progress(progress_callback, 40, "Analyzing schema structure")
            
            # 调用Neo4j服务的相应方法
            if hasattr(self.neo4j_service, 'parse_schema'):
                result = await self.neo4j_service.parse_schema(content, schema_type)
            else:
                # 使用通用文档处理方法
                result = await self.neo4j_service.add_document(content, f"schema_{schema_type}")
            
            self._update_progress(progress_callback, 80, "Building schema graph")
            
            return result
            
        except Exception as e:
            logger.error(f"Neo4j schema processing failed: {e}")
            raise
    
    async def _simulate_schema_processing(self, content: str, schema_type: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """模拟模式处理（用于测试）"""
        self._update_progress(progress_callback, 50, "Simulating schema analysis")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 70, "Simulating table extraction")
        await asyncio.sleep(1)
        
        self._update_progress(progress_callback, 90, "Simulating relationship mapping")
        await asyncio.sleep(0.5)
        
        # 简单的SQL表计数模拟
        table_count = content.upper().count("CREATE TABLE")
        
        return {
            "tables_parsed": table_count,
            "relationships_found": table_count * 2,  # 模拟关系数
            "processing_time": 2.5,
            "schema_type": schema_type,
            "simulated": True
        }

class KnowledgeGraphConstructionProcessor(TaskProcessor):
    """知识图谱构建任务处理器"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理知识图谱构建任务"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting knowledge graph construction")
            
            # 从载荷中提取参数
            data_sources = payload.get("data_sources", [])
            construction_type = payload.get("construction_type", "full")
            
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
                
                # 处理单个数据源
                source_result = await self._process_data_source(source, progress_callback)
                results.append(source_result)
            
            self._update_progress(progress_callback, 80, "Integrating knowledge graph")
            
            # 整合结果
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
        """处理单个数据源"""
        source_type = source.get("type", "unknown")
        source_path = source.get("path")
        source_content = source.get("content")
        
        if self.neo4j_service:
            if source_content:
                return await self.neo4j_service.add_document(source_content, source_type)
            elif source_path:
                # 读取文件并处理
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return await self.neo4j_service.add_document(content, source_type)
        
        # 模拟处理
        await asyncio.sleep(0.5)
        return {
            "nodes_created": 10,
            "relationships_created": 5,
            "source_type": source_type,
            "simulated": True
        }
    
    async def _integrate_results(self, results: list, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """整合处理结果"""
        total_nodes = sum(r.get("nodes_created", 0) for r in results)
        total_relationships = sum(r.get("relationships_created", 0) for r in results)
        
        # 模拟整合过程
        await asyncio.sleep(1)
        
        return {
            "total_nodes_created": total_nodes,
            "total_relationships_created": total_relationships,
            "sources_integrated": len(results),
            "integration_time": 1.0
        }

class BatchProcessingProcessor(TaskProcessor):
    """批处理任务处理器"""
    
    def __init__(self, neo4j_service=None):
        self.neo4j_service = neo4j_service
    
    async def process(self, task: Task, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理批处理任务"""
        payload = task.payload
        
        try:
            self._update_progress(progress_callback, 10, "Starting batch processing")
            
            # 从载荷中提取参数
            directory_path = payload.get("directory_path")
            file_patterns = payload.get("file_patterns", ["*.txt", "*.md", "*.sql"])
            batch_size = payload.get("batch_size", 10)
            
            if not directory_path:
                raise ValueError("Directory path is required for batch processing")
            
            directory = Path(directory_path)
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            self._update_progress(progress_callback, 20, "Scanning directory for files")
            
            # 收集所有匹配的文件
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
            
            # 批量处理文件
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
            
            # 汇总结果
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
        """处理一批文件"""
        results = []
        
        for file_path in files:
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 确定文件类型
                file_type = file_path.suffix.lower().lstrip('.')
                
                # 处理文件
                if self.neo4j_service:
                    result = await self.neo4j_service.add_document(content, file_type)
                else:
                    # 模拟处理
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
        """汇总批处理结果"""
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
    """任务处理器注册表"""
    
    def __init__(self):
        self._processors: Dict[TaskType, TaskProcessor] = {}
    
    def register_processor(self, task_type: TaskType, processor: TaskProcessor):
        """注册任务处理器"""
        self._processors[task_type] = processor
        logger.info(f"Registered processor for task type: {task_type.value}")
    
    def get_processor(self, task_type: TaskType) -> Optional[TaskProcessor]:
        """获取任务处理器"""
        return self._processors.get(task_type)
    
    def initialize_default_processors(self, neo4j_service=None):
        """初始化默认的任务处理器"""
        self.register_processor(
            TaskType.DOCUMENT_PROCESSING, 
            DocumentProcessingProcessor(neo4j_service)
        )
        self.register_processor(
            TaskType.SCHEMA_PARSING, 
            SchemaParsingProcessor(neo4j_service)
        )
        self.register_processor(
            TaskType.KNOWLEDGE_GRAPH_CONSTRUCTION, 
            KnowledgeGraphConstructionProcessor(neo4j_service)
        )
        self.register_processor(
            TaskType.BATCH_PROCESSING, 
            BatchProcessingProcessor(neo4j_service)
        )
        
        logger.info("Initialized all default task processors")

# 全局处理器注册表
processor_registry = TaskProcessorRegistry()

# 便捷函数，用于API路由
async def process_document_task(**kwargs):
    """文档处理任务便捷函数"""
    # 这个函数会被任务队列调用，实际处理由处理器完成
    # 这里只是一个占位符，实际处理在TaskQueue._execute_task_by_type中完成
    pass

async def process_schema_parsing_task(**kwargs):
    """模式解析任务便捷函数"""
    # 这个函数会被任务队列调用，实际处理由处理器完成
    pass

async def process_knowledge_graph_task(**kwargs):
    """知识图谱构建任务便捷函数"""
    # 这个函数会被任务队列调用，实际处理由处理器完成
    pass

async def process_batch_task(**kwargs):
    """批处理任务便捷函数"""
    # 这个函数会被任务队列调用，实际处理由处理器完成
    pass 