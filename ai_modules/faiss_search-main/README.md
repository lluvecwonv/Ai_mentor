# FAISS Vector Search Service 🔍

AI-Based Hybrid Search System for JBNU Course Database

## ✨ Key Features

- **LangChain LLM Integration**: Automatic conversion of natural language queries to SQL
- **FAISS Vector Search**: Semantic similarity search based on OpenAI embeddings
- **Hybrid Search**: Combination of LLM SQL filtering + vector search
- **Simplified Architecture**: Maximum performance with minimal code

## 🏗️ Project Structure

```
faiss_search-main/
├── controller/
│   └── searchController.py     # FastAPI endpoints (46 lines)
├── service/
│   └── searchService.py        # Search service (110 lines)
├── util/
│   ├── langchainLlmClient.py   # LangChain LLM client
│   ├── dbClient.py             # MySQL connection manager
│   └── utils.py                # Utility functions
├── prompts/
│   └── sql_prefilter_generator.txt  # SQL generation prompt
└── main.py                     # FastAPI app (40 lines)
```

## 🔄 Search Flow

```
User Query ("Computer Science AI class")
    ↓
[1] LLM Generates SQL
    - Uses LangChain
    - Generates SQL WHERE clause based on prompt
    ↓
[2] MySQL Filtering
    - Filters relevant courses
    - Includes vector data
    ↓
[3] FAISS Vector Search
    - Generates OpenAI embeddings
    - Calculates similarity
    ↓
[4] Return Results
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Environment variables (.env)
OPENAI_API_KEY=your_api_key
DB_HOST=your_host
DB_PASSWORD=your_password
```

### 2. Run Server

```bash
python main.py
# Runs on http://localhost:7997
```

### 3. API Usage

```bash
# Search request
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning course",
    "count": 10
  }'
```

## 📚 Main Components

### SearchService (Simplified)

```python
class SearchService:
    def __init__(self, db_client):
        self.llm_client = LangchainLlmClient()  # LLM managed internally
        self.db_client = db_client              # DB injected externally

    def search_hybrid(query_text, count):
        # 1. Generate SQL with LLM
        # 2. Filter with DB
        # 3. Vector search
        # 4. Return results
```

### LangchainLlmClient

- **ChatOpenAI**: Uses GPT-4o-mini model
- **OpenAIEmbeddings**: text-embedding-3-small
- **Unified Management**: LLM and embedding models managed in one place

### Utility Functions

- `load_prompt()`: Load prompt files
- `extract_sql_from_response()`: Extract SQL from LLM response
- `prepare_vectors()`: Prepare vector data
- `generate_embedding()`: Generate text embeddings

## 🎯 Performance Optimization

### Code Simplification
- **Previous**: 500+ lines of complex code
- **Current**: Simplified to under 200 lines (60% reduction)
- **Method Integration**: Removed duplicates, single responsibility principle

### LLM Optimization
- **LangChain Integration**: Uses LangChain instead of direct OpenAI calls
- **Prompt Engineering**: Improved SQL generation accuracy
- **Error Handling**: Implemented fallback mechanism

### Search Performance
- **SQL Pre-filtering**: Prevents unnecessary vector operations
- **FAISS IndexFlatIP**: High-speed inner product based search
- **Dynamic Indexing**: Indexes only filtered results

## 📊 API Endpoints

### POST /search
Unified search API

**Request:**
```json
{
  "query": "search term",
  "count": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "Course Name",
      "department": "Department",
      "professor": "Professor Name",
      "similarity_score": 0.95
    }
  ]
}
```

