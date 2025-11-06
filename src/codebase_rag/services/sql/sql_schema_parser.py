"""
SQL Schema parser service
used to parse database schema information for SQL dump file
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class ColumnInfo:
    """column information"""
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
    """table information"""
    schema_name: str
    table_name: str
    columns: List[ColumnInfo]
    primary_key: Optional[List[str]] = None
    foreign_keys: List[Dict] = None
    
    def __post_init__(self):
        if self.foreign_keys is None:
            self.foreign_keys = []

class SQLSchemaParser:
    """SQL Schema parser"""
    
    def __init__(self):
        self.tables: Dict[str, TableInfo] = {}
        
    def parse_schema_file(self, file_path: str) -> Dict[str, Any]:
        """parse SQL schema file"""
        logger.info(f"Parsing SQL schema file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # analyze content
            self._parse_content(content)
            
            # generate analysis report
            analysis = self._generate_analysis()
            
            logger.success(f"Successfully parsed {len(self.tables)} tables")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse schema file: {e}")
            raise
    
    def _parse_content(self, content: str):
        """parse SQL content"""
        # clean content, remove comments
        content = self._clean_sql_content(content)
        
        # split into statements
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
        """split SQL statements"""
        # split by / (Oracle style)
        statements = content.split('/')
        
        # clean empty statements
        return [stmt.strip() for stmt in statements if stmt.strip()]
    
    def _parse_create_table(self, statement: str):
        """parse CREATE TABLE statement"""
        try:
            # extract table name
            table_match = re.search(r'create\s+table\s+(\w+)\.(\w+)', statement, re.IGNORECASE)
            if not table_match:
                return
            
            schema_name = table_match.group(1)
            table_name = table_match.group(2)
            
            # extract column definitions
            columns_section = re.search(r'\((.*)\)', statement, re.DOTALL)
            if not columns_section:
                return
            
            columns_text = columns_section.group(1)
            columns = self._parse_columns(columns_text)
            
            # create table information
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
        """parse column definitions"""
        columns = []
        
        # split column definitions
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
        """split column definitions"""
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
                lines.append(current_line[:-1])  # remove comma
                current_line = ""
        
        if current_line.strip():
            lines.append(current_line)
        
        return lines
    
    def _parse_single_column(self, line: str) -> Optional[ColumnInfo]:
        """parse single column definition"""
        try:
            # basic pattern: column name data type [constraints...]
            parts = line.strip().split()
            if len(parts) < 2:
                return None
            
            column_name = parts[0]
            data_type = parts[1]
            
            # check if nullable
            nullable = 'not null' not in line.lower()
            
            # extract default value
            default_value = None
            default_match = re.search(r'default\s+([^,\s]+)', line, re.IGNORECASE)
            if default_match:
                default_value = default_match.group(1).strip("'\"")
            
            # extract constraints
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
        """generate analysis report"""
        # categorize tables by business domains
        business_domains = self._categorize_tables()
        
        # statistics
        stats = {
            "total_tables": len(self.tables),
            "total_columns": sum(len(table.columns) for table in self.tables.values()),
        }
        
        # analyze data types
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
        """categorize tables by business domains"""
        domains = {
            "policy_management": [],
            "customer_management": [],
            "agent_management": [],
            "product_management": [],
            "fund_management": [],
            "commission_management": [],
            "underwriting_management": [],
            "system_management": [],
            "report_analysis": [],
            "other": []
        }
        
        for table_name in self.tables.keys():
            table_name_upper = table_name.upper()
            
            if any(keyword in table_name_upper for keyword in ['POLICY', 'PREMIUM']):
                domains["policy_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['CLIENT', 'CUSTOMER']):
                domains["customer_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['AGENT', 'ADVISOR']):
                domains["agent_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['PRODUCT', 'PLAN']):
                domains["product_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['FD_', 'FUND']):
                domains["fund_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['COMMISSION', 'COMM_']):
                domains["commission_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['UNDERWRITING', 'UW_', 'RATING']):
                domains["underwriting_management"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['SUN_', 'REPORT', 'STAT']):
                domains["report_analysis"].append(table_name)
            elif any(keyword in table_name_upper for keyword in ['TYPE_', 'CONFIG', 'PARAM', 'LOOKUP']):
                domains["system_management"].append(table_name)
            else:
                domains["other"].append(table_name)
        
        # remove empty domains
        return {k: v for k, v in domains.items() if v}
    
    def _analyze_data_types(self) -> Dict[str, int]:
        """analyze data type distribution"""
        type_counts = {}
        
        for table in self.tables.values():
            for column in table.columns:
                # extract basic data type
                base_type = column.data_type.split('(')[0].upper()
                type_counts[base_type] = type_counts.get(base_type, 0) + 1
        
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _table_to_dict(self, table: TableInfo) -> Dict[str, Any]:
        """convert table information to dictionary"""
        return {
            "schema_name": table.schema_name,
            "table_name": table.table_name,
            "columns": [self._column_to_dict(col) for col in table.columns],
            "primary_key": table.primary_key,
            "foreign_keys": table.foreign_keys
        }
    
    def _column_to_dict(self, column: ColumnInfo) -> Dict[str, Any]:
        """convert column information to dictionary"""
        return {
            "name": column.name,
            "data_type": column.data_type,
            "nullable": column.nullable,
            "default_value": column.default_value,
            "constraints": column.constraints
        }
    
    def generate_documentation(self, analysis: Dict[str, Any]) -> str:
        """generate documentation"""
        doc = f"""# {analysis['project_name']} database schema documentation

## project overview
- **project name**: {analysis['project_name']}
- **database schema**: {analysis['database_schema']}

## statistics
- **total tables**: {analysis['statistics']['total_tables']}
- **total columns**: {analysis['statistics']['total_columns']}

## business domain classification
"""
        
        for domain, tables in analysis['business_domains'].items():
            doc += f"\n### {domain} ({len(tables)} tables)\n"
            for table in tables[:10]:  # only show first 10 tables
                doc += f"- {table}\n"
            if len(tables) > 10:
                doc += f"- ... and {len(tables) - 10} more tables\n"
        
        doc += f"""
## data type distribution
"""
        for data_type, count in list(analysis['data_types'].items())[:10]:
            doc += f"- **{data_type}**: {count} fields\n"
        
        return doc

# global parser instance
sql_parser = SQLSchemaParser() 