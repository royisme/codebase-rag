from typing import List, Dict, Any, Optional, Tuple
import re
import ast
from loguru import logger

from .base import (
    DataTransformer, DataSource, DataSourceType, ProcessingResult,
    ProcessedChunk, ExtractedRelation, ChunkType
)

class DocumentTransformer(DataTransformer):
    """文档转换器"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        return data_source.type == DataSourceType.DOCUMENT
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换文档为chunks"""
        try:
            # 检测文档类型
            if data_source.source_path and data_source.source_path.endswith('.md'):
                chunks = await self._transform_markdown(data_source, content)
            else:
                chunks = await self._transform_plain_text(data_source, content)
            
            return ProcessingResult(
                source_id=data_source.id,
                success=True,
                chunks=chunks,
                relations=[],  # 文档通常不提取结构化关系
                metadata={"transformer": "DocumentTransformer", "chunk_count": len(chunks)}
            )
            
        except Exception as e:
            logger.error(f"Failed to transform document {data_source.name}: {e}")
            return ProcessingResult(
                source_id=data_source.id,
                success=False,
                error_message=str(e)
            )
    
    async def _transform_markdown(self, data_source: DataSource, content: str) -> List[ProcessedChunk]:
        """转换Markdown文档"""
        chunks = []
        
        # 按标题分割
        sections = self._split_by_headers(content)
        
        for i, (title, section_content) in enumerate(sections):
            if len(section_content.strip()) == 0:
                continue
                
            # 如果章节太长，进一步切分
            if len(section_content) > self.chunk_size:
                sub_chunks = self._split_text_by_size(section_content)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunk = ProcessedChunk(
                        source_id=data_source.id,
                        chunk_type=ChunkType.DOCUMENT_SECTION,
                        content=sub_chunk,
                        title=f"{title} (Part {j+1})" if title else f"Section {i+1} (Part {j+1})",
                        metadata={
                            "section_index": i,
                            "sub_chunk_index": j,
                            "original_title": title,
                            "chunk_size": len(sub_chunk)
                        }
                    )
                    chunks.append(chunk)
            else:
                chunk = ProcessedChunk(
                    source_id=data_source.id,
                    chunk_type=ChunkType.DOCUMENT_SECTION,
                    content=section_content,
                    title=title or f"Section {i+1}",
                    metadata={
                        "section_index": i,
                        "original_title": title,
                        "chunk_size": len(section_content)
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_by_headers(self, content: str) -> List[Tuple[Optional[str], str]]:
        """按Markdown标题分割内容"""
        lines = content.split('\n')
        sections = []
        current_title = None
        current_content = []
        
        for line in lines:
            # 检查是否是标题行
            if re.match(r'^#{1,6}\s+', line):
                # 保存之前的章节
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                
                # 开始新章节
                current_title = re.sub(r'^#{1,6}\s+', '', line).strip()
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一个章节
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections
    
    async def _transform_plain_text(self, data_source: DataSource, content: str) -> List[ProcessedChunk]:
        """转换纯文本文档"""
        chunks = []
        text_chunks = self._split_text_by_size(content)
        
        for i, chunk_content in enumerate(text_chunks):
            chunk = ProcessedChunk(
                source_id=data_source.id,
                chunk_type=ChunkType.TEXT,
                content=chunk_content,
                title=f"Text Chunk {i+1}",
                metadata={
                    "chunk_index": i,
                    "chunk_size": len(chunk_content)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_text_by_size(self, text: str) -> List[str]:
        """按大小分割文本"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > self.chunk_size and current_chunk:
                # 保存当前chunk
                chunks.append(' '.join(current_chunk))
                
                # 开始新chunk，保留重叠
                overlap_words = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_words + [word]
                current_size = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

class CodeTransformer(DataTransformer):
    """代码转换器"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        return data_source.type == DataSourceType.CODE
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换代码为chunks和relations"""
        try:
            language = data_source.metadata.get("language", "unknown")
            
            if language == "python":
                return await self._transform_python_code(data_source, content)
            elif language in ["javascript", "typescript"]:
                return await self._transform_js_code(data_source, content)
            else:
                return await self._transform_generic_code(data_source, content)
                
        except Exception as e:
            logger.error(f"Failed to transform code {data_source.name}: {e}")
            return ProcessingResult(
                source_id=data_source.id,
                success=False,
                error_message=str(e)
            )
    
    async def _transform_python_code(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换Python代码"""
        chunks = []
        relations = []
        
        try:
            # 使用AST解析Python代码
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 提取函数
                    func_chunk = self._extract_function_chunk(data_source, content, node)
                    chunks.append(func_chunk)
                    
                    # 提取函数调用关系
                    func_relations = self._extract_function_relations(data_source, node)
                    relations.extend(func_relations)
                    
                elif isinstance(node, ast.ClassDef):
                    # 提取类
                    class_chunk = self._extract_class_chunk(data_source, content, node)
                    chunks.append(class_chunk)
                    
                    # 提取类继承关系
                    class_relations = self._extract_class_relations(data_source, node)
                    relations.extend(class_relations)
            
            return ProcessingResult(
                source_id=data_source.id,
                success=True,
                chunks=chunks,
                relations=relations,
                metadata={"transformer": "CodeTransformer", "language": "python"}
            )
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error in {data_source.name}, falling back to generic parsing: {e}")
            return await self._transform_generic_code(data_source, content)
    
    def _extract_function_chunk(self, data_source: DataSource, content: str, node: ast.FunctionDef) -> ProcessedChunk:
        """提取函数代码块"""
        lines = content.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        
        function_code = '\n'.join(lines[start_line:end_line])
        
        # 提取函数签名和文档字符串
        docstring = ast.get_docstring(node)
        args = [arg.arg for arg in node.args.args]
        
        return ProcessedChunk(
            source_id=data_source.id,
            chunk_type=ChunkType.CODE_FUNCTION,
            content=function_code,
            title=f"Function: {node.name}",
            summary=docstring or f"Function {node.name} with parameters: {', '.join(args)}",
            metadata={
                "function_name": node.name,
                "parameters": args,
                "line_start": start_line + 1,
                "line_end": end_line,
                "has_docstring": docstring is not None,
                "docstring": docstring
            }
        )
    
    def _extract_class_chunk(self, data_source: DataSource, content: str, node: ast.ClassDef) -> ProcessedChunk:
        """提取类代码块"""
        lines = content.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        
        class_code = '\n'.join(lines[start_line:end_line])
        
        # 提取类信息
        docstring = ast.get_docstring(node)
        base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        
        return ProcessedChunk(
            source_id=data_source.id,
            chunk_type=ChunkType.CODE_CLASS,
            content=class_code,
            title=f"Class: {node.name}",
            summary=docstring or f"Class {node.name} with methods: {', '.join(methods)}",
            metadata={
                "class_name": node.name,
                "base_classes": base_classes,
                "methods": methods,
                "line_start": start_line + 1,
                "line_end": end_line,
                "has_docstring": docstring is not None,
                "docstring": docstring
            }
        )
    
    def _extract_function_relations(self, data_source: DataSource, node: ast.FunctionDef) -> List[ExtractedRelation]:
        """提取函数调用关系"""
        relations = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                # 函数调用关系
                relation = ExtractedRelation(
                    source_id=data_source.id,
                    from_entity=node.name,
                    to_entity=child.func.id,
                    relation_type="CALLS",
                    properties={
                        "from_type": "function",
                        "to_type": "function"
                    }
                )
                relations.append(relation)
        
        return relations
    
    def _extract_class_relations(self, data_source: DataSource, node: ast.ClassDef) -> List[ExtractedRelation]:
        """提取类继承关系"""
        relations = []
        
        for base in node.bases:
            if isinstance(base, ast.Name):
                relation = ExtractedRelation(
                    source_id=data_source.id,
                    from_entity=node.name,
                    to_entity=base.id,
                    relation_type="INHERITS",
                    properties={
                        "from_type": "class",
                        "to_type": "class"
                    }
                )
                relations.append(relation)
        
        return relations
    
    async def _transform_js_code(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换JavaScript/TypeScript代码"""
        chunks = []
        relations = []
        
        # 使用正则表达式提取函数和类（简化版本）
        
        # 提取函数
        function_pattern = r'(function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*\}|const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{[^}]*\})'
        for match in re.finditer(function_pattern, content, re.MULTILINE | re.DOTALL):
            func_code = match.group(1)
            func_name = match.group(2) or match.group(3)
            
            chunk = ProcessedChunk(
                source_id=data_source.id,
                chunk_type=ChunkType.CODE_FUNCTION,
                content=func_code,
                title=f"Function: {func_name}",
                metadata={
                    "function_name": func_name,
                    "language": data_source.metadata.get("language", "javascript")
                }
            )
            chunks.append(chunk)
        
        # 提取类
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{[^}]*\}'
        for match in re.finditer(class_pattern, content, re.MULTILINE | re.DOTALL):
            class_code = match.group(0)
            class_name = match.group(1)
            parent_class = match.group(2)
            
            chunk = ProcessedChunk(
                source_id=data_source.id,
                chunk_type=ChunkType.CODE_CLASS,
                content=class_code,
                title=f"Class: {class_name}",
                metadata={
                    "class_name": class_name,
                    "parent_class": parent_class,
                    "language": data_source.metadata.get("language", "javascript")
                }
            )
            chunks.append(chunk)
            
            # 如果有继承关系，添加关系
            if parent_class:
                relation = ExtractedRelation(
                    source_id=data_source.id,
                    from_entity=class_name,
                    to_entity=parent_class,
                    relation_type="INHERITS",
                    properties={"from_type": "class", "to_type": "class"}
                )
                relations.append(relation)
        
        return ProcessingResult(
            source_id=data_source.id,
            success=True,
            chunks=chunks,
            relations=relations,
            metadata={"transformer": "CodeTransformer", "language": data_source.metadata.get("language")}
        )
    
    async def _transform_generic_code(self, data_source: DataSource, content: str) -> ProcessingResult:
        """通用代码转换（按行数分割）"""
        chunks = []
        lines = content.split('\n')
        chunk_size = 50  # 每个代码块50行
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_content = '\n'.join(chunk_lines)
            
            chunk = ProcessedChunk(
                source_id=data_source.id,
                chunk_type=ChunkType.CODE_MODULE,
                content=chunk_content,
                title=f"Code Chunk {i//chunk_size + 1}",
                metadata={
                    "chunk_index": i // chunk_size,
                    "line_start": i + 1,
                    "line_end": min(i + chunk_size, len(lines)),
                    "language": data_source.metadata.get("language", "unknown")
                }
            )
            chunks.append(chunk)
        
        return ProcessingResult(
            source_id=data_source.id,
            success=True,
            chunks=chunks,
            relations=[],
            metadata={"transformer": "CodeTransformer", "method": "generic"}
        )

class SQLTransformer(DataTransformer):
    """SQL转换器"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """判断是否能处理该数据源"""
        return data_source.type == DataSourceType.SQL
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """转换SQL为chunks和relations"""
        try:
            from ..sql_parser import sql_analyzer
            
            chunks = []
            relations = []
            
            # 分割SQL语句
            sql_statements = self._split_sql_statements(content)
            
            for i, sql in enumerate(sql_statements):
                if not sql.strip():
                    continue
                
                # 解析SQL
                parse_result = sql_analyzer.parse_sql(sql)
                
                if parse_result.parsed_successfully:
                    # 创建SQL块
                    chunk = ProcessedChunk(
                        source_id=data_source.id,
                        chunk_type=ChunkType.SQL_TABLE if parse_result.sql_type == 'create' else ChunkType.SQL_SCHEMA,
                        content=sql,
                        title=f"SQL Statement {i+1}: {parse_result.sql_type.upper()}",
                        summary=parse_result.explanation,
                        metadata={
                            "sql_type": parse_result.sql_type,
                            "tables": parse_result.tables,
                            "columns": parse_result.columns,
                            "functions": parse_result.functions,
                            "optimized_sql": parse_result.optimized_sql
                        }
                    )
                    chunks.append(chunk)
                    
                    # 提取表关系
                    table_relations = self._extract_table_relations(data_source, parse_result)
                    relations.extend(table_relations)
            
            return ProcessingResult(
                source_id=data_source.id,
                success=True,
                chunks=chunks,
                relations=relations,
                metadata={"transformer": "SQLTransformer", "statement_count": len(sql_statements)}
            )
            
        except Exception as e:
            logger.error(f"Failed to transform SQL {data_source.name}: {e}")
            return ProcessingResult(
                source_id=data_source.id,
                success=False,
                error_message=str(e)
            )
    
    def _split_sql_statements(self, content: str) -> List[str]:
        """分割SQL语句"""
        # 简单按分号分割，实际应用中可能需要更复杂的解析
        statements = []
        current_statement = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            current_statement.append(line)
            
            if line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # 添加最后一个语句（如果没有分号结尾）
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements
    
    def _extract_table_relations(self, data_source: DataSource, parse_result) -> List[ExtractedRelation]:
        """提取表关系"""
        relations = []
        
        # 从JOIN中提取表关系
        for join in parse_result.joins:
            # 简化的JOIN解析，实际应用中需要更复杂的逻辑
            if "JOIN" in join and "ON" in join:
                # 这里应该解析具体的JOIN关系
                # 暂时跳过，因为需要更复杂的SQL解析
                pass
        
        # 从外键约束中提取关系（如果有的话）
        # 这需要在SQL解析器中增加外键检测功能
        
        return relations

class TransformerRegistry:
    """转换器注册表"""
    
    def __init__(self):
        self.transformers = [
            DocumentTransformer(),
            CodeTransformer(),
            SQLTransformer(),
        ]
    
    def get_transformer(self, data_source: DataSource) -> DataTransformer:
        """根据数据源获取合适的转换器"""
        for transformer in self.transformers:
            if transformer.can_handle(data_source):
                return transformer
        
        raise ValueError(f"No suitable transformer found for data source: {data_source.name}")
    
    def add_transformer(self, transformer: DataTransformer):
        """添加自定义转换器"""
        self.transformers.insert(0, transformer)  # 新转换器优先级最高

# 全局转换器注册表实例
transformer_registry = TransformerRegistry() 