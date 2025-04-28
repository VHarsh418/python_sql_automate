import os
import re
from groq import Groq

class SQLTranslator:
    def __init__(self):
        self.table_schema = {}
        self.table_relationships = {}
        
        # Initialize Groq client
        try:
            self.groq_client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )
            self.api_available = True
        except Exception as e:
            print(f"Warning: Groq API initialization failed: {e}")
            self.api_available = False
        
    def translate(self, natural_language_query):
        """Convert natural language query to SQL using Groq LLM"""
        try:
            if not self.api_available:
                return "Error: Groq API is not available. Please check your API key."
                
            # Check if schema is available
            if not self.table_schema:
                return "Error: No database schema available. Please select a database first and update the schema."
            
            # Create a prompt with context about the database schema
            schema_context = self._get_schema_context()
            relationships = self._get_relationships_context()
            
            prompt = f"""
You are a helpful and secure SQL assistant. Your task is to convert natural language into safe and correct MySQL queries that follow standard CRUD patterns.

DATABASE SCHEMA:
{schema_context}

TABLE RELATIONSHIPS:
{relationships}

RULES:
- Generate only ONE SQL query - no extra text, comments, or explanations
- Do NOT generate DROP, TRUNCATE, or ALTER statements unless explicitly requested
- Do NOT generate DELETE or UPDATE queries without a WHERE clause
- Do NOT use * in SELECT statements; select specific columns
- LIMIT large result sets (default to LIMIT 100 if not specified)
- Ensure the query is syntactically correct for MySQL
- If the query mentions joining tables, use appropriate JOIN syntax based on the relationships
- If showing all fields is explicitly requested, you may use * but comments are preferred

USER REQUEST: {natural_language_query}

SQL QUERY:
"""
            
            # Get response from Groq
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,  # Low temperature for more deterministic output
                max_tokens=200,   # Limit response length
            )
            
            sql_query = chat_completion.choices[0].message.content.strip()
            
            # Validate the SQL query for safety
            if self._is_unsafe_query(sql_query):
                return "Error: Generated query contains unsafe operations. Please rephrase your request."
            
            return sql_query
            
        except Exception as e:
            return f"Error: Failed to generate SQL query: {str(e)}"
    
    def _get_schema_context(self):
        """Generate a string representation of the database schema"""
        schema_str = ""
        for table, columns in self.table_schema.items():
            schema_str += f"Table `{table}`:\n"
            for column in columns:
                schema_str += f"- {column}\n"
            schema_str += "\n"
        
        return schema_str
    
    def _get_relationships_context(self):
        """Generate a string representation of table relationships"""
        if not self.table_relationships:
            # Attempt to detect relationships from schema
            self._detect_relationships()
            
        if not self.table_relationships:
            return "No explicit relationships detected. Use standard JOIN syntax if needed."
            
        rel_str = ""
        for table, relationships in self.table_relationships.items():
            rel_str += f"Table `{table}` relates to:\n"
            for related_table, relation in relationships.items():
                rel_str += f"- Table `{related_table}` via {relation['from_col']} → {relation['to_col']}\n"
            rel_str += "\n"
        
        return rel_str
    
    def _detect_relationships(self):
        """Detect potential relationships between tables based on column names"""
        # Look for common patterns like tablenameid, id_tablename, etc.
        for table, columns in self.table_schema.items():
            for column in columns:
                # Check for columns named like "user_id", "product_id", etc.
                pattern = r"^(\w+)_id$"
                match = re.match(pattern, column.lower())
                if match:
                    related_table = match.group(1)
                    # Check if this is likely a valid relation (target table exists)
                    if related_table in self.table_schema or related_table + 's' in self.table_schema:
                        target_table = related_table if related_table in self.table_schema else related_table + 's'
                        # Add the relationship
                        if table not in self.table_relationships:
                            self.table_relationships[table] = {}
                        self.table_relationships[table][target_table] = {
                            'from_col': column,
                            'to_col': 'id'
                        }
    
    def _is_unsafe_query(self, query):
        """Check if the query contains unsafe operations"""
        query = query.strip().upper()
        
        # Check for unsafe operations
        unsafe_operations = ["DROP", "TRUNCATE"]
        for op in unsafe_operations:
            if op in query and "IF EXISTS" not in query:
                return True
        
        # Check for UPDATE or DELETE without WHERE
        if query.startswith("UPDATE") and "WHERE" not in query:
            return True
        
        if query.startswith("DELETE") and "WHERE" not in query:
            return True
        
        return False
    
    def update_schema(self, table_name, columns):
        """Update the table schema with new tables or columns"""
        self.table_schema[table_name] = columns
        # Reset relationships when schema changes
        self.table_relationships = {}
        self._detect_relationships()
    
    def clear_schema(self):
        """Clear the existing schema information"""
        self.table_schema = {}
        self.table_relationships = {}
        
    def get_table_schema(self):
        """Return the current table schema"""
        return self.table_schema
    
    def get_relationships(self):
        """Return the detected table relationships"""
        return self.table_relationships 