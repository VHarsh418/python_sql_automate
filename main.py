import os
import mysql.connector
from dotenv import load_dotenv
from sql_translator import SQLTranslator

# Load environment variables
load_dotenv()

class Database:
    def __init__(self, database=None):
        try:
            # Connect without specifying a database first
            self.connection = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", "")
            )
            self.cursor = self.connection.cursor(dictionary=True)
            
            # If a specific database is provided or in env, connect to it
            if database:
                self.select_database(database)
            elif os.getenv("DB_NAME"):
                self.select_database(os.getenv("DB_NAME"))
                
            print("Database connection successful!")
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            raise
    
    def select_database(self, database_name):
        """Connect to a specific database"""
        try:
            self.cursor.execute(f"USE {database_name}")
            self.current_database = database_name
            print(f"Connected to database: {database_name}")
            return True
        except mysql.connector.Error as err:
            print(f"Error selecting database {database_name}: {err}")
            return False
    
    def get_available_databases(self):
        """Get a list of all available databases"""
        try:
            self.cursor.execute("SHOW DATABASES")
            databases = [db['Database'] for db in self.cursor.fetchall()]
            # Filter out system databases if needed
            system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
            return [db for db in databases if db not in system_dbs]
        except Exception as e:
            print(f"Error fetching databases: {e}")
            return []
    
    def _create_database(self, db_name):
        """Create a new database"""
        try:
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            self.connection.commit()
            print(f"Database '{db_name}' created successfully!")
            return True
        except mysql.connector.Error as err:
            print(f"Failed to create database: {err}")
            return False
    
    def _create_initial_tables(self):
        """Create initial tables in the database"""
        try:
            # Create USERS table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS USERS (
                    ID INT AUTO_INCREMENT PRIMARY KEY,
                    NAME VARCHAR(100) NOT NULL,
                    EMAIL VARCHAR(100),
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create PRODUCTS table for more diverse schema
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS PRODUCTS (
                    ID INT AUTO_INCREMENT PRIMARY KEY,
                    NAME VARCHAR(100) NOT NULL,
                    PRICE DECIMAL(10,2) NOT NULL,
                    DESCRIPTION TEXT,
                    IN_STOCK BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create ORDERS table with foreign keys - fixing the timestamp issue
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ORDERS (
                    ID INT AUTO_INCREMENT PRIMARY KEY,
                    USER_ID INT,
                    ORDER_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    TOTAL_AMOUNT DECIMAL(10,2) NOT NULL,
                    STATUS VARCHAR(20) DEFAULT 'PENDING',
                    FOREIGN KEY (USER_ID) REFERENCES USERS(ID) ON DELETE SET NULL
                )
            """)
            
            # Create ORDER_ITEMS table to demonstrate more complex relationships
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ORDER_ITEMS (
                    ID INT AUTO_INCREMENT PRIMARY KEY,
                    ORDER_ID INT,
                    PRODUCT_ID INT,
                    QUANTITY INT NOT NULL DEFAULT 1,
                    PRICE DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (ORDER_ID) REFERENCES ORDERS(ID) ON DELETE CASCADE,
                    FOREIGN KEY (PRODUCT_ID) REFERENCES PRODUCTS(ID) ON DELETE SET NULL
                )
            """)
            
            self.connection.commit()
            print("Initial tables created successfully!")
            return True
        except mysql.connector.Error as err:
            print(f"Error creating tables: {err}")
            return False
            
    def execute_query(self, query, params=None):
        """Execute a SQL query with optional parameters"""
        try:
            # Process parameters if provided
            if params:
                # Process any date or datetime objects to MySQL format
                processed_params = []
                for param in params:
                    if hasattr(param, 'strftime'):  # Check if it's a date-like object
                        if hasattr(param, 'hour'):  # It's a datetime
                            processed_params.append(param.strftime('%Y-%m-%d %H:%M:%S'))
                        else:  # It's a date
                            processed_params.append(param.strftime('%Y-%m-%d'))
                    else:
                        processed_params.append(param)
                self.cursor.execute(query, tuple(processed_params))
            else:
                self.cursor.execute(query)
            
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                self.connection.commit()
                affected_rows = self.cursor.rowcount
                return f"{affected_rows} row(s) affected"
            else:
                result = self.cursor.fetchall()
                if not result:
                    return "No results found"
                return result
        except Exception as e:
            print(f"Error executing query: {e}")
            raise Exception(f"Query execution failed: {e}")
    
    def get_schema(self):
        """Get the database schema information for all tables in the current database"""
        schema = {}
        
        try:
            if not hasattr(self, 'current_database'):
                return {}
                
            # Get all tables in the current database
            self.cursor.execute("SHOW TABLES")
            tables_result = self.cursor.fetchall()
            
            # Determine the key name that contains table names
            # It will be 'Tables_in_' followed by the database name
            if tables_result:
                table_key = list(tables_result[0].keys())[0]  # Get the first key
                tables = [table[table_key] for table in tables_result]
                
                # Get columns for each table
                for table in tables:
                    self.cursor.execute(f"DESCRIBE {table}")
                    columns = [row['Field'] for row in self.cursor.fetchall()]
                    schema[table.lower()] = columns
                
            return schema
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {}
    
    def add_sample_data(self):
        """Add sample data to the tables for testing purposes"""
        try:
            if not hasattr(self, 'current_database'):
                return False
            
            # First check if tables exist
            schema = self.get_schema()
            if not schema:
                print("No tables found to add sample data")
                return False
                
            # Add sample users first (since they are referenced by orders)
            if 'users' in schema:
                try:
                    # Check if users already exist
                    user_check = self.execute_query("SELECT COUNT(*) as count FROM USERS")
                    if not isinstance(user_check, str) and user_check[0]['count'] == 0:
                        self.execute_query("INSERT INTO USERS (NAME, EMAIL) VALUES (%s, %s)", 
                                        ("Alice Smith", "alice@example.com"))
                        self.execute_query("INSERT INTO USERS (NAME, EMAIL) VALUES (%s, %s)", 
                                        ("Bob Jones", "bob@example.com"))
                        self.execute_query("INSERT INTO USERS (NAME, EMAIL) VALUES (%s, %s)", 
                                        ("Charlie Brown", "charlie@example.com"))
                        print("Sample users added")
                except Exception as e:
                    print(f"Error adding users: {e}")
                    
            # Add sample products
            if 'products' in schema:
                try:
                    # Check if products already exist
                    product_check = self.execute_query("SELECT COUNT(*) as count FROM PRODUCTS")
                    if not isinstance(product_check, str) and product_check[0]['count'] == 0:
                        self.execute_query("INSERT INTO PRODUCTS (NAME, PRICE, DESCRIPTION) VALUES (%s, %s, %s)", 
                                        ("Laptop", 1299.99, "High-performance laptop with 16GB RAM"))
                        self.execute_query("INSERT INTO PRODUCTS (NAME, PRICE, DESCRIPTION) VALUES (%s, %s, %s)", 
                                        ("Smartphone", 799.99, "Latest model with advanced camera"))
                        self.execute_query("INSERT INTO PRODUCTS (NAME, PRICE, DESCRIPTION) VALUES (%s, %s, %s)", 
                                        ("Headphones", 149.99, "Wireless noise-cancelling headphones"))
                        print("Sample products added")
                except Exception as e:
                    print(f"Error adding products: {e}")
                    
            # Add sample orders - ensure users exist before adding orders that reference them
            if 'orders' in schema and 'users' in schema:
                try:
                    # Check if orders already exist
                    order_check = self.execute_query("SELECT COUNT(*) as count FROM ORDERS")
                    if not isinstance(order_check, str) and order_check[0]['count'] == 0:
                        # Check if we have users in the database
                        users = self.execute_query("SELECT ID FROM USERS LIMIT 2")
                        if isinstance(users, str) or len(users) < 2:
                            print("Not enough users to create sample orders")
                            return True
                            
                        # Now we can safely add orders with valid user IDs
                        user1_id = users[0]['ID']
                        user2_id = users[1]['ID']
                        
                        # Insert orders - using NULL for ORDER_DATE to let MySQL use DEFAULT CURRENT_TIMESTAMP
                        self.execute_query("INSERT INTO ORDERS (USER_ID, TOTAL_AMOUNT, STATUS) VALUES (%s, %s, %s)", 
                                        (user1_id, 1449.98, "COMPLETED"))
                        self.execute_query("INSERT INTO ORDERS (USER_ID, TOTAL_AMOUNT, STATUS) VALUES (%s, %s, %s)", 
                                        (user2_id, 799.99, "PROCESSING"))
                        print("Sample orders added")
                except Exception as e:
                    print(f"Error adding orders: {e}")
            
            # Add sample order items - this requires both orders and products
            if 'order_items' in schema and 'orders' in schema and 'products' in schema:
                try:
                    # Check if order items already exist
                    item_check = self.execute_query("SELECT COUNT(*) as count FROM ORDER_ITEMS")
                    if not isinstance(item_check, str) and item_check[0]['count'] == 0:
                        # Get order IDs
                        orders = self.execute_query("SELECT ID FROM ORDERS LIMIT 2")
                        if isinstance(orders, str) or len(orders) < 1:
                            print("No orders available for order items")
                            return True
                            
                        # Get product IDs
                        products = self.execute_query("SELECT ID, PRICE FROM PRODUCTS LIMIT 3")
                        if isinstance(products, str) or len(products) < 1:
                            print("No products available for order items")
                            return True
                            
                        # Now we can safely add order items
                        order1_id = orders[0]['ID']
                        if len(orders) > 1:
                            order2_id = orders[1]['ID']
                        else:
                            order2_id = order1_id
                            
                        product1_id = products[0]['ID']
                        product1_price = products[0]['PRICE']
                        
                        product2_id = products[1]['ID'] if len(products) > 1 else product1_id
                        product2_price = products[1]['PRICE'] if len(products) > 1 else product1_price
                        
                        # Insert order items
                        self.execute_query("""
                            INSERT INTO ORDER_ITEMS (ORDER_ID, PRODUCT_ID, QUANTITY, PRICE) 
                            VALUES (%s, %s, %s, %s)
                        """, (order1_id, product1_id, 1, product1_price))
                        
                        self.execute_query("""
                            INSERT INTO ORDER_ITEMS (ORDER_ID, PRODUCT_ID, QUANTITY, PRICE) 
                            VALUES (%s, %s, %s, %s)
                        """, (order1_id, product2_id, 2, product2_price))
                        
                        if len(orders) > 1 and len(products) > 2:
                            product3_id = products[2]['ID']
                            product3_price = products[2]['PRICE']
                            self.execute_query("""
                                INSERT INTO ORDER_ITEMS (ORDER_ID, PRODUCT_ID, QUANTITY, PRICE) 
                                VALUES (%s, %s, %s, %s)
                            """, (order2_id, product3_id, 1, product3_price))
                        
                        print("Sample order items added")
                except Exception as e:
                    print(f"Error adding order items: {e}")
            
            return True
        except Exception as e:
            print(f"Error adding sample data: {e}")
            return False
            
    def close(self):
        """Close database connection"""
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'connection') and self.connection:
                self.connection.close()
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database connection: {e}")

