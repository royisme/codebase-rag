"""
Universal SQL Schema Parser with Configurable Business Domain Classification
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml
from loguru import logger

@dataclass
class ColumnInfo:
    """Column information"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    constraints: List[str] = field(default_factory=list)

@dataclass 
class TableInfo:
    """Table information"""
    schema_name: str
    table_name: str
    columns: List[ColumnInfo]
    primary_key: Optional[List[str]] = field(default_factory=list)
    foreign_keys: List[Dict] = field(default_factory=list)

@dataclass
class ParsingConfig:
    """Parsing configuration"""
    project_name: str = "Unknown Project"
    database_schema: str = "Unknown Schema"
    
    # Business domain classification rules
    business_domains: Dict[str, List[str]] = field(default_factory=dict)
    
    # SQL dialect settings
    statement_separator: str = "/"  # Oracle uses /, MySQL uses ;
    comment_patterns: List[str] = field(default_factory=lambda: [r'--.*$', r'/\*.*?\*/'])
    
    # Parsing rules
    table_name_pattern: str = r'create\s+table\s+(\w+)\.(\w+)'
    column_section_pattern: str = r'\((.*)\)'
    
    # Output settings
    include_statistics: bool = True
    include_data_types_analysis: bool = True
    include_documentation: bool = True

class UniversalSQLSchemaParser:
    """Universal SQL Schema parser with configurable business domain classification"""
    
    def __init__(self, config: Optional[ParsingConfig] = None):
        self.config = config or ParsingConfig()
        self.tables: Dict[str, TableInfo] = {}
        
    @classmethod
    def from_config_file(cls, config_path: str):
        """Create parser from configuration file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_path.suffix.lower() in ['.yml', '.yaml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        else:
            raise ValueError("Configuration file must be YAML or JSON format")
        
        config = ParsingConfig(**config_data)
        return cls(config)
    
    def set_business_domains(self, domains: Dict[str, List[str]]):
        """Set business domain classification rules"""
        self.config.business_domains = domains
        
    def parse_schema_file(self, file_path: str) -> Dict[str, Any]:
        """Parse SQL schema file"""
        logger.info(f"Parsing SQL schema file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean content
            content = self._clean_sql_content(content)
            
            # Split into statements  
            statements = self._split_statements(content)
            
            # Parse each statement
            for statement in statements:
                statement = statement.strip()
                if not statement:
                    continue
                    
                if statement.upper().startswith('CREATE TABLE'):
                    self._parse_create_table(statement)
            
            # Generate analysis
            analysis = self._generate_analysis()
            
            logger.success(f"Successfully parsed {len(self.tables)} tables")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse schema file: {e}")
            raise
    
    def _clean_sql_content(self, content: str) -> str:
        """Clean SQL content by removing comments"""
        for pattern in self.config.comment_patterns:
            if pattern.endswith('$'):
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            else:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
        return content
    
    def _split_statements(self, content: str) -> List[str]:
        """Split SQL statements"""
        statements = content.split(self.config.statement_separator)
        return [stmt.strip() for stmt in statements if stmt.strip()]
    
    def _parse_create_table(self, statement: str):
        """Parse CREATE TABLE statement"""
        try:
            # Extract table name using configurable pattern
            table_match = re.search(self.config.table_name_pattern, statement, re.IGNORECASE)
            if not table_match:
                return
            
            schema_name = table_match.group(1)
            table_name = table_match.group(2)
            
            # Extract column definitions
            columns_section = re.search(self.config.column_section_pattern, statement, re.DOTALL)
            if not columns_section:
                return
            
            columns_text = columns_section.group(1)
            columns = self._parse_columns(columns_text)
            
            # Create table information
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
        """Parse column definitions"""
        columns = []
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
        """Split column definitions"""
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
                lines.append(current_line[:-1])
                current_line = ""
        
        if current_line.strip():
            lines.append(current_line)
        
        return lines
    
    def _parse_single_column(self, line: str) -> Optional[ColumnInfo]:
        """Parse single column definition"""
        try:
            parts = line.strip().split()
            if len(parts) < 2:
                return None
            
            column_name = parts[0]
            data_type = parts[1]
            
            # Check if nullable
            nullable = 'not null' not in line.lower()
            
            # Extract default value
            default_value = None
            default_match = re.search(r'default\s+([^,\s]+)', line, re.IGNORECASE)
            if default_match:
                default_value = default_match.group(1).strip("'\"")
            
            # Extract constraints
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
    
    def _categorize_tables(self) -> Dict[str, List[str]]:
        """Categorize tables using configurable business domain rules"""
        if not self.config.business_domains:
            # Return simple categorization if no rules defined
            return {"uncategorized": list(self.tables.keys())}
        
        categorized = {domain: [] for domain in self.config.business_domains.keys()}
        categorized["uncategorized"] = []
        
        for table_name in self.tables.keys():
            table_name_upper = table_name.upper()
            categorized_flag = False
            
            # Check each business domain
            for domain, keywords in self.config.business_domains.items():
                if any(keyword.upper() in table_name_upper for keyword in keywords):
                    categorized[domain].append(table_name)
                    categorized_flag = True
                    break
            
            # If not categorized, put in uncategorized
            if not categorized_flag:
                categorized["uncategorized"].append(table_name)
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
    
    def _analyze_data_types(self) -> Dict[str, int]:
        """Analyze data type distribution"""
        if not self.config.include_data_types_analysis:
            return {}
        
        type_counts = {}
        for table in self.tables.values():
            for column in table.columns:
                base_type = column.data_type.split('(')[0].upper()
                type_counts[base_type] = type_counts.get(base_type, 0) + 1
        
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _generate_analysis(self) -> Dict[str, Any]:
        """Generate analysis report"""
        analysis = {
            "project_name": self.config.project_name,
            "database_schema": self.config.database_schema,
            "tables": {name: self._table_to_dict(table) for name, table in self.tables.items()}
        }
        
        if self.config.include_statistics:
            analysis["statistics"] = {
                "total_tables": len(self.tables),
                "total_columns": sum(len(table.columns) for table in self.tables.values()),
            }
        
        # Business domain categorization
        analysis["business_domains"] = self._categorize_tables()
        
        # Data types analysis
        if self.config.include_data_types_analysis:
            analysis["data_types"] = self._analyze_data_types()
        
        return analysis
    
    def _table_to_dict(self, table: TableInfo) -> Dict[str, Any]:
        """Convert table information to dictionary"""
        return {
            "schema_name": table.schema_name,
            "table_name": table.table_name,
            "columns": [self._column_to_dict(col) for col in table.columns],
            "primary_key": table.primary_key,
            "foreign_keys": table.foreign_keys
        }
    
    def _column_to_dict(self, column: ColumnInfo) -> Dict[str, Any]:
        """Convert column information to dictionary"""
        return {
            "name": column.name,
            "data_type": column.data_type,
            "nullable": column.nullable,
            "default_value": column.default_value,
            "constraints": column.constraints
        }
    
    def generate_documentation(self, analysis: Dict[str, Any]) -> str:
        """Generate documentation"""
        if not self.config.include_documentation:
            return ""
        
        doc = f"""# {analysis['project_name']} Database Schema Documentation

