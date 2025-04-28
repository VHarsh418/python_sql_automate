import streamlit as st
import os
import mysql.connector
from dotenv import load_dotenv
from sql_translator import SQLTranslator
import pandas as pd
import time
import datetime
from datetime import date

# Load environment variables
load_dotenv()

from main import Database

# Set page config
st.set_page_config(
    page_title="ChatWithDB",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve UI aesthetics
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .stSelectbox [data-baseweb=select] {
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }
    .sidebar .sidebar-content {
        background-color: #f1f3f5;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f1f1;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    .connection-status {
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    .connection-status.connected {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .connection-status.disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .db-box {
        padding: 10px;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .db-box:hover {
        background-color: #e9ecef;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .db-box.selected {
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    
    # Create connection parameters
    if 'connection_params' not in st.session_state:
        st.session_state.connection_params = {
            'host': os.getenv("DB_HOST", "localhost"),
            'user': os.getenv("DB_USER", "root"),
            'password': os.getenv("DB_PASSWORD", ""),
        }
    
    # Create Database instance without default database
    if 'db' not in st.session_state:
        try:
            st.session_state.db = Database()
            st.session_state.connection_error = None
        except Exception as e:
            st.session_state.connection_error = str(e)
            st.session_state.db = None
    
    if 'translator' not in st.session_state:
        st.session_state.translator = SQLTranslator()
    
    if 'connected_db' not in st.session_state:
        st.session_state.connected_db = getattr(st.session_state.db, 'current_database', None)
    
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    if 'results' not in st.session_state:
        st.session_state.results = None
    
    if 'available_databases' not in st.session_state:
        if st.session_state.db:
            try:
                st.session_state.available_databases = st.session_state.db.get_available_databases()
            except:
                st.session_state.available_databases = []
        else:
            st.session_state.available_databases = []

# Function to reconnect to MySQL server
def reconnect_db():
    try:
        st.session_state.db = Database()
        st.session_state.connection_error = None
        st.session_state.available_databases = st.session_state.db.get_available_databases()
        return True
    except Exception as e:
        st.session_state.connection_error = str(e)
        st.session_state.db = None
        st.session_state.available_databases = []
        return False

# Function to refresh schema
def refresh_schema():
    if st.session_state.db and st.session_state.connected_db:
        schema = st.session_state.db.get_schema()
        st.session_state.translator.clear_schema()
        for table, columns in schema.items():
            st.session_state.translator.update_schema(table, columns)

# Function to handle datetime format conversion
def format_value_for_mysql(value, field_type):
    """Format values correctly for MySQL based on their type"""
    if value is None:
        return None
        
    # Handle datetime types
    if 'datetime' in field_type.lower() or 'timestamp' in field_type.lower():
        # Let MySQL use default CURRENT_TIMESTAMP if applicable
        if isinstance(value, str) and value.strip() == '':
            return None
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value
            
    # Handle date types
    elif 'date' in field_type.lower() and 'datetime' not in field_type.lower():
        if isinstance(value, (datetime.date, date)):
            return value.strftime('%Y-%m-%d')
        return value
            
    # Handle time types
    elif 'time' in field_type.lower() and 'datetime' not in field_type.lower():
        if isinstance(value, datetime.time):
            return value.strftime('%H:%M:%S')
        return value
            
    # Handle boolean
    elif field_type.lower() == 'tinyint(1)' or 'boolean' in field_type.lower() or 'bool' in field_type.lower():
        return 1 if value else 0
            
    # Return as is for other types
    return value

# Sidebar for database connection and selection
with st.sidebar:
    st.title("🗄️ Database Manager")
    
    # Connection settings
    with st.expander("Connection Settings", expanded=not st.session_state.db):
        connection_form = st.form("connection_form")
        with connection_form:
            host = st.text_input("Host", value=st.session_state.connection_params['host'])
            user = st.text_input("Username", value=st.session_state.connection_params['user'])
            password = st.text_input("Password", value=st.session_state.connection_params['password'], type="password")
            
            submitted = st.form_submit_button("Connect")
            if submitted:
                st.session_state.connection_params = {
                    'host': host,
                    'user': user,
                    'password': password,
                }
                
                # Update environment variables
                os.environ["DB_HOST"] = host
                os.environ["DB_USER"] = user
                os.environ["DB_PASSWORD"] = password
                
                with st.spinner("Connecting to MySQL server..."):
                    if reconnect_db():
                        st.success("Connected to MySQL server!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Connection failed: {st.session_state.connection_error}")
    
    # Display connection status
    if st.session_state.db:
        st.markdown('<div class="connection-status connected">✓ Connected to MySQL Server</div>', unsafe_allow_html=True)
        
        # Database selection
        st.subheader("Select Database")
        
        # Refresh database list button
        if st.button("🔄 Refresh Database List"):
            with st.spinner("Refreshing..."):
                try:
                    st.session_state.available_databases = st.session_state.db.get_available_databases()
                    st.success("Database list refreshed!")
                except Exception as e:
                    st.error(f"Failed to refresh database list: {str(e)}")
        
        # Display available databases as cards
        if st.session_state.available_databases:
            for db_name in st.session_state.available_databases:
                is_selected = st.session_state.connected_db == db_name
                box_class = "db-box selected" if is_selected else "db-box"
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f'<div class="{box_class}">{db_name}</div>', unsafe_allow_html=True)
                with col2:
                    if st.button("Connect", key=f"connect_{db_name}"):
                        with st.spinner(f"Connecting to {db_name}..."):
                            if st.session_state.db.select_database(db_name):
                                st.session_state.connected_db = db_name
                                refresh_schema()
                                st.success(f"Connected to {db_name}")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"Failed to connect to {db_name}")
        else:
            st.info("No databases found. Create a new one or check your connection.")
        
        # Create a new database
        st.subheader("Create New Database")
        with st.form("create_db_form"):
            new_db_name = st.text_input("Database Name")
            create_tables = st.checkbox("Create initial tables")
            submit_create = st.form_submit_button("Create Database")
            
            if submit_create and new_db_name:
                with st.spinner(f"Creating database {new_db_name}..."):
                    if st.session_state.db._create_database(new_db_name):
                        if st.session_state.db.select_database(new_db_name):
                            st.session_state.connected_db = new_db_name
                            
                            if create_tables:
                                st.session_state.db._create_initial_tables()
                            
                            # Refresh schema and database list
                            refresh_schema()
                            st.session_state.available_databases = st.session_state.db.get_available_databases()
                            
                            st.success(f"Created and connected to {new_db_name}")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error(f"Failed to create database {new_db_name}")
        
        # Display schema info if connected to a database
        if st.session_state.connected_db:
            st.subheader(f"Schema: {st.session_state.connected_db}")
            schema = st.session_state.translator.get_table_schema()
            
            if not schema:
                st.info("No tables found in this database.")
                if st.button("Create Sample Table"):
                    with st.spinner("Creating sample table..."):
                        st.session_state.db._create_initial_tables()
                        refresh_schema()
                        st.success("Sample table created!")
                        time.sleep(0.5)
                        st.rerun()
            else:
                for table, columns in schema.items():
                    with st.expander(f"📋 {table}"):
                        for column in columns:
                            st.markdown(f"• {column}")
    else:
        # Not connected
        st.markdown('<div class="connection-status disconnected">✕ Not connected to MySQL Server</div>', unsafe_allow_html=True)
        if st.session_state.connection_error:
            st.error(f"Error: {st.session_state.connection_error}")
        st.info("Please check your connection settings and try again.")

# Main content
st.title("🗄️ ChatWithDB")
st.caption("A natural language interface for your MySQL databases")

# Check if connected to database server
if not st.session_state.db:
    st.warning("Not connected to MySQL server. Please configure connection settings in the sidebar.")
# Check if connected to any database
elif not st.session_state.connected_db:
    st.warning("Please select a database from the sidebar to begin")
    
    # Show quick database creation form
    st.subheader("Quick Database Creation")
    col1, col2 = st.columns([3, 1])
    with col1:
        quick_db_name = st.text_input("Enter database name")
    with col2:
        if st.button("Create & Connect") and quick_db_name:
            with st.spinner(f"Creating database {quick_db_name}..."):
                if st.session_state.db._create_database(quick_db_name):
                    if st.session_state.db.select_database(quick_db_name):
                        st.session_state.connected_db = quick_db_name
                        st.session_state.available_databases = st.session_state.db.get_available_databases()
                        st.success(f"Created and connected to {quick_db_name}")
                        time.sleep(0.5)
                        st.rerun()
else:
    # Connected to a database - show main interface
    st.success(f"Connected to: {st.session_state.connected_db}")
    
    # Create tabs for different functions
    tabs = st.tabs(["🤖 Chat Query", "📝 SQL Query", "📊 Data Entry", "🔍 Data Browser", "📜 Query History"])
    
    # Chat Query Tab
    with tabs[0]:
        st.header("Chat with your Database")
        nl_query = st.text_area("Enter your request in natural language", placeholder="Example: Show me all tables in the database")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate SQL"):
                if nl_query:
                    with st.spinner("Generating SQL..."):
                        sql_query = st.session_state.translator.translate(nl_query)
                        if sql_query.startswith("Error:"):
                            st.error(sql_query)
                        else:
                            st.session_state.generated_sql = sql_query
                            st.rerun()
                else:
                    st.warning("Please enter a query")
        
        # Display generated SQL and execute button
        if 'generated_sql' in st.session_state:
            st.code(st.session_state.generated_sql, language="sql")
            
            with col2:
                if st.button("Execute SQL"):
                    with st.spinner("Executing..."):
                        try:
                            result = st.session_state.db.execute_query(st.session_state.generated_sql)
                            st.session_state.results = result
                            
                            # Add to history
                            st.session_state.query_history.append({
                                "natural_language": nl_query,
                                "sql": st.session_state.generated_sql,
                                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            # Update schema if table structure changed
                            if st.session_state.generated_sql.strip().upper().startswith(("CREATE TABLE", "ALTER TABLE")):
                                refresh_schema()
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error executing query: {str(e)}")
    
    # SQL Query Tab
    with tabs[1]:
        st.header("Direct SQL Query")
        sql_query = st.text_area("Enter SQL query", placeholder="Example: SELECT * FROM users LIMIT 10")
        if st.button("Execute"):
            if sql_query:
                with st.spinner("Executing..."):
                    try:
                        result = st.session_state.db.execute_query(sql_query)
                        st.session_state.results = result
                        
                        # Add to history
                        st.session_state.query_history.append({
                            "natural_language": "Direct SQL Query",
                            "sql": sql_query,
                            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        # Update schema if table structure changed
                        if sql_query.strip().upper().startswith(("CREATE TABLE", "ALTER TABLE")):
                            refresh_schema()
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error executing query: {str(e)}")
            else:
                st.warning("Please enter a query")
    
    # Data Entry Tab
    with tabs[2]:
        st.header("Data Entry")
        
        schema = st.session_state.translator.get_table_schema()
        if not schema:
            st.warning("No tables found in current database.")
            if st.button("Create Sample Tables"):
                with st.spinner("Creating sample tables..."):
                    try:
                        st.session_state.db._create_initial_tables()
                        refresh_schema()
                        
                        # Add sample data
                        add_sample = st.checkbox("Add sample data", value=True)
                        if add_sample:
                            st.session_state.db.add_sample_data()
                        
                        st.success("Sample tables created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating tables: {str(e)}")
        else:
            # Get table selection
            selected_table = st.selectbox("Select Table", options=list(schema.keys()))
            
            # Create a form with input fields for each column
            with st.form(key=f"data_entry_form_{selected_table}"):
                st.subheader(f"Enter data for {selected_table}")
                
                # Get detailed table info
                try:
                    table_info = st.session_state.db.execute_query(f"DESCRIBE {selected_table}")
                    
                    if isinstance(table_info, str) and "Error" in table_info:
                        st.error(table_info)
                        submit_disabled = True
                    else:
                        # Create a dictionary to store form values
                        column_values = {}
                        
                        # Filter out auto-increment columns
                        input_columns = [col for col in table_info 
                                        if col['Extra'] != 'auto_increment' 
                                        and col['Key'] != 'PRI']
                        
                        # Create form fields for each column
                        for col in input_columns:
                            field_name = col['Field']
                            field_type = col['Type']
                            is_nullable = col['Null'] == 'YES'
                            default_value = col['Default'] if col['Default'] else ""
                            
                            # Handle different field types appropriately
                            if 'int' in field_type.lower():
                                column_values[field_name] = st.number_input(
                                    f"{field_name} ({field_type})", 
                                    value=0 if default_value == "" else int(default_value),
                                    step=1
                                )
                            elif 'decimal' in field_type.lower() or 'float' in field_type.lower() or 'double' in field_type.lower():
                                column_values[field_name] = st.number_input(
                                    f"{field_name} ({field_type})", 
                                    value=0.0 if default_value == "" else float(default_value),
                                    step=0.01
                                )
                            elif 'date' in field_type.lower() and 'datetime' not in field_type.lower() and 'timestamp' not in field_type.lower():
                                column_values[field_name] = st.date_input(
                                    f"{field_name} ({field_type})"
                                )
                            elif 'time' in field_type.lower() and 'datetime' not in field_type.lower() and 'timestamp' not in field_type.lower():
                                column_values[field_name] = st.time_input(
                                    f"{field_name} ({field_type})"
                                )
                            elif 'datetime' in field_type.lower() or 'timestamp' in field_type.lower():
                                # For timestamp fields, offer the option to use current timestamp
                                use_current_timestamp = st.checkbox(f"Use current timestamp for {field_name}", value=True)
                                if use_current_timestamp:
                                    column_values[field_name] = None  # Let MySQL use default
                                else:
                                    column_values[field_name] = st.date_input(
                                        f"{field_name} ({field_type})"
                                    )
                            elif 'enum' in field_type.lower() or 'set' in field_type.lower():
                                # Extract options from enum/set type
                                options = field_type.split("(")[1].split(")")[0].replace("'", "").split(",")
                                column_values[field_name] = st.selectbox(
                                    f"{field_name} ({field_type})",
                                    options=options
                                )
                            elif 'text' in field_type.lower():
                                column_values[field_name] = st.text_area(
                                    f"{field_name} ({field_type})", 
                                    value=default_value
                                )
                            elif 'boolean' in field_type.lower() or field_type.lower() == 'bool' or field_type.lower() == 'tinyint(1)':
                                column_values[field_name] = st.checkbox(
                                    f"{field_name} ({field_type})",
                                    value=default_value == "1" or default_value.lower() == "true" if default_value else False
                                )
                            else:
                                # Default to text input for other types
                                column_values[field_name] = st.text_input(
                                    f"{field_name} ({field_type})", 
                                    value=default_value
                                )
                        
                        # Submit button
                        submit_data = st.form_submit_button("Insert Data")
                        
                        if submit_data:
                            # Convert data types as needed before insertion
                            processed_values = {}
                            for col in input_columns:
                                field_name = col['Field']
                                field_type = col['Type']
                                value = column_values[field_name]
                                
                                # Process the value according to its field type
                                processed_values[field_name] = format_value_for_mysql(value, field_type)
                            
                            # Prepare and execute the query
                            if processed_values:
                                cols = ', '.join(processed_values.keys())
                                placeholders = ', '.join(['%s'] * len(processed_values))
                                values = tuple(processed_values.values())
                                
                                query = f"INSERT INTO {selected_table} ({cols}) VALUES ({placeholders})"
                                try:
                                    result = st.session_state.db.execute_query(query, values)
                                    st.success(result)
                                    # Add a short delay so user can see success message
                                    time.sleep(0.5)
                                    st.rerun()  # Clear form after success
                                except Exception as e:
                                    st.error(f"Error inserting data: {str(e)}")
                            else:
                                st.warning("No data to insert")
                except Exception as e:
                    st.error(f"Error retrieving table structure: {str(e)}")
    
    # Data Browser Tab
    with tabs[3]:
        st.header("Data Browser")
        
        schema = st.session_state.translator.get_table_schema()
        if not schema:
            st.warning("No tables found in this database.")
        else:
            col1, col2 = st.columns([2,1])
            with col1:
                browse_table = st.selectbox("Select Table to Browse", options=list(schema.keys()))
            with col2:
                rows_to_show = st.slider("Rows to display", min_value=5, max_value=100, value=25, step=5)
                
            if st.button(f"Browse {browse_table} data"):
                with st.spinner(f"Loading data from {browse_table}..."):
                    try:
                        # Get all columns for the table
                        columns_list = schema[browse_table]
                        columns_str = ", ".join(columns_list)
                        
                        # Execute query to get data
                        query = f"SELECT {columns_str} FROM {browse_table} LIMIT {rows_to_show}"
                        result = st.session_state.db.execute_query(query)
                        
                        if isinstance(result, str):
                            if "No results found" in result:
                                st.info(f"Table '{browse_table}' is empty.")
                            else:
                                st.warning(result)
                        else:
                            # Display data as a dataframe
                            df = pd.DataFrame(result)
                            st.dataframe(df, use_container_width=True)
                            
                            # Add download button
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download data as CSV",
                                data=csv,
                                file_name=f"{browse_table}_data.csv",
                                mime="text/csv"
                            )
                            
                            # Display record count
                            count_query = f"SELECT COUNT(*) as total FROM {browse_table}"
                            count_result = st.session_state.db.execute_query(count_query)
                            if not isinstance(count_result, str):
                                total_records = count_result[0]['total']
                                st.caption(f"Showing {len(df)} of {total_records} total records")
                    except Exception as e:
                        st.error(f"Error retrieving data: {str(e)}")
            
            # Add sample data option
            if st.button("Add sample data to tables"):
                with st.spinner("Adding sample data..."):
                    try:
                        if st.session_state.db.add_sample_data():
                            st.success("Sample data added successfully!")
                        else:
                            st.warning("Failed to add all sample data. Some tables may have been populated.")
                    except Exception as e:
                        st.error(f"Error adding sample data: {str(e)}")
    
    # Query History Tab
    with tabs[4]:
        st.header("Query History")
        if not st.session_state.query_history:
            st.info("No queries executed yet.")
        else:
            for i, query in enumerate(reversed(st.session_state.query_history)):
                with st.expander(f"{query['timestamp']} - {query['natural_language'][:50]}..."):
                    st.code(query['sql'], language="sql")
                    if st.button("Re-run this query", key=f"rerun_{i}"):
                        with st.spinner("Executing..."):
                            try:
                                result = st.session_state.db.execute_query(query['sql'])
                                st.session_state.results = result
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error executing query: {str(e)}")

    # Display query results if available
    if st.session_state.results:
        st.header("Query Results")
        
        if isinstance(st.session_state.results, str):
            if "Error" in st.session_state.results:
                st.error(st.session_state.results)
            else:
                st.success(st.session_state.results)
        else:
            # Convert to DataFrame for better display
            try:
                df = pd.DataFrame(st.session_state.results)
                st.dataframe(df, use_container_width=True)
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name="query_results.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Error displaying results: {str(e)}")

# Footer
st.markdown("---")
st.caption("ChatWithDB - Dynamic MySQL database interface powered by Streamlit") 