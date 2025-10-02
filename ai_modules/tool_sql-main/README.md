# 🔍 SQL Tool - Natural Language to SQL Service

AI Mentor system's SQL module that converts natural language questions to SQL queries using LangChain framework.

## 🚀 Key Features

- **Natural Language Processing**: Converts user questions to SQL queries using GPT-4o-mini
- **LangChain Integration**: Leverages LangChain ChatOpenAI for consistent SQL generation
- **MySQL Database**: Direct database query execution with PyMySQL
- **Simple Architecture**: Minimal code with maximum efficiency (~300 lines total)
- **Auto-reconnection**: Automatic database reconnection on connection loss

## 📁 Project Structure

```
tool_sql-main/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python package dependencies
├── .env                       # Environment variables
├── Dockerfile                 # Docker configuration
│
├── controller/
│   └── sqlController.py       # FastAPI router and request handling
│
├── service/
│   └── sqlCoreService.py      # Core SQL processing service
│
├── util/
│   ├── langchainLlmClient.py  # LangChain LLM client
│   ├── dbClient.py            # Database connection client
│   ├── utils.py               # Utility functions
│   └── logger.py              # Logging configuration
│
└── prompts/                   # SQL generation prompt templates
```

## 🔧 Installation & Setup

### 1. Environment Setup
```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 2. Install packages
pip install -r requirements.txt

# 3. Configure environment variables (.env file)
OPENAI_API_KEY=your_openai_api_key
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=your_database_name
DB_PORT=3313
```

### 2. Run Server
```bash
# Run development server
python main.py

# Or run directly with uvicorn
uvicorn main:app --host 0.0.0.0 --port 7999 --reload
```

## 📚 API Usage

### Endpoints

#### 1. Execute SQL Query
```http
POST /api/v1/query
Content-Type: application/json

{
  "query": "Show me classes taught by Professor Oh Il-seok"
}
```

**Response:**
```json
{
  "result": "Total 2 results:\n1. {'name': 'Database Systems'}\n2. {'name': 'Big Data Processing'}"
}
```

#### 2. SQL Agent (same as query)
```http
POST /api/v1/agent
Content-Type: application/json

{
  "query": "Show me all Computer Science professors"
}
```

#### 3. Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

### Request Model
- **query** (required): User question (1-1000 characters)

## 🏗️ Architecture

### Processing Flow

```
User Question: "Show me classes taught by Professor Oh"
    ↓
1. Load SQL Generation Prompt
    ↓
2. LLM Call (GPT-4o-mini)
   System Prompt + User Question → SQL Query
    ↓
   Generated SQL:
   SELECT name FROM jbnu_class_gpt
   WHERE professor LIKE '%Oh%';
    ↓
3. Execute SQL Query
   PyMySQL executes query on database
    ↓
4. Format Results
   Total 2 results:
   1. {'name': 'Database Systems'}
   2. {'name': 'Big Data Processing'}
    ↓
5. Return Response
   {"result": "..."}
```

### Core Components

#### SqlCoreService (`service/sqlCoreService.py`)
**Main SQL processing service**

```python
class SqlService:
    def execute(self, query: str) -> str:
        # 1. Convert natural language to SQL
        sql = self._to_sql(query)

        # 2. Execute SQL query
        result = self.db_client.execute_query(sql)

        # 3. Format and return results
        return format_result(result)
```

#### LangchainLlmClient (`util/langchainLlmClient.py`)
**LLM client configuration**

```python
ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.05,  # Low temperature for consistent SQL
    seed=42            # Reproducible results
)
```

#### DbClient (`util/dbClient.py`)
**Database connection management**

- PyMySQL with DictCursor
- Automatic reconnection
- UTF-8 encoding support

### Utility Functions

**`load_prompt()`** - Load prompt template from file
**`format_result()`** - Format database results for display
**`remove_markdown()`** - Clean SQL code blocks (```sql ... ```)

## 🔍 Example Usage

### Query Examples

**1. Find courses by professor:**
```json
{
  "query": "What classes does Professor Kim teach?"
}
```

**2. Department courses:**
```json
{
  "query": "Show me all Computer Science courses"
}
```

**3. Course details:**
```json
{
  "query": "Tell me about Database Systems course"
}
```

## 🛠️ Development

### Adding Custom Prompts

Edit or create prompt files in `prompts/` directory:

```
prompts/
└── sql_system_prompt.txt
```

Use in code:
```python
from util.utils import load_prompt

prompt = load_prompt("sql_system_prompt")
```

### Database Configuration

Environment variables:
```bash
DB_HOST=210.117.181.113
DB_PORT=3313
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=nll_third
```

## 📊 Logging

Basic Python logging is used:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing query...")
logger.error("SQL execution failed")
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
docker build -t sql-tool .

# Run container
docker run -p 7999:7999 --env-file .env sql-tool
```

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 7999

CMD ["python", "main.py"]
```

## 📝 Requirements

```
fastapi
uvicorn
langchain
langchain-openai
pymysql
python-dotenv
pydantic
```

## ⚙️ Configuration

### LLM Settings
- **Model**: gpt-4o-mini
- **Temperature**: 0.05 (for consistent SQL generation)
- **Seed**: 42 (for reproducibility)

### Database Settings
- **Driver**: PyMySQL
- **Cursor**: DictCursor (returns results as dictionaries)
- **Charset**: utf8mb4
- **Auto-reconnect**: Enabled

## 🔒 Security Notes

- Never commit `.env` file
- Use environment variables for sensitive data
- Validate user input (max 1000 characters)
- Use parameterized queries when possible
;'[[[[[[[[';;;;[;[[[[[[[';'/;;/']]]]]]]]]]]]]]]]