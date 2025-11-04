from typing import List, Dict, Any, Optional, Tuple
import re
import ast
from loguru import logger

from .base import (
    DataTransformer, DataSource, DataSourceType, ProcessingResult,
    ProcessedChunk, ExtractedRelation, ChunkType
)

class DocumentTransformer(DataTransformer):
    """document transformer"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        return data_source.type == DataSourceType.DOCUMENT
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """transform document to chunks"""
        try:
            # detect document type
            if data_source.source_path and data_source.source_path.endswith('.md'):
                chunks = await self._transform_markdown(data_source, content)
            else:
                chunks = await self._transform_plain_text(data_source, content)
            
            return ProcessingResult(
                source_id=data_source.id,
                success=True,
                chunks=chunks,
                relations=[],  # document usually does not extract structured relations
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
        """transform Markdown document"""
        chunks = []
        
        # split by headers
        sections = self._split_by_headers(content)
        
        for i, (title, section_content) in enumerate(sections):
            if len(section_content.strip()) == 0:
                continue
                
            # if section is too long, further split
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
        """split content by Markdown headers"""
        lines = content.split('\n')
        sections = []
        current_title = None
        current_content = []
        
        for line in lines:
            # check if line is a header
            if re.match(r'^#{1,6}\s+', line):
                # save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                
                # start new section
                current_title = re.sub(r'^#{1,6}\s+', '', line).strip()
                current_content = []
            else:
                current_content.append(line)
        
        # save last section
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))
        
        return sections
    
    async def _transform_plain_text(self, data_source: DataSource, content: str) -> List[ProcessedChunk]:
        """transform plain text document"""
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
        """split text by size"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > self.chunk_size and current_chunk:
                # save current chunk
                chunks.append(' '.join(current_chunk))
                
                # start new chunk, keep overlap
                overlap_words = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_words + [word]
                current_size = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

