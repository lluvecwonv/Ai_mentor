# JBNU AI Mentor - LLM Agent Service

**Core LLM Agent Service for JBNU AI Mentor System**

## 📖 Overview

LLM Agent is the central service of the JBNU AI Mentor system, providing intelligent educational counseling services through LangGraph-based complexity-aware query processing and multi-data source integration.

## 🏗️ Architecture

### Core Components
```
llm_agent-main/
├── main.py                       # FastAPI application entry point
├── controller/
│   └── agentController.py        # API controller
├── service/
│   ├── core/
│   │   ├── unified_langgraph_app.py   # Unified LangGraph application
│   │   ├── langgraph_state.py         # LangGraph state management
│   │   └── memory.py                  # Conversation memory management
│   ├── analysis/
│   │   ├── query_analyzer.py          # Query complexity analysis
│   │   ├── context_analyzer.py        # Context analysis
│   │   └── result_synthesizer.py      # Result synthesis
│   └── nodes/
│       └── node_manager.py            # LangGraph node management
├── processors/
│   ├── router.py                 # Routing logic
│   └── chain_processor.py        # Chain processor
├── handlers/
│   ├── vector_search_handler.py  # FAISS vector search
│   ├── sql_query_handler.py      # SQL database
│   ├── department_mapping_handler.py  # Department mapping
│   └── curriculum_handler.py     # Curriculum planning
├── utils/
│   ├── llm_client_langchain.py   # LangChain LLM client
│   ├── prompt_loader.py          # Prompt management
│   └── json_utils.py             # JSON utilities
├── prompts/                      # Prompt templates
├── config/
│   └── settings.py               # Configuration management
└── logs/                         # Log files
```

## 🚀 Key Features

### 1. LangGraph-Based Complexity Processing

#### Light Complexity
- **General Questions**: Direct LLM responses
- **Greetings**: Simple welcome messages

#### Medium Complexity
- **SQL Queries**: Database search
- **Vector Search**: FAISS-based similarity search
- **Curriculum**: Learning plan development
- **Agent**: Special domain processing

#### Heavy Complexity
- **Sequential Processing**: Sequential utilization of multiple data sources
- **Complex Queries**: Multi-step reasoning required

### 2. Query Analysis System

#### Parallel Analysis (analyze_query_parallel)
```python
# Step 1: Query expansion
expansion_result = await self._expand_query_async(query, history_context)

# Step 2: Enhanced query generation
enhanced_query = self._combine_expansion_with_query(query, expansion_result)

# Step 3: Routing analysis
analysis_result = await self._analyze_routing_async(enhanced_query, contextual_prompt, history_context)
```

#### Expansion Information
- **expansion_context**: Background information
- **expansion_keywords**: Related keywords
- **expanded_queries**: Expanded queries for vector search

### 3. Multi-Data Source Integration

#### External Service Integration
```python
# Configuration file (config/settings.py)
sql_query_url = "http://svc7999:7999/api/v1/agent"           # SQL Database
faiss_search_url = "http://svc7997:7997/search"             # Vector Search
curriculum_plan_url = "http://localhost:7996/chat"          # Curriculum Planning
department_mapping_url = "http://department-mapping:8000/agent"  # Department Mapping
llm_fallback_url = "http://svc7998:7998/agent"              # Fallback LLM
```

## 📡 API Endpoints

### Main Agent API
```http
POST /api/v2/agent
Content-Type: application/json

{
  "message": "Please tell me the graduation requirements for Computer Science",
  "session_id": "user123",
  "stream": false
}
```

### Streaming API
```http
POST /api/v2/agent-stream
Content-Type: application/json

{
  "message": "Please create a machine learning study plan",
  "session_id": "user123"
}
```

### OpenAI Compatible API
```http
POST /api/chat/completions
Content-Type: application/json

{
  "model": "ai-mentor",
  "messages": [
    {"role": "user", "content": "Please recommend programming languages"}
  ],
  "stream": true
}
```

## 🔧 Core Components Detail

### UnifiedLangGraphApp (service/core/unified_langgraph_app.py)

**Unified LangGraph Application - Handles All Complexity Levels**

```python
class UnifiedLangGraphApp:
    def __init__(self, conversation_memory: ConversationMemory = None):
        # Initialize existing components
        self.query_analyzer = QueryAnalyzer()
        self.vector_handler = VectorSearchHandler()
        self.sql_handler = SqlQueryHandler()
        # ... other handlers

        # Build graph
        self.graph = self._build_unified_graph()
```

**Graph Flow:**
```
START → router → [complexity-based nodes] → synthesis → finalize → END
```

### QueryAnalyzer (service/analysis/query_analyzer.py)

**LangChain-Based Query Analyzer**

