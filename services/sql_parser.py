import sqlglot
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from loguru import logger

class SQLParseResult(BaseModel):
    """SQL解析结果模型"""
    original_sql: str
    parsed_successfully: bool
    sql_type: Optional[str] = None
    tables: List[str] = []
    columns: List[str] = []
    conditions: List[str] = []
    joins: List[str] = []
    functions: List[str] = []
    syntax_errors: List[str] = []
    optimized_sql: Optional[str] = None
    explanation: Optional[str] = None

class SQLAnalysisService:
    """SQL分析服务"""
    
    def __init__(self):
        self.supported_dialects = [
            "mysql", "postgresql", "sqlite", "oracle", 
            "sqlserver", "bigquery", "snowflake", "redshift"
        ]
    
    def parse_sql(self, sql: str, dialect: str = "mysql") -> SQLParseResult:
        """
        解析SQL语句并提取关键信息
        
        Args:
            sql: SQL语句
            dialect: SQL方言
            
        Returns:
            SQLParseResult: 解析结果
        """
        result = SQLParseResult(
            original_sql=sql,
            parsed_successfully=False
        )
        
        try:
            # 解析SQL
            parsed = sqlglot.parse_one(sql, dialect=dialect)
            result.parsed_successfully = True
            
            # 提取SQL类型
            result.sql_type = parsed.__class__.__name__.lower()
            
            # 提取表名
            result.tables = self._extract_tables(parsed)
            
            # 提取列名
            result.columns = self._extract_columns(parsed)
            
            # 提取条件
            result.conditions = self._extract_conditions(parsed)
            
            # 提取JOIN
            result.joins = self._extract_joins(parsed)
            
            # 提取函数
            result.functions = self._extract_functions(parsed)
            
            # 生成优化建议
            result.optimized_sql = self._optimize_sql(sql, dialect)
            
            # 生成解释
            result.explanation = self._generate_explanation(parsed, result)
            
            logger.info(f"Successfully parsed SQL: {sql[:100]}...")
            
        except Exception as e:
            result.syntax_errors.append(str(e))
            logger.error(f"Failed to parse SQL: {e}")
        
        return result
    
    def _extract_tables(self, parsed) -> List[str]:
        """提取表名"""
        tables = []
        for table in parsed.find_all(sqlglot.expressions.Table):
            if table.name:
                tables.append(table.name)
        return list(set(tables))
    
    def _extract_columns(self, parsed) -> List[str]:
        """提取列名"""
        columns = []
        for column in parsed.find_all(sqlglot.expressions.Column):
            if column.name:
                columns.append(column.name)
        return list(set(columns))
    
    def _extract_conditions(self, parsed) -> List[str]:
        """提取WHERE条件"""
        conditions = []
        for where in parsed.find_all(sqlglot.expressions.Where):
            conditions.append(str(where.this))
        return conditions
    
    def _extract_joins(self, parsed) -> List[str]:
        """提取JOIN操作"""
        joins = []
        for join in parsed.find_all(sqlglot.expressions.Join):
            join_type = join.side if join.side else "INNER"
            join_table = str(join.this) if join.this else "unknown"
            join_condition = str(join.on) if join.on else "no condition"
            joins.append(f"{join_type} JOIN {join_table} ON {join_condition}")
        return joins
    
    def _extract_functions(self, parsed) -> List[str]:
        """提取函数调用"""
        functions = []
        for func in parsed.find_all(sqlglot.expressions.Anonymous):
            if func.this:
                functions.append(func.this)
        for func in parsed.find_all(sqlglot.expressions.Func):
            functions.append(func.__class__.__name__)
        return list(set(functions))
    
    def _optimize_sql(self, sql: str, dialect: str) -> str:
        """优化SQL语句"""
        try:
            # 使用sqlglot进行SQL优化
            optimized = sqlglot.optimize(sql, dialect=dialect)
            return str(optimized)
        except Exception as e:
            logger.warning(f"Failed to optimize SQL: {e}")
            return sql
    
    def _generate_explanation(self, parsed, result: SQLParseResult) -> str:
        """生成SQL解释"""
        explanation_parts = []
        
        if result.sql_type:
            explanation_parts.append(f"这是一个{result.sql_type.upper()}查询")
        
        if result.tables:
            tables_str = "、".join(result.tables)
            explanation_parts.append(f"涉及的表: {tables_str}")
        
        if result.columns:
            explanation_parts.append(f"查询了{len(result.columns)}个字段")
        
        if result.conditions:
            explanation_parts.append(f"包含{len(result.conditions)}个筛选条件")
        
        if result.joins:
            explanation_parts.append(f"使用了{len(result.joins)}个表连接")
        
        if result.functions:
            explanation_parts.append(f"使用了函数: {', '.join(result.functions)}")
        
        return "；".join(explanation_parts) if explanation_parts else "简单查询"
    
    def convert_between_dialects(self, sql: str, from_dialect: str, to_dialect: str) -> Dict[str, Any]:
        """在不同SQL方言之间转换"""
        try:
            # 解析原SQL
            parsed = sqlglot.parse_one(sql, dialect=from_dialect)
            
            # 转换到目标方言
            converted = parsed.sql(dialect=to_dialect)
            
            return {
                "success": True,
                "original_sql": sql,
                "converted_sql": converted,
                "from_dialect": from_dialect,
                "to_dialect": to_dialect
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_sql": sql,
                "from_dialect": from_dialect,
                "to_dialect": to_dialect
            }
    
    def validate_sql_syntax(self, sql: str, dialect: str = "mysql") -> Dict[str, Any]:
        """验证SQL语法"""
        try:
            sqlglot.parse_one(sql, dialect=dialect)
            return {
                "valid": True,
                "message": "SQL语法正确"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "SQL语法错误"
            }

# 全局SQL分析服务实例
sql_analyzer = SQLAnalysisService() 