# JBNU AI Mentor - LLM Agent Service

**JBNU AI 멘토 시스템의 핵심 LLM 에이전트 서비스**

## 📖 개요

LLM Agent는 JBNU AI Mentor 시스템의 중심 서비스로, LangGraph 기반의 복잡도별 쿼리 처리와 다중 데이터 소스 통합을 통해 지능형 교육 상담 서비스를 제공합니다.

## 🏗️ 아키텍처

### 핵심 구성요소
```
llm_agent-main/
├── main.py                       # FastAPI 애플리케이션 진입점
├── controller/
│   └── agentController.py        # API 컨트롤러
├── service/
│   ├── core/
│   │   ├── unified_langgraph_app.py   # 통합 LangGraph 애플리케이션
│   │   ├── langgraph_state.py         # LangGraph 상태 관리
│   │   └── memory.py                  # 대화 메모리 관리
│   ├── analysis/
│   │   ├── query_analyzer.py          # 쿼리 복잡도 분석
│   │   ├── context_analyzer.py        # 컨텍스트 분석
│   │   └── result_synthesizer.py      # 결과 합성
│   └── nodes/
│       └── node_manager.py            # LangGraph 노드 관리
├── processors/
│   ├── router.py                 # 라우팅 로직
│   └── chain_processor.py        # 체인 처리기
├── handlers/
│   ├── vector_search_handler.py  # FAISS 벡터 검색
│   ├── sql_query_handler.py      # SQL 데이터베이스
│   ├── department_mapping_handler.py  # 학과 매핑
│   └── curriculum_handler.py     # 커리큘럼 계획
├── utils/
│   ├── llm_client_langchain.py   # LangChain LLM 클라이언트
│   ├── prompt_loader.py          # 프롬프트 관리
│   └── json_utils.py             # JSON 유틸리티
├── prompts/                      # 프롬프트 템플릿
├── config/
│   └── settings.py               # 설정 관리
└── logs/                         # 로그 파일
```

## 🚀 주요 기능

### 1. LangGraph 기반 복잡도별 처리

#### Light 복잡도
- **일반 질문**: 직접 LLM 응답
- **인사말**: 간단한 환영 메시지

#### Medium 복잡도
- **SQL 쿼리**: 데이터베이스 검색
- **벡터 검색**: FAISS 기반 유사도 검색
- **커리큘럼**: 학습 계획 수립
- **에이전트**: 특수 도메인 처리

#### Heavy 복잡도
- **순차 처리**: 여러 데이터 소스 순차 활용
- **복합 쿼리**: 다단계 추론 필요

### 2. 쿼리 분석 시스템

#### 병렬 분석 (analyze_query_parallel)
```python
# 1단계: 쿼리 확장
expansion_result = await self._expand_query_async(query, history_context)

# 2단계: 향상된 쿼리 생성
enhanced_query = self._combine_expansion_with_query(query, expansion_result)

# 3단계: 라우팅 분석
analysis_result = await self._analyze_routing_async(enhanced_query, contextual_prompt, history_context)
```

#### 확장 정보
- **expansion_context**: 배경 정보
- **expansion_keywords**: 관련 키워드
- **expanded_queries**: 벡터 검색용 확장 쿼리

### 3. 다중 데이터 소스 통합

#### 외부 서비스 연동
```python
# 설정 파일 (config/settings.py)
sql_query_url = "http://svc7999:7999/api/v1/agent"           # SQL 데이터베이스
faiss_search_url = "http://svc7997:7997/search"             # 벡터 검색
curriculum_plan_url = "http://localhost:7996/chat"          # 커리큘럼 계획
department_mapping_url = "http://department-mapping:8000/agent"  # 학과 매핑
llm_fallback_url = "http://svc7998:7998/agent"              # 폴백 LLM
```

## 📡 API 엔드포인트

### 메인 에이전트 API
```http
POST /api/v2/agent
Content-Type: application/json

{
  "message": "컴퓨터공학과 졸업요건을 알려주세요",
  "session_id": "user123",
  "stream": false
}
```

### 스트리밍 API
```http
POST /api/v2/agent-stream
Content-Type: application/json

{
  "message": "머신러닝 공부 계획을 세워주세요",
  "session_id": "user123"
}
```

### OpenAI 호환 API
```http
POST /api/chat/completions
Content-Type: application/json

{
  "model": "ai-mentor",
  "messages": [
    {"role": "user", "content": "프로그래밍 언어 추천해주세요"}
  ],
  "stream": true
}
```

## 🔧 핵심 구성요소 상세

### UnifiedLangGraphApp (service/core/unified_langgraph_app.py)

**통합 LangGraph 애플리케이션 - 모든 복잡도 처리**

```python
class UnifiedLangGraphApp:
    def __init__(self, conversation_memory: ConversationMemory = None):
        # 기존 컴포넌트들 초기화
        self.query_analyzer = QueryAnalyzer()
        self.vector_handler = VectorSearchHandler()
        self.sql_handler = SqlQueryHandler()
        # ... 기타 핸들러들

        # 그래프 빌드
        self.graph = self._build_unified_graph()
```

**그래프 흐름:**
```
START → router → [복잡도별 노드] → synthesis → finalize → END
```