**Key Methods:**
- `analyze_query_parallel()`: Parallel query analysis + expansion
- `_expand_query_async()`: Asynchronous query expansion
- `_analyze_routing_async()`: Asynchronous routing analysis
- `_get_history_context()`: History context extraction

**Analysis Result:**
```python
{
    "decision_question_type": "curriculum",
    "decision_data_source": "vector",
    "complexity": "medium",
    "owner_hint": "curriculum-handler",
    "plan": ["Collect information via vector search", "Develop curriculum plan"],
    "expansion_context": "Background information about Computer Science",
    "expansion_keywords": "graduation requirements, credits, required courses"
}
```

### NodeManager (service/nodes/node_manager.py)

**LangGraph Node Manager**

**Available Nodes:**
- `router`: Complexity analysis and routing
- `light_llm`: Simple LLM responses
- `light_greeting`: Greeting handling
- `medium_sql`: SQL database search
- `medium_vector`: FAISS vector search
- `medium_curriculum`: Curriculum planning
- `medium_agent`: Special domain processing
- `heavy_sequential`: Sequential multi-processing
- `synthesis`: Result synthesis
- `finalize`: Final processing

### Handler System

#### VectorSearchHandler (handlers/vector_search_handler.py)
```python
async def search_with_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    # Vector search using expanded queries
    expanded_queries = analysis_result.get("expanded_queries", [])
    # Call FAISS service
    response = await self._call_faiss_service(search_params)
```

#### SqlQueryHandler (handlers/sql_query_handler.py)
```python
async def query_with_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    # Generate and execute SQL query
    query_context = self._build_query_context(analysis_result)
    # Call SQL service
    response = await self._call_sql_service(query_context)
```

## ⚙️ Configuration Management

### Key Settings in settings.py

```python
class Settings(BaseSettings):
    # Basic settings
    service_name: str = "llm-agent"
    debug: bool = False
    port: int = 8001

    # LLM settings
    openai_api_key: Optional[str] = None
    default_model: str = "gpt-4o-mini"

    # Memory settings
    max_history_length: int = 20
    max_conversation_turns: int = 10

    # Complexity analysis threshold
    complexity_threshold: float = 0.4

    # Security settings
    max_message_length: int = 10000
    max_messages_per_request: int = 100

    # Performance settings
    max_concurrent_requests: int = 100
    request_timeout: int = 30

    # External service URLs
    sql_query_url: str = "http://svc7999:7999/api/v1/agent"
    faiss_search_url: str = "http://svc7997:7997/search"
    curriculum_plan_url: str = "http://localhost:7996/chat"
    department_mapping_url: str = "http://department-mapping:8000/agent"
    llm_fallback_url: str = "http://svc7998:7998/agent"
```

## 🔍 Prompt System

### Key Prompt Templates

#### router_prompt.txt
```
Analyze the user's question and determine the appropriate processing method.

Question: {query}

Please respond in JSON format with the most suitable processing method:
- question_type: [curriculum, course, department, general, greeting]
- data_source: [sql, vector, llm, department]
- complexity: [light, medium, heavy]
- owner_hint: [responsible service name]
- plan: [processing plan array]
```

#### query_reasoning_prompt.txt
```
Analyze the following question and provide expansion information.

Question: {query}

Please respond in JSON format:
{
  "expansion_context": "Background information of the question",
  "expansion_keywords": "Related keywords (comma-separated)",
  "expansion_augmentation": "Question supplementary explanation"
}
```

## 💾 Memory Management

### ConversationMemory (service/core/memory.py)

**Features:**
- Session-based conversation history management
- Recent exchange retrieval
- Context summary generation

```python
class ConversationMemory:
    def add_exchange(self, session_id: str, user_message: str, ai_response: str):
        # Store conversation exchange

    def get_recent_exchanges(self, session_id: str, limit: int = 5):
        # Return recent conversations

    def get_context_summary(self, session_id: str):
        # Generate context summary
```

## 🚀 Running the Service

### Development Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-api-key"

# Run service
python main.py
```

### Docker Environment
```bash
# Build container
docker build -t llm-agent .

# Run container
docker run -p 8001:8001 \
  -e OPENAI_API_KEY="your-api-key" \
  llm-agent
```

## 📊 Monitoring and Logging

### Log Configuration
```python
LOGGING_CONFIG = {
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "default",
        },
        "file": {
            "level": "DEBUG",
            "filename": "/path/to/logs/llm-agent.log",
        },
    }
}
```

### Performance Statistics
```python
# Provided by QueryAnalyzer
stats = query_analyzer.get_performance_stats()
{
    "analyzer_type": "LangChain_v3",
    "total_analyses": 1250,
    "avg_analysis_time": 0.45,
    "success_rate": 99.2
}
```
