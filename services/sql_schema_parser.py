"""
SQL Schema 解析服务
专门用于解析 ws_dundas 项目的数据库 schema 信息
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    constraints: List[str] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []

@dataclass
class TableInfo:
    """表信息"""
    schema_name: str
    table_name: str
    columns: List[ColumnInfo]
    primary_key: Optional[List[str]] = None
    foreign_keys: List[Dict] = None
    
    def __post_init__(self):
        if self.foreign_keys is None:
            self.foreign_keys = []

class SQLSchemaParser:
    """SQL Schema 解析器"""
    
    def __init__(self):
        self.tables: Dict[str, TableInfo] = {}
        
    def parse_schema_file(self, file_path: str) -> Dict[str, Any]:
        """解析SQL schema文件"""
        logger.info(f"Parsing SQL schema file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分析内容
            self._parse_content(content)
            
            # 生成分析报告
            analysis = self._generate_analysis()
            
            logger.success(f"Successfully parsed {len(self.tables)} tables")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse schema file: {e}")
            raise
    
    def _parse_content(self, content: str):
        """解析SQL内容"""
        # 清理内容，移除注释
        content = self._clean_sql_content(content)
        
        # 分割为语句
        statements = self._split_statements(content)
        
        for statement in statements:
            statement = statement.strip()
            if not statement:
                continue
                
            # 解析CREATE TABLE语句
            if statement.upper().startswith('CREATE TABLE'):
                self._parse_create_table(statement)
    
    def _clean_sql_content(self, content: str) -> str:
        """清理SQL内容"""
        # 移除单行注释
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content
    
    def _split_statements(self, content: str) -> List[str]:
        """分割SQL语句"""
        # 按照 / 分割语句（Oracle风格）
        statements = content.split('/')
        
        # 清理空语句
        return [stmt.strip() for stmt in statements if stmt.strip()]
    
    def _parse_create_table(self, statement: str):
        """解析CREATE TABLE语句"""
        try:
            # 提取表名
            table_match = re.search(r'create\s+table\s+(\w+)\.(\w+)', statement, re.IGNORECASE)
            if not table_match:
                return
            
            schema_name = table_match.group(1)
            table_name = table_match.group(2)
            
            # 提取列定义
            columns_section = re.search(r'\((.*)\)', statement, re.DOTALL)
            if not columns_section:
                return
            
            columns_text = columns_section.group(1)
            columns = self._parse_columns(columns_text)
            
            # 创建表信息
            table_info = TableInfo(
                schema_name=schema_name,
                table_name=table_name,
                columns=columns
            )
            
            self.tables[f"{schema_name}.{table_name}"] = table_info
            
            logger.debug(f"Parsed table: {schema_name}.{table_name} with {len(columns)} columns")
            
        except Exception as e:
            logger.warning(f"Failed to parse CREATE TABLE statement: {e}")
    
    def _parse_columns(self, columns_text: str) -> List[ColumnInfo]:
        """解析列定义"""
        columns = []
        
        # 分割列定义
        column_lines = self._split_column_definitions(columns_text)
        
        for line in column_lines:
            line = line.strip()
            if not line or line.upper().startswith('CONSTRAINT'):
                continue
            
            column = self._parse_single_column(line)
            if column:
                columns.append(column)
        
        return columns
    
    def _split_column_definitions(self, columns_text: str) -> List[str]:
        """分割列定义"""
        lines = []
        current_line = ""
        paren_count = 0
        
        for char in columns_text:
            current_line += char
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                lines.append(current_line[:-1])  # 移除逗号
                current_line = ""
        
        if current_line.strip():
            lines.append(current_line)
        
        return lines
    
    def _parse_single_column(self, line: str) -> Optional[ColumnInfo]:
        """解析单个列定义"""
        try:
            # 基本模式：列名 数据类型 [约束...]
            parts = line.strip().split()
            if len(parts) < 2:
                return None
            
            column_name = parts[0]
            data_type = parts[1]
            
            # 检查是否可空
            nullable = 'not null' not in line.lower()
            
            # 提取默认值
            default_value = None
            default_match = re.search(r'default\s+([^,\s]+)', line, re.IGNORECASE)
            if default_match:
                default_value = default_match.group(1).strip("'\"")
            
            # 提取约束
            constraints = []
            if 'primary key' in line.lower():
                constraints.append('PRIMARY KEY')
            if 'unique' in line.lower():
                constraints.append('UNIQUE')
            if 'check' in line.lower():
                constraints.append('CHECK')
            
            return ColumnInfo(
                name=column_name,
                data_type=data_type,
                nullable=nullable,
                default_value=default_value,
                constraints=constraints
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse column definition: {line} - {e}")
            return None
    
    def _generate_analysis(self) -> Dict[str, Any]:
        """生成分析报告"""
        # 按业务领域分类表
        business_domains = self._categorize_tables()
        
        # 统计信息
        stats = {
            "total_tables": len(self.tables),
            "total_columns": sum(len(table.columns) for table in self.tables.values()),
        }
        
        # 数据类型分析
        data_types = self._analyze_data_types()
        
        return {
            "project_name": "ws_dundas",
            "database_schema": "SKYTEST",
            "business_domains": business_domains,
            "statistics": stats,
            "data_types": data_types,
            "tables": {name: self._table_to_dict(table) for name, table in self.tables.items()}
        }
    
    def _categorize_tables(self) -> Dict[str, List[str]]:
        """按业务领域分类表"""
        domains = {
            "保单管理": [],
            "客户管理": [],
            "代理人管理": [],
            "产品管理": [],
            "基金管理": [],
            "佣金管理": [],
            "核保管理": [],
            "系统管理": [],
            "报表分析": [],
            "其他": []
        }
        
        for table_name in self.tables.keys():
            table_name_upper = table_name.upper()
            
            if any(keyword in table_name_upper for keyword in ['POLICY', 'PREMIUM']):
                domains["保单管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['CLIENT', 'CUSTOMER']):
                domains["客户管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['AGENT', 'ADVISOR']):
                domains["代理人管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['PRODUCT', 'PLAN']):
                domains["产品管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['FD_', 'FUND']):
                domains["基金管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['COMMISSION', 'COMM_']):
                domains["佣金管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['UNDERWRITING', 'UW_', 'RATING']):
                domains["核保管理"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['SUN_', 'REPORT', 'STAT']):
                domains["报表分析"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['TYPE_', 'CONFIG', 'PARAM', 'LOOKUP']):
                domains["系统管理"].append(table_name)
            else:
                domains["其他"].append(table_name)
        
        # 移除空的域
        return {k: v for k, v in domains.items() if v}
    
    def _analyze_data_types(self) -> Dict[str, int]:
        """分析数据类型分布"""
        type_counts = {}
        
        for table in self.tables.values():
            for column in table.columns:
                # 提取基本数据类型
                base_type = column.data_type.split('(')[0].upper()
                type_counts[base_type] = type_counts.get(base_type, 0) + 1
        
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _table_to_dict(self, table: TableInfo) -> Dict[str, Any]:
        """将表信息转换为字典"""
        return {
            "schema_name": table.schema_name,
            "table_name": table.table_name,
            "columns": [self._column_to_dict(col) for col in table.columns],
            "primary_key": table.primary_key,
            "foreign_keys": table.foreign_keys
        }
    
    def _column_to_dict(self, column: ColumnInfo) -> Dict[str, Any]:
        """将列信息转换为字典"""
        return {
            "name": column.name,
            "data_type": column.data_type,
            "nullable": column.nullable,
            "default_value": column.default_value,
            "constraints": column.constraints
        }
    
    def generate_documentation(self, analysis: Dict[str, Any]) -> str:
        """生成文档"""
        doc = f"""# {analysis['project_name']} 数据库架构文档

## 项目概述
- **项目名称**: {analysis['project_name']}
- **数据库Schema**: {analysis['database_schema']}

## 统计信息
- **总表数**: {analysis['statistics']['total_tables']}
- **总列数**: {analysis['statistics']['total_columns']}

## 业务领域分类
"""
        
        for domain, tables in analysis['business_domains'].items():
            doc += f"\n### {domain} ({len(tables)}个表)\n"
            for table in tables[:10]:  # 只显示前10个
                doc += f"- {table}\n"
            if len(tables) > 10:
                doc += f"- ... 还有 {len(tables) - 10} 个表\n"
        
        doc += f"""
## 数据类型分布
"""
        for data_type, count in list(analysis['data_types'].items())[:10]:
            doc += f"- **{data_type}**: {count} 个字段\n"
        
        return doc

# 全局解析器实例
sql_parser = SQLSchemaParser() 