class CodeTransformer(DataTransformer):
    """code transformer"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        return data_source.type == DataSourceType.CODE
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """transform code to chunks and relations"""
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
        """transform Python code"""
        chunks = []
        relations = []

        try:
            # use AST to parse Python code
            tree = ast.parse(content)

            # Extract imports FIRST (file-level relationships)
            import_relations = self._extract_python_imports(data_source, tree)
            relations.extend(import_relations)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # extract function
                    func_chunk = self._extract_function_chunk(data_source, content, node)
                    chunks.append(func_chunk)

                    # extract function call relations
                    func_relations = self._extract_function_relations(data_source, node)
                    relations.extend(func_relations)

                elif isinstance(node, ast.ClassDef):
                    # extract class
                    class_chunk = self._extract_class_chunk(data_source, content, node)
                    chunks.append(class_chunk)

                    # extract class inheritance relations
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
        """extract function code chunk"""
        lines = content.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        
        function_code = '\n'.join(lines[start_line:end_line])
        
        # extract function signature and docstring
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
        """extract class code chunk"""
        lines = content.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        
        class_code = '\n'.join(lines[start_line:end_line])
        
        # extract class information
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
        """extract function call relations"""
        relations = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                # function call relation
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
        """extract class inheritance relations"""
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

    def _extract_python_imports(self, data_source: DataSource, tree: ast.AST) -> List[ExtractedRelation]:
        """
        Extract Python import statements and create IMPORTS relationships.

        Handles:
        - import module
        - import module as alias
        - from module import name
        - from module import name as alias
        - from . import relative
        - from ..package import relative
        """
        relations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import module [as alias]
                for alias in node.names:
                    module_name = alias.name
                    relation = ExtractedRelation(
                        source_id=data_source.id,
                        from_entity=data_source.source_path or data_source.name,
                        to_entity=module_name,
                        relation_type="IMPORTS",
                        properties={
                            "from_type": "file",
                            "to_type": "module",
                            "import_type": "import",
                            "alias": alias.asname if alias.asname else None,
                            "module": module_name
                        }
                    )
                    relations.append(relation)

            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import name [as alias]
                module_name = node.module if node.module else ""
                level = node.level  # 0=absolute, 1+=relative (. or ..)

                # Construct full module path for relative imports
                if level > 0:
                    # Relative import (from . import or from .. import)
                    relative_prefix = "." * level
                    full_module = f"{relative_prefix}{module_name}" if module_name else relative_prefix
                else:
                    full_module = module_name

                for alias in node.names:
                    imported_name = alias.name

                    # Create import relation
                    relation = ExtractedRelation(
                        source_id=data_source.id,
                        from_entity=data_source.source_path or data_source.name,
                        to_entity=full_module,
                        relation_type="IMPORTS",
                        properties={
                            "from_type": "file",
                            "to_type": "module",
                            "import_type": "from_import",
                            "module": full_module,
                            "imported_name": imported_name,
                            "alias": alias.asname if alias.asname else None,
                            "is_relative": level > 0,
                            "level": level
                        }
                    )
                    relations.append(relation)

        return relations
    
    async def _transform_js_code(self, data_source: DataSource, content: str) -> ProcessingResult:
        """transform JavaScript/TypeScript code"""
        chunks = []
        relations = []

        # Extract imports FIRST (file-level relationships)
        import_relations = self._extract_js_imports(data_source, content)
        relations.extend(import_relations)

        # use regex to extract functions and classes (simplified version)

        # extract functions
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

        # extract classes
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

            # if there is inheritance relation, add relation
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

    def _extract_js_imports(self, data_source: DataSource, content: str) -> List[ExtractedRelation]:
        """
        Extract JavaScript/TypeScript import statements and create IMPORTS relationships.

        Handles:
        - import module from 'path'
        - import { named } from 'path'
        - import * as namespace from 'path'
        - import 'path' (side-effect)
        - const module = require('path')
        """
        relations = []

        # ES6 imports: import ... from '...'
        # Patterns:
        # - import defaultExport from 'module'
        # - import { export1, export2 } from 'module'
        # - import * as name from 'module'
        # - import 'module'
        es6_import_pattern = r'import\s+(?:(\w+)|(?:\{([^}]+)\})|(?:\*\s+as\s+(\w+)))?\s*(?:from\s+)?[\'"]([^\'"]+)[\'"]'

        for match in re.finditer(es6_import_pattern, content):
            default_import = match.group(1)
            named_imports = match.group(2)
            namespace_import = match.group(3)
            module_path = match.group(4)

            # Normalize module path (remove leading ./ and ../)
            normalized_path = module_path

            # Create import relation
            relation = ExtractedRelation(
                source_id=data_source.id,
                from_entity=data_source.source_path or data_source.name,
                to_entity=normalized_path,
                relation_type="IMPORTS",
                properties={
                    "from_type": "file",
                    "to_type": "module",
                    "import_type": "es6_import",
                    "module": normalized_path,
                    "default_import": default_import,
                    "named_imports": named_imports.strip() if named_imports else None,
                    "namespace_import": namespace_import,
                    "is_relative": module_path.startswith('.'),
                    "language": data_source.metadata.get("language", "javascript")
                }
            )
            relations.append(relation)

        # CommonJS require: const/var/let module = require('path')
        require_pattern = r'(?:const|var|let)\s+(\w+)\s*=\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'

        for match in re.finditer(require_pattern, content):
            variable_name = match.group(1)
            module_path = match.group(2)

            relation = ExtractedRelation(
                source_id=data_source.id,
                from_entity=data_source.source_path or data_source.name,
                to_entity=module_path,
                relation_type="IMPORTS",
                properties={
                    "from_type": "file",
                    "to_type": "module",
                    "import_type": "commonjs_require",
                    "module": module_path,
                    "variable_name": variable_name,
                    "is_relative": module_path.startswith('.'),
                    "language": data_source.metadata.get("language", "javascript")
                }
            )
            relations.append(relation)

        return relations
    
    async def _transform_generic_code(self, data_source: DataSource, content: str) -> ProcessingResult:
        """generic code transformation (split by line count)"""
        chunks = []
        lines = content.split('\n')
        chunk_size = 50  # each code chunk is 50 lines
        
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
    """SQL transformer"""
    
    def can_handle(self, data_source: DataSource) -> bool:
        """check if can handle the data source"""
        return data_source.type == DataSourceType.SQL
    
    async def transform(self, data_source: DataSource, content: str) -> ProcessingResult:
        """transform SQL to chunks and relations"""
        try:
            from ..sql_parser import sql_analyzer
            
            chunks = []
            relations = []
            
            # split SQL statements
            sql_statements = self._split_sql_statements(content)
            
            for i, sql in enumerate(sql_statements):
                if not sql.strip():
                    continue
                
                # parse SQL
                parse_result = sql_analyzer.parse_sql(sql)
                
                if parse_result.parsed_successfully:
                    # create SQL chunk
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
                    
                    # extract table relations
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
        """split SQL statements"""
        # simple split by semicolon, in actual application, more complex parsing may be needed
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
        
        # add last statement (if no semicolon at the end)
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements
    
    def _extract_table_relations(self, data_source: DataSource, parse_result) -> List[ExtractedRelation]:
        """extract table relations"""
        relations = []
        
        # extract table relations from JOIN
        for join in parse_result.joins:
            # simplified JOIN parsing, in actual application, more complex logic may be needed
            if "JOIN" in join and "ON" in join:
                # should parse specific JOIN relation
                # temporarily skip, because more complex SQL parsing is needed
                pass
        
        # extract relations from foreign key constraints (if any)
        # this needs to be added to SQL parser to detect foreign keys
        
        return relations

class TransformerRegistry:
    """transformer registry"""
    
    def __init__(self):
        self.transformers = [
            DocumentTransformer(),
            CodeTransformer(),
            SQLTransformer(),
        ]
    
    def get_transformer(self, data_source: DataSource) -> DataTransformer:
        """get suitable transformer for data source"""
        for transformer in self.transformers:
            if transformer.can_handle(data_source):
                return transformer
        
        raise ValueError(f"No suitable transformer found for data source: {data_source.name}")
    
    def add_transformer(self, transformer: DataTransformer):
        """add custom transformer"""
        self.transformers.insert(0, transformer)  # new transformer has highest priority

# global transformer registry instance
transformer_registry = TransformerRegistry() 