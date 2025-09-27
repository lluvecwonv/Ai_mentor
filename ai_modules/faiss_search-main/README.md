# FAISS 벡터 검색 서비스 🔍

전북대학교 강의를 위한 AI 기반 하이브리드 검색 시스템

## ✨ 핵심 기능

- **LangChain LLM 통합**: 자연어 쿼리를 SQL로 자동 변환
- **FAISS 벡터 검색**: OpenAI 임베딩 기반 의미 유사도 검색
- **하이브리드 검색**: LLM SQL 필터링 + 벡터 검색 결합
- **간소화된 아키텍처**: 최소한의 코드로 최대 성능

## 🏗️ 프로젝트 구조

```
faiss_search-main/
├── controller/
│   └── searchController.py     # FastAPI 엔드포인트 (46줄)
├── service/
│   └── searchService.py        # 검색 서비스 (110줄)
├── util/
│   ├── langchainLlmClient.py   # LangChain LLM 클라이언트
│   ├── dbClient.py             # MySQL 연결 관리
│   └── utils.py                # 유틸리티 함수
├── prompts/
│   └── sql_prefilter_generator.txt  # SQL 생성 프롬프트
└── main.py                     # FastAPI 앱 (40줄)
```

## 🔄 검색 플로우

```
사용자 쿼리 ("컴공 인공지능 수업")
    ↓
[1] LLM이 SQL 생성
    - LangChain 사용
    - 프롬프트 기반 SQL WHERE 절 생성
    ↓
[2] MySQL 필터링
    - 관련 강의만 선별
    - 벡터 데이터 포함
    ↓
[3] FAISS 벡터 검색
    - OpenAI 임베딩 생성
    - 유사도 계산
    ↓
[4] 결과 반환
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 (.env)
OPENAI_API_KEY=your_api_key
DB_HOST=your_host
DB_PASSWORD=your_password
```

### 2. 서버 실행

```bash
python main.py
# http://localhost:7997 에서 실행
```

### 3. API 사용

```bash
# 검색 요청
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "머신러닝 관련 수업",
    "count": 10
  }'
```

## 📚 주요 컴포넌트

### SearchService (간소화됨)

```python
class SearchService:
    def __init__(self, db_client):
        self.llm_client = LangchainLlmClient()  # LLM 내부 관리
        self.db_client = db_client              # DB 외부 주입

    def search_hybrid(query_text, count):
        # 1. LLM으로 SQL 생성
        # 2. DB에서 필터링
        # 3. 벡터 검색
        # 4. 결과 반환
```

### LangchainLlmClient

- **ChatOpenAI**: GPT-4o-mini 모델 사용
- **OpenAIEmbeddings**: text-embedding-ada-002
- **통합 관리**: LLM과 임베딩 모델 한 곳에서 관리

### 유틸리티 함수

- `load_prompt()`: 프롬프트 파일 로드
- `extract_sql_from_response()`: LLM 응답에서 SQL 추출
- `prepare_vectors()`: 벡터 데이터 준비
- `generate_embedding()`: 텍스트 임베딩 생성

## 🎯 성능 최적화

### 코드 간소화
- **이전**: 500+ 줄의 복잡한 코드
- **현재**: 200줄 이하로 간소화 (60% 감소)
- **메서드 통합**: 중복 제거, 단일 책임 원칙

### LLM 최적화
- **LangChain 통합**: OpenAI 직접 호출 대신 LangChain 사용
- **프롬프트 엔지니어링**: SQL 생성 정확도 향상
- **에러 처리**: 폴백 메커니즘 구현

### 검색 성능
- **SQL 사전 필터링**: 불필요한 벡터 연산 방지
- **FAISS IndexFlatIP**: 고속 내적 기반 검색
- **동적 인덱싱**: 필터링된 결과만 인덱싱

## 📊 API 엔드포인트

### POST /search
통합 검색 API

**요청:**
```json
{
  "query": "검색어",
  "count": 10
}
```

**응답:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "과목명",
      "department": "학과",
      "professor": "교수명",
      "similarity_score": 0.95
    }
  ]
}
```

## 🔧 설치 요구사항

```txt
fastapi
uvicorn
langchain
langchain-openai
faiss-cpu
pymysql
python-dotenv
numpy
httpx
```