def display_results(results):
    """Format and display query results"""
    if isinstance(results, str):
        print(results)
        return
        
    if not results:
        print("No results found")
        return
        
    # Print table headers
    headers = results[0].keys()
    header_row = " | ".join(str(h).upper() for h in headers)
    separator = "-" * len(header_row)
    
    print(separator)
    print(header_row)
    print(separator)
    
    # Print rows
    for row in results:
        print(" | ".join(str(row[h]) for h in headers))
    
    print(separator)
    print(f"Total rows: {len(results)}")

def main():
    db = Database()
    translator = SQLTranslator()
    
    # Initialize with current database if one is selected
    if hasattr(db, 'current_database'):
        schema = db.get_schema()
        translator.clear_schema()  # Clear existing schema first
        for table, columns in schema.items():
            translator.update_schema(table, columns)
        print("Database schema loaded successfully!")
    
    while True:
        current_db = getattr(db, 'current_database', 'None')
        print(f"\n=== MySQL Automation Tool === [Current DB: {current_db}]")
        print("1. Execute SQL query")
        print("2. Convert natural language to SQL")
        print("3. Add test data")
        print("4. Update schema information")
        print("5. List available databases")
        print("6. Select a database")
        print("7. Create a new database")
        print("8. Exit")
        
        choice = input("Enter your choice (1-8): ")
        
        if choice == "1":
            query = input("Enter SQL query: ")
            try:
                result = db.execute_query(query)
                display_results(result)
            except Exception as e:
                print(f"Error: {e}")
            
        elif choice == "2":
            nl_query = input("Enter your request in natural language: ")
            sql_query = translator.translate(nl_query)
            print("\nGenerated SQL Query:")
            print(sql_query)
            
            if sql_query.startswith("Error:"):
                print(sql_query)
                continue
                
            execute = input("\nDo you want to execute this query? (y/n): ")
            if execute.lower() == 'y':
                try:
                    result = db.execute_query(sql_query)
                    display_results(result)
                    
                    # Update schema after potential structure changes
                    if sql_query.strip().upper().startswith(("CREATE TABLE", "ALTER TABLE")):
                        schema = db.get_schema()
                        translator.clear_schema()  # Clear existing schema first
                        for table, columns in schema.items():
                            translator.update_schema(table, columns)
                        print("Schema updated after table modification.")
                except Exception as e:
                    print(f"Error: {e}")
        
        elif choice == "3":
            if not hasattr(db, 'current_database'):
                print("Please select a database first.")
                continue
                
            print("Adding test data...")
            add_sample = input("Do you want to add sample data to USERS, PRODUCTS, and ORDERS tables? (y/n): ")
            if add_sample.lower() == 'y':
                if db.add_sample_data():
                    print("Sample data added successfully!")
                else:
                    print("Failed to add sample data.")
                continue
                
            table_name = input("Enter table name: ")
            try:
                # Get table structure
                table_info = db.execute_query(f"DESCRIBE {table_name}")
                if isinstance(table_info, str) and "Error" in table_info:
                    print(table_info)
                    continue
                
                columns = [col['Field'] for col in table_info if col['Key'] != 'PRI' or col['Extra'] != 'auto_increment']
                
                # Build INSERT query
                values = []
                for col in columns:
                    val = input(f"Enter value for {col}: ")
                    values.append(val)
                
                placeholders = ', '.join(['%s'] * len(columns))
                cols = ', '.join(columns)
                
                query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                result = db.execute_query(query, tuple(values))
                print(result)
            except Exception as e:
                print(f"Error adding test data: {e}")
            
        elif choice == "4":
            if not hasattr(db, 'current_database'):
                print("Please select a database first.")
                continue
                
            print("Updating schema information...")
            schema = db.get_schema()
            translator.clear_schema()  # Clear existing schema first
            for table, columns in schema.items():
                translator.update_schema(table, columns)
            print("Current database schema:")
            for table, columns in translator.get_table_schema().items():
                print(f"Table: {table}")
                for column in columns:
                    print(f"  - {column}")
        
        elif choice == "5":
            print("\nAvailable databases:")
            databases = db.get_available_databases()
            for i, database in enumerate(databases, 1):
                print(f"{i}. {database}")
        
        elif choice == "6":
            databases = db.get_available_databases()
            print("\nAvailable databases:")
            for i, database in enumerate(databases, 1):
                print(f"{i}. {database}")
            
            try:
                db_index = int(input("\nSelect database number: ")) - 1
                if 0 <= db_index < len(databases):
                    selected_db = databases[db_index]
                    if db.select_database(selected_db):
                        # Load schema for the selected database
                        schema = db.get_schema()
                        translator.clear_schema()  # Clear existing schema first
                        for table, columns in schema.items():
                            translator.update_schema(table, columns)
                        print(f"Schema for database '{selected_db}' loaded successfully!")
                else:
                    print("Invalid selection!")
            except ValueError:
                print("Please enter a valid number!")
        
        elif choice == "7":
            db_name = input("Enter new database name: ")
            if db._create_database(db_name):
                db.select_database(db_name)
                create_tables = input("Do you want to create initial tables? (y/n): ")
                if create_tables.lower() == 'y':
                    db._create_initial_tables()
                    add_sample = input("Do you want to add sample data? (y/n): ")
                    if add_sample.lower() == 'y':
                        db.add_sample_data()
            
        elif choice == "8":
            db.close()
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()


# database.execute("show databases")

# for i in database:
#     print(i)


# database.execute("create database if not exists project")

# mysql.database = "project"


# Creating Tables


# database.execute("CREATE TABLE IF NOT EXISTS USERS (ID INT AUTO_INCREMENT PRIMARY KEY, NAME VARCHAR(100)) ")

# Checking for table if created or not

# database.execute("show tables")

# for i in database:
#     print(i)


# def insert_(name):
#     query = "INSERT INTO USERS (name) VALUES (%s)"
#     database.execute(query , (name,))
#     mysql.commit()
    
# insert_("Vansh")
# insert_("Anuj")
# insert_("Arihant")

    