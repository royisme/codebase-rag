import sqlglot
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from loguru import logger

class SQLParseResult(BaseModel):
    """SQL parse result"""
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
    """SQL analysis service"""
    
    def __init__(self):
        self.supported_dialects = [
            "mysql", "postgresql", "sqlite", "oracle", 
            "sqlserver", "bigquery", "snowflake", "redshift"
        ]
    
    def parse_sql(self, sql: str, dialect: str = "mysql") -> SQLParseResult:
        """
        parse SQL statement and extract key information
        
        Args:
            sql: SQL statement
            dialect: SQL dialect
            
        Returns:
            SQLParseResult: parse result
        """
        result = SQLParseResult(
            original_sql=sql,
            parsed_successfully=False
        )
        
        try:
            # parse SQL
            parsed = sqlglot.parse_one(sql, dialect=dialect)
            result.parsed_successfully = True
            
            # extract SQL type
            result.sql_type = parsed.__class__.__name__.lower()
            
            # extract table names
            result.tables = self._extract_tables(parsed)
            
            # extract column names
            result.columns = self._extract_columns(parsed)
            
            # extract conditions
            result.conditions = self._extract_conditions(parsed)
            
            # extract JOIN
            result.joins = self._extract_joins(parsed)
            
            # extract functions
            result.functions = self._extract_functions(parsed)
            
            # generate optimization suggestion
            result.optimized_sql = self._optimize_sql(sql, dialect)
            
            # generate explanation
            result.explanation = self._generate_explanation(parsed, result)
            
            logger.info(f"Successfully parsed SQL: {sql[:100]}...")
            
        except Exception as e:
            result.syntax_errors.append(str(e))
            logger.error(f"Failed to parse SQL: {e}")
        
        return result
    
    def _extract_tables(self, parsed) -> List[str]:
        """extract table names"""
        tables = []
        for table in parsed.find_all(sqlglot.expressions.Table):
            if table.name:
                tables.append(table.name)
        return list(set(tables))
    
    def _extract_columns(self, parsed) -> List[str]:
        """extract column names"""
        columns = []
        for column in parsed.find_all(sqlglot.expressions.Column):
            if column.name:
                columns.append(column.name)
        return list(set(columns))
    
    def _extract_conditions(self, parsed) -> List[str]:
        """extract WHERE conditions"""
        conditions = []
        for where in parsed.find_all(sqlglot.expressions.Where):
            conditions.append(str(where.this))
        return conditions
    
    def _extract_joins(self, parsed) -> List[str]:
        """extract JOIN operations"""
        joins = []
        for join in parsed.find_all(sqlglot.expressions.Join):
            join_type = join.side if join.side else "INNER"
            join_table = str(join.this) if join.this else "unknown"
            join_condition = str(join.on) if join.on else "no condition"
            joins.append(f"{join_type} JOIN {join_table} ON {join_condition}")
        return joins
    
    def _extract_functions(self, parsed) -> List[str]:
        """extract function calls"""
        functions = []
        for func in parsed.find_all(sqlglot.expressions.Anonymous):
            if func.this:
                functions.append(func.this)
        for func in parsed.find_all(sqlglot.expressions.Func):
            functions.append(func.__class__.__name__)
        return list(set(functions))
    
    def _optimize_sql(self, sql: str, dialect: str) -> str:
        """optimize SQL statement"""
        try:
            # use sqlglot to optimize SQL
            optimized = sqlglot.optimize(sql, dialect=dialect)
            return str(optimized)
        except Exception as e:
            logger.warning(f"Failed to optimize SQL: {e}")
            return sql
    
    def _generate_explanation(self, parsed, result: SQLParseResult) -> str:
        """generate SQL explanation"""
        explanation_parts = []
        
        if result.sql_type:
            explanation_parts.append(f"this is a {result.sql_type.upper()} query")
        
        if result.tables:
            tables_str = "、".join(result.tables)
            explanation_parts.append(f"involved tables: {tables_str}")
        
        if result.columns:
            explanation_parts.append(f"query {len(result.columns)} columns")
        
        if result.conditions:
            explanation_parts.append(f"contains {len(result.conditions)} conditions")
        
        if result.joins:
            explanation_parts.append(f"uses {len(result.joins)} table joins")
        
        if result.functions:
            explanation_parts.append(f"uses functions: {', '.join(result.functions)}")
        
        return "；".join(explanation_parts) if explanation_parts else "simple query"
    
    def convert_between_dialects(self, sql: str, from_dialect: str, to_dialect: str) -> Dict[str, Any]:
        """convert between dialects"""
        try:
            # parse original SQL
            parsed = sqlglot.parse_one(sql, dialect=from_dialect)
            
            # convert to target dialect
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
        """validate SQL syntax"""
        try:
            sqlglot.parse_one(sql, dialect=dialect)
            return {
                "valid": True,
                "message": "SQL syntax is correct"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "SQL syntax error"
            }

# global SQL analysis service instance
sql_analyzer = SQLAnalysisService() 