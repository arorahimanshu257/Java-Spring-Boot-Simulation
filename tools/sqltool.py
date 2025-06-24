from typing import Any, Type, Union, List
import re
from urllib.parse import parse_qs, urlparse

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from helpers.logger_config import logger


class NL2SQLToolInput(BaseModel):
    sql_query: str = Field(
        title="SQL Query",
        description="The SQL query to execute.",
    )


class SQLTool(BaseTool):
    name: str = "NL2SQLTool"
    description: str = """Converts natural language to SQL queries and executes them.
    Input of the tool should always be in the format below
    REQUIRED INPUT FORMAT: {"sql_query": "YOUR SQL QUERY HERE"}
    IMPORTANT: Always use fully qualified table names with schema (schema_name.table_name) in your queries.
    For example, use 'sales.customers' instead of just 'customers' when the table is in a non-public schema."""
    db_uri: str = Field(
        title="Database URI",
        description="The URI of the database to connect to.",
    )
    tables: list = []
    columns: dict = {}
    relationships: dict = {} 
    target_schemas: List[str] = []
    args_schema: Type[BaseModel] = NL2SQLToolInput

    def model_post_init(self, __context: Any) -> None:
        self.target_schemas = self._extract_schemas_from_uri(self.db_uri)
        
        if not self.target_schemas:
            self.target_schemas = ['public']  
            
        
        schema_condition = " OR ".join([f"t.table_schema = '{schema}'" for schema in self.target_schemas])
        
        schema_data = self.execute_sql(
            f"""
            SELECT 
                t.table_schema,
                t.table_name,
                c.column_name,
                c.data_type
            FROM 
                information_schema.tables t
            JOIN 
                information_schema.columns c 
                ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE 
                ({schema_condition})
                AND t.table_type = 'BASE TABLE'
            ORDER BY 
                t.table_schema, t.table_name, c.ordinal_position;
            """
        )
        
        schema_condition = " OR ".join([f"tc.table_schema = '{schema}'" for schema in self.target_schemas])
        foreign_schema_condition = " OR ".join([f"ccu.table_schema = '{schema}'" for schema in self.target_schemas])

        relationship_data = self.execute_sql(
            f"""
            SELECT
                tc.table_schema as schema_name,
                tc.table_name as table_name,
                kcu.column_name as column_name,
                ccu.table_schema AS foreign_schema_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints tc
            JOIN
                information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN
                information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE
                (({schema_condition}) OR ({foreign_schema_condition}))
                AND tc.constraint_type = 'FOREIGN KEY';
            """
        )
        
        data = {}
        tables = []
        seen_tables = set()
        
        for row in schema_data:
            schema = row["table_schema"]
            table = row["table_name"]
            qualified_name = f"{schema}.{table}"
            
            if qualified_name not in seen_tables:
                tables.append({"table_schema": schema, "table_name": table})
                seen_tables.add(qualified_name)
                data[f'{qualified_name}_columns'] = []
            
            data[f'{qualified_name}_columns'].append({
                "column_name": row["column_name"],
                "data_type": row["data_type"]
            })

        relationships = {}
        for row in relationship_data:
            source_schema = row["schema_name"]
            source_table = row["table_name"]
            source_column = row["column_name"]
            target_schema = row["foreign_schema_name"]
            target_table = row["foreign_table_name"]
            target_column = row["foreign_column_name"]
            
            source_qualified = f"{source_schema}.{source_table}"
            target_qualified = f"{target_schema}.{target_table}"
            
            if source_qualified not in relationships:
                relationships[source_qualified] = []
            
            relationships[source_qualified].append({
                "column": source_column,
                "references_table": target_qualified,
                "references_column": target_column
            })
        
        self.tables = tables
        self.columns = data
        self.relationships = relationships

    def _extract_schemas_from_uri(self, db_uri: str) -> List[str]:
        """Extract the schemas from the database URI if present."""
        try:
            parsed_url = urlparse(db_uri)
            
            if parsed_url.query:
                query_params = parse_qs(parsed_url.query)
                options = query_params.get('options', [])
                
                for option in options:
                    search_path_match = re.search(r'search_path=([^&]+)', option)
                    if search_path_match:
                        schemas_str = search_path_match.group(1)
                        schemas = [s.strip() for s in schemas_str.split(',')]
                        return schemas
            
            return []
        except Exception as e:
            logger.error(f"Error extracting schema from URI: {e}")
            return []
            
    def _format_relationships_for_prompt(self) -> str:
        """Format relationship data in a clear, readable way for the prompt."""
        formatted_text = ""
        for source_table, relations in self.relationships.items():
            formatted_text += f"{source_table} has the following foreign keys:\n"
            for relation in relations:
                formatted_text += f"  - {source_table}.{relation['column']} → {relation['references_table']}.{relation['references_column']}\n"
        
        if not formatted_text:
            return "No relationships found between tables."
        
        return formatted_text

    def _run(self, sql_query: str):
        try:
            data = self.execute_sql(sql_query) 
        except Exception as exc:
            data = (
            f"ERROR ANALYSIS:\n"
            f"Original query: {sql_query}\n"
            f"Error encountered: {exc}\n\n"
            f"Available tables:{self.tables}\n"
            f"Available columns:{self.columns}\n"
            f"RELATIONSHIPS:\n{self._format_relationships_for_prompt()}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Use fully qualified table names (schema_name.table_name) in your queries\n"
            f"2. Construct appropriate JOIN conditions based on the relationships above\n"
            f"3. If any queries require join, ensure you're using joins correctly based on the defined relationships\n"
            f"4. Make sure you are generating queries based on the available tables and columns only\n"
            f"5. If a particular table is not present in the schema which is in db uri, please mention this clearly\n"
            )

        return data

    def execute_sql(self, sql_query: str) -> Union[list, str]:
        engine = create_engine(self.db_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            result = session.execute(text(sql_query))
            session.commit()

            if result.returns_rows:
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                return data
            else:
                return f"Query {sql_query} executed successfully"

        except Exception as e:
            session.rollback()
            raise e

        finally:
            session.close()