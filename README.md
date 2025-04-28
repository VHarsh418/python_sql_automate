# ChatWithDB

A dynamic MySQL database interface with natural language querying capabilities powered by Groq's LLM.

## Features

- 🌐 **Connect to any MySQL database** - Work with any database on your MySQL server
- 🤖 **Natural Language to SQL** - Ask questions in plain English and get SQL queries
- 📊 **Dynamic Schema Handling** - Automatically adapts to any table structure
- 📱 **Modern UI** - Clean, responsive interface built with Streamlit
- 📝 **Direct SQL Queries** - Execute custom SQL commands directly
- 📋 **Data Entry Forms** - Add data to any table with auto-generated forms
- 📜 **Query History** - Track and re-run previous queries
- 🔄 **Real-time Query Execution** - Get instant results for your queries
- 🛠️ **Error Handling** - Clear error messages and suggestions for fixing issues

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ChatWithDB.git
   cd ChatWithDB
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your `.env` file with your database credentials:
   ```
   DB_HOST = localhost
   DB_USER = your_username
   DB_PASSWORD = your_password
   DB_NAME = optional_default_database
   GROQ_API_KEY = your_groq_api_key
   ```

## Usage

### Running the Streamlit App

```bash
streamlit run app.py
```

The application will open in your default web browser. You can:
- Connect to your MySQL database
- Ask questions in natural language
- Execute SQL queries directly
- Add new records to tables
- View query history

### Running the CLI Version

```bash
python main.py
```

## Project Structure

- `app.py` - Main Streamlit application
- `main.py` - CLI version of the application
- `sql_translator.py` - Natural language to SQL translation logic
- `requirements.txt` - Project dependencies
- `.env` - Environment variables and configuration

## Technology Stack

- Python 3.7+
- Streamlit - Web application framework
- MySQL - Database management system
- Groq LLM API - Natural language processing
- python-dotenv - Environment variable management
- mysql-connector-python - MySQL database connector

## Requirements

- Python 3.7 or higher
- MySQL Server 5.7 or higher
- Groq API key (for natural language processing)
- Internet connection (for Groq API access)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details 