### QueryAnalyzer (service/analysis/query_analyzer.py)

**LangChain 기반 쿼리 분석기**

**주요 메서드:**
- `analyze_query_parallel()`: 병렬 쿼리 분석 + 확장
- `_expand_query_async()`: 비동기 쿼리 확장
- `_analyze_routing_async()`: 비동기 라우팅 분석
- `_get_history_context()`: 히스토리 컨텍스트 추출

**분석 결과:**
```python
{
    "decision_question_type": "curriculum",
    "decision_data_source": "vector",
    "complexity": "medium",
    "owner_hint": "curriculum-handler",
    "plan": ["벡터 검색으로 관련 정보 수집", "커리큘럼 계획 수립"],
    "expansion_context": "컴퓨터공학과 관련 배경정보",
    "expansion_keywords": "졸업요건, 학점, 필수과목"
}
```

### NodeManager (service/nodes/node_manager.py)

**LangGraph 노드 관리자**

**제공 노드들:**
- `router`: 복잡도 분석 및 라우팅
- `light_llm`: 간단한 LLM 응답
- `light_greeting`: 인사말 처리
- `medium_sql`: SQL 데이터베이스 검색
- `medium_vector`: FAISS 벡터 검색
- `medium_curriculum`: 커리큘럼 계획
- `medium_agent`: 특수 도메인 처리
- `heavy_sequential`: 순차적 다중 처리
- `synthesis`: 결과 합성
- `finalize`: 최종 처리

### 핸들러 시스템

#### VectorSearchHandler (handlers/vector_search_handler.py)
```python
async def search_with_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    # 확장된 쿼리들을 사용한 벡터 검색
    expanded_queries = analysis_result.get("expanded_queries", [])
    # FAISS 서비스 호출
    response = await self._call_faiss_service(search_params)
```

#### SqlQueryHandler (handlers/sql_query_handler.py)
```python
async def query_with_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    # SQL 쿼리 생성 및 실행
    query_context = self._build_query_context(analysis_result)
    # SQL 서비스 호출
    response = await self._call_sql_service(query_context)
```

## ⚙️ 설정 관리

### settings.py 주요 설정

```python
class Settings(BaseSettings):
    # 기본 설정
    service_name: str = "llm-agent"
    debug: bool = False
    port: int = 8001

    # LLM 설정
    openai_api_key: Optional[str] = None
    default_model: str = "gpt-4o-mini"

    # 메모리 설정
    max_history_length: int = 20
    max_conversation_turns: int = 10

    # 복잡도 분석 임계값
    complexity_threshold: float = 0.4

    # 보안 설정
    max_message_length: int = 10000
    max_messages_per_request: int = 100

    # 성능 설정
    max_concurrent_requests: int = 100
    request_timeout: int = 30

    # 외부 서비스 URL
    sql_query_url: str = "http://svc7999:7999/api/v1/agent"
    faiss_search_url: str = "http://svc7997:7997/search"
    curriculum_plan_url: str = "http://localhost:7996/chat"
    department_mapping_url: str = "http://department-mapping:8000/agent"
    llm_fallback_url: str = "http://svc7998:7998/agent"
```

## 🔍 프롬프트 시스템

### 주요 프롬프트 템플릿

#### router_prompt.txt
```
사용자의 질문을 분석하여 적절한 처리 방법을 결정해주세요.

질문: {query}

다음 중 가장 적합한 처리 방법을 JSON 형태로 응답해주세요:
- question_type: [curriculum, course, department, general, greeting]
- data_source: [sql, vector, llm, department]
- complexity: [light, medium, heavy]
- owner_hint: [담당 서비스명]
- plan: [처리 계획 배열]
```

#### query_reasoning_prompt.txt
```
다음 질문을 분석하여 확장 정보를 제공해주세요.

질문: {query}

JSON 형태로 응답해주세요:
{
  "expansion_context": "질문의 배경 정보",
  "expansion_keywords": "관련 키워드들 (쉼표 구분)",
  "expansion_augmentation": "질문 보완 설명"
}
```

## 💾 메모리 관리

### ConversationMemory (service/core/memory.py)

**기능:**
- 세션별 대화 히스토리 관리
- 최근 교환 내역 추출
- 컨텍스트 요약 생성

```python
class ConversationMemory:
    def add_exchange(self, session_id: str, user_message: str, ai_response: str):
        # 대화 교환 저장

    def get_recent_exchanges(self, session_id: str, limit: int = 5):
        # 최근 대화 반환

    def get_context_summary(self, session_id: str):
        # 컨텍스트 요약 생성
```

## 🚀 실행 방법

### 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
export OPENAI_API_KEY="your-api-key"

# 서비스 실행
python main.py
```

### Docker 환경
```bash
# 컨테이너 빌드
docker build -t llm-agent .

# 컨테이너 실행
docker run -p 8001:8001 \
  -e OPENAI_API_KEY="your-api-key" \
  llm-agent
```

## 📊 모니터링 및 로깅

### 로그 설정
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

### 성능 통계
```python
# QueryAnalyzer에서 제공
stats = query_analyzer.get_performance_stats()
{
    "analyzer_type": "LangChain_v3",
    "total_analyses": 1250,
    "avg_analysis_time": 0.45,
    "success_rate": 99.2
}
```