## Project Overview
- **Project Name**: {analysis['project_name']}
- **Database Schema**: {analysis['database_schema']}

"""
        
        if "statistics" in analysis:
            stats = analysis["statistics"]
            doc += f"""## Statistics
- **Total Tables**: {stats['total_tables']}
- **Total Columns**: {stats['total_columns']}

"""
        
        if analysis.get("business_domains"):
            doc += "## Business Domain Classification\n"
            for domain, tables in analysis["business_domains"].items():
                doc += f"\n### {domain.replace('_', ' ').title()} ({len(tables)} tables)\n"
                for table in tables[:10]:
                    doc += f"- {table}\n"
                if len(tables) > 10:
                    doc += f"- ... and {len(tables) - 10} more tables\n"
        
        if analysis.get("data_types"):
            doc += "\n## Data Type Distribution\n"
            for data_type, count in list(analysis["data_types"].items())[:10]:
                doc += f"- **{data_type}**: {count} fields\n"
        
        return doc

# Predefined configurations for common business domains

class BusinessDomainTemplates:
    """Predefined business domain templates"""
    
    INSURANCE = {
        "policy_management": ["POLICY", "PREMIUM", "COVERAGE", "CLAIM"],
        "customer_management": ["CLIENT", "CUSTOMER", "INSURED", "CONTACT"],
        "agent_management": ["AGENT", "ADVISOR", "BROKER", "SALES"],
        "product_management": ["PRODUCT", "PLAN", "BENEFIT", "RIDER"],
        "fund_management": ["FD_", "FUND", "INVESTMENT", "PORTFOLIO"],
        "commission_management": ["COMMISSION", "COMM_", "PAYMENT", "PAYABLE"],
        "underwriting_management": ["UNDERWRITING", "UW_", "RATING", "RISK"],
        "system_management": ["TYPE_", "CONFIG", "PARAM", "LOOKUP", "SETTING"],
        "report_analysis": ["SUN_", "REPORT", "STAT", "ANALYTICS"]
    }
    
    ECOMMERCE = {
        "product_catalog": ["PRODUCT", "CATEGORY", "ITEM", "SKU"],
        "order_management": ["ORDER", "CART", "CHECKOUT", "PAYMENT"],
        "customer_management": ["CUSTOMER", "USER", "PROFILE", "ACCOUNT"],
        "inventory_management": ["INVENTORY", "STOCK", "WAREHOUSE", "SUPPLIER"],
        "shipping_logistics": ["SHIPPING", "DELIVERY", "ADDRESS", "TRACKING"],
        "financial_management": ["INVOICE", "PAYMENT", "TRANSACTION", "BILLING"],
        "marketing_promotion": ["PROMOTION", "DISCOUNT", "COUPON", "CAMPAIGN"],
        "analytics_reporting": ["ANALYTICS", "REPORT", "METRICS", "LOG"]
    }
    
    BANKING = {
        "account_management": ["ACCOUNT", "BALANCE", "HOLDER", "PROFILE"],
        "transaction_processing": ["TRANSACTION", "TRANSFER", "PAYMENT", "DEPOSIT"],
        "loan_credit": ["LOAN", "CREDIT", "MORTGAGE", "DEBT"],
        "investment_trading": ["INVESTMENT", "PORTFOLIO", "TRADE", "SECURITY"],
        "customer_service": ["CUSTOMER", "CLIENT", "CONTACT", "SUPPORT"],
        "compliance_risk": ["COMPLIANCE", "RISK", "AUDIT", "REGULATION"],
        "card_services": ["CARD", "ATM", "POS", "TERMINAL"],
        "system_admin": ["CONFIG", "PARAM", "SETTING", "TYPE_", "STATUS"]
    }
    
    HEALTHCARE = {
        "patient_management": ["PATIENT", "PERSON", "CONTACT", "DEMOGRAPHICS"],
        "medical_records": ["MEDICAL", "RECORD", "HISTORY", "DIAGNOSIS"],
        "appointment_scheduling": ["APPOINTMENT", "SCHEDULE", "CALENDAR", "BOOKING"],
        "billing_insurance": ["BILLING", "INSURANCE", "CLAIM", "PAYMENT"],
        "pharmacy_medication": ["MEDICATION", "PRESCRIPTION", "DRUG", "PHARMACY"],
        "staff_management": ["STAFF", "DOCTOR", "NURSE", "EMPLOYEE"],
        "facility_equipment": ["FACILITY", "ROOM", "EQUIPMENT", "DEVICE"],
        "system_configuration": ["CONFIG", "SETTING", "TYPE_", "LOOKUP"]
    }

def create_insurance_parser() -> UniversalSQLSchemaParser:
    """Create parser configured for insurance business"""
    config = ParsingConfig(
        project_name="Insurance Management System",
        business_domains=BusinessDomainTemplates.INSURANCE
    )
    return UniversalSQLSchemaParser(config)

def create_ecommerce_parser() -> UniversalSQLSchemaParser:
    """Create parser configured for e-commerce business"""
    config = ParsingConfig(
        project_name="E-commerce Platform",
        business_domains=BusinessDomainTemplates.ECOMMERCE
    )
    return UniversalSQLSchemaParser(config)

def create_banking_parser() -> UniversalSQLSchemaParser:
    """Create parser configured for banking business"""
    config = ParsingConfig(
        project_name="Banking System",
        business_domains=BusinessDomainTemplates.BANKING
    )
    return UniversalSQLSchemaParser(config)

def create_healthcare_parser() -> UniversalSQLSchemaParser:
    """Create parser configured for healthcare business"""
    config = ParsingConfig(
        project_name="Healthcare Management System", 
        business_domains=BusinessDomainTemplates.HEALTHCARE
    )
    return UniversalSQLSchemaParser(config)