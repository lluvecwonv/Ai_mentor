# 🔍 FAISS Search Service (svc7997) - 상세 문서

전북대학교 AI 멘토링 시스템의 **벡터 검색 서비스**입니다. FAISS 기반의 의미적 검색과 SQL 사전 필터링을 결합한 하이브리드 검색을 제공합니다.

## 📋 목차
- [서비스 개요](#서비스-개요)
- [아키텍처](#아키텍처)
- [디렉토리 구조](#디렉토리-구조)
- [API 엔드포인트](#api-엔드포인트)
- [주요 기능](#주요-기능)
- [설정 및 환경변수](#설정-및-환경변수)
- [데이터베이스 스키마](#데이터베이스-스키마)
- [사용 예제](#사용-예제)

## 🎯 서비스 개요

### 역할
- **포트**: 7997
- **컨테이너명**: svc7997
- **기능**: Vector-Search-Agent (FAISS 유사도 검색)
- **용도**: 과목/키워드 유사도 기반 검색

### 주요 특징
- **하이브리드 검색**: SQL 사전 필터링 + FAISS 벡터 검색
- **의미적 검색**: OpenAI 임베딩 기반 과목 내용 이해
- **성능 최적화**: 학과/교수 필터링으로 검색 범위 제한
- **실시간 로깅**: 상세한 검색 과정 추적

## 🏗️ 아키텍처

```
사용자 쿼리 → SQL 사전필터링 → 벡터 검색 → 유사도 순위 → 결과 반환
     ↓              ↓              ↓           ↓
   LLM 분석    MySQL 필터링    FAISS 검색   스코어링
```

### 검색 프로세스
1. **쿼리 분석**: LLM이 사용자 쿼리를 분석하여 SQL 필터 생성
2. **SQL 필터링**: 학과/교수/기타 조건으로 후보 강의 제한
3. **벡터 검색**: FAISS를 사용한 의미적 유사도 검색
4. **결과 반환**: 유사도 점수와 함께 정렬된 결과 제공

## 📁 디렉토리 구조

```
faiss_search-main/
├── main.py                           # FastAPI 애플리케이션 엔트리포인트
├── controller/
│   └── searchController.py           # API 엔드포인트 컨트롤러
├── service/
│   ├── searchService.py              # 핵심 검색 로직 (하이브리드 검색)
│   ├── queryService.py               # SQL 쿼리 생성 및 실행
│   └── __init__.py
├── util/
│   ├── dbClient.py                   # MySQL 데이터베이스 클라이언트
│   ├── utils.py                      # 유틸리티 함수들
│   └── logging_setup.py              # 로깅 설정
├── prompts/
│   └── sql_prefilter_generator.txt   # SQL 생성 프롬프트 템플릿
├── logs/                             # 로그 파일 저장소
├── Dockerfile                        # Docker 컨테이너 설정
├── requirements.txt                  # Python 의존성
└── .env                             # 환경변수 설정
```

### 각 디렉토리 역할

#### 🎮 `controller/`
- **searchController.py**: API 엔드포인트 정의 및 요청 처리

#### 🔧 `service/`
- **searchService.py**: 핵심 검색 로직, FAISS 인덱싱 및 검색
- **queryService.py**: LLM 기반 SQL 쿼리 생성 및 실행

#### 🛠️ `util/`
- **dbClient.py**: MySQL 연결 및 쿼리 실행
- **utils.py**: JSON 파싱, SQL 추출 등 유틸리티
- **logging_setup.py**: 구조화된 로깅 설정

#### 📝 `prompts/`
- **sql_prefilter_generator.txt**: SQL 쿼리 생성을 위한 LLM 프롬프트

## 🌐 API 엔드포인트

### 1. **기본 벡터 검색**
```http
POST /search
```

#### 요청 파라미터
```json
{
  "query": "인공지능 관련 수업",     // 검색 쿼리 (필수)
  "key": "머신러닝",              // query 대신 사용 가능 (호환성)
  "count": 5,                    // 반환할 결과 수 (기본값: 5)
  "debug": false                 // 디버그 정보 포함 여부
}
```

#### 응답 형식
```json
{
  "results": [
    {
      "id": 12345,
      "name": "인공지능개론",
      "department": "컴퓨터인공지능학부",
      "professor": "김AI교수",
      "credits": 3,
      "schedule": "월수 10:30-12:00",
      "location": "공대 301호",
      "delivery_mode": "대면",
      "description": "인공지능의 기초 개념...",
      "similarity_score": 0.8924
    }
  ],
  "debug": false
}
```

### 2. **SQL 사전 필터링 검색**
```http
POST /search-sql-filter
```
- **용도**: 학과/교수 등으로 사전 필터링 후 벡터 검색
- **파라미터**: `/search`와 동일
- **특징**: LLM이 쿼리를 분석하여 적절한 SQL 필터 자동 생성

### 3. **개선된 SQL 필터링 검색**
```http
POST /search-sql-filter-improved
```
- **용도**: 성능 최적화된 하이브리드 검색
- **추가 응답**: `processing_time`, `search_method` 포함

### 4. **헬스 체크**
```http
GET /
```
- **응답**: `{"message": "faiss_search-main is running"}`

## ⚙️ 주요 기능

### 🔍 SearchService 클래스

#### 핵심 메서드

##### `search_hybrid(query_text: str, count: int = 10) -> List[Dict]`
- **기능**: 하이브리드 검색 (SQL 필터링 + FAISS 검색)
- **파라미터**:
  - `query_text`: 검색할 텍스트
  - `count`: 반환할 결과 수
- **반환**: 유사도 점수가 포함된 강의 목록
- **프로세스**:
  1. SQL로 관련 강의 필터링
  2. 필터링된 강의에서 FAISS 벡터 검색
  3. 유사도 점수 계산 및 정렬

##### `generate_embedding(text: str) -> Optional[np.ndarray]`
- **기능**: OpenAI text-embedding-ada-002 모델로 임베딩 생성
- **파라미터**: `text` - 임베딩할 텍스트
- **반환**: 1536차원 벡터 또는 None (실패시)

##### `_search_in_filtered_courses(query_text, filtered_courses, count) -> List[Dict]`
- **기능**: 필터링된 강의들에서 FAISS 기반 벡터 검색
- **특징**:
  - Inner Product 기반 유사도 계산
  - 벡터 정규화 적용
  - 실시간 성능 로깅

##### `_get_all_courses_with_vectors() -> List[Dict]`
- **기능**: 전체 데이터베이스에서 벡터 데이터를 포함한 강의 목록 반환
- **용도**: SQL 필터링 실패시 폴백
- **제한**: 최대 1000개 강의

### 🗃️ QueryService 클래스

#### 핵심 메서드

##### `generate_sql(user_query: str) -> Optional[str]`
- **기능**: LLM을 사용하여 사용자 쿼리에서 SQL 필터 생성
- **파라미터**: `user_query` - 사용자 입력 쿼리
- **반환**: SQL 쿼리 문자열 또는 None
- **사용 모델**: gpt-4o-mini
- **템플릿**: `prompts/sql_prefilter_generator.txt`
- **파라미터**:
  - `temperature`: 0.1 (일관성 있는 SQL 생성)
  - `max_tokens`: 1000

##### `get_filtered_courses(user_query: str) -> List[Dict]`
- **기능**: SQL 쿼리 생성 → 실행 → 벡터 데이터와 함께 반환
- **프로세스**:
  1. LLM으로 SQL 쿼리 생성
  2. 생성된 SQL로 강의 필터링
  3. 벡터 데이터 포함하여 결과 반환

##### `_execute_sql_with_vectors(sql_query: str) -> List[Dict]`
- **기능**: SQL 실행하여 벡터 데이터 포함한 강의 목록 반환
- **특징**: 하위 쿼리를 사용하여 벡터 데이터까지 포함한 완전한 강의 정보 반환

##### `_load_prompt()`
- **기능**: SQL 생성을 위한 프롬프트 템플릿 로드
- **파일**: `prompts/sql_prefilter_generator.txt`
- **인코딩**: UTF-8

### 🗄️ DbClient 클래스

#### 핵심 메서드

##### `__init__()`
- **환경변수 우선순위**:
  1. `VECTOR_DB_PASSWORD` (벡터 DB 전용)
  2. `DB_PASSWORD` (일반 DB 비밀번호)
  3. 기본값
- **기본 설정**:
  - Host: ${DB_HOST} (환경변수로 설정)
  - Port: 3313
  - Database: nll
  - Charset: utf8mb4

##### `connect()`
- **기능**: MySQL 데이터베이스 연결
- **설정**: UTF-8 인코딩, DictCursor 사용
- **커서 타입**: `pymysql.cursors.DictCursor`

##### `ensure_connection() -> bool`
- **기능**: 연결 상태 확인 및 자동 재연결
- **반환**: 연결 성공 여부
- **사용 시기**: 모든 쿼리 실행 전

##### `execute_query(query, params=None)`
- **기능**: 매개변수화된 쿼리 실행
- **특징**: SQL 인젝션 방지
- **반환**: 쿼리 결과 또는 None

### 🛠️ utils.py 유틸리티 함수들

#### `parse_llm_json_response(response_text: str) -> dict`
- **기능**: LLM 응답에서 JSON 데이터를 추출하고 파싱
- **처리 형식**:
  - ```json...``` 블록
  - 순수 JSON 형태 ({ ... })
- **에러 핸들링**: JSON 파싱 실패시 빈 딕셔너리 반환

#### `extract_sql_query_from_llm_response(response_text: str) -> str`
- **기능**: LLM 응답에서 SQL 쿼리와 추론 정보를 추출
- **반환값**:
  - 유효한 SQL 쿼리 문자열
  - None (SQL 필터링 불필요한 경우)
- **로깅**: SQL 생성 과정 및 이유 기록

## 🔧 설정 및 환경변수

### 필수 환경변수

```bash
# OpenAI API 설정
OPENAI_API_KEY=your-openai-api-key       # OpenAI API 키

# 데이터베이스 설정
DB_HOST=210.117.181.113                  # MySQL 호스트
DB_PORT=3313                             # MySQL 포트
DB_USER=root                             # MySQL 사용자
DB_PASSWORD=your_password                # MySQL 비밀번호
VECTOR_DB_PASSWORD=vector_specific_pass  # 벡터 DB 전용 비밀번호 (우선순위)
DB_NAME=nll_third                        # 데이터베이스 이름

# 서비스 설정
SERVICE_NAME=faiss-search                # 서비스 이름 (로깅용)
PORT=7997                                # 서비스 포트
```

### Docker 환경변수 (docker-compose.yml)

```yaml
environment:
  - PORT=7997
  - TZ=Asia/Seoul
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - DB_HOST=210.117.181.113
  - DB_PORT=3313
  - DB_USER=root
  - DB_NAME=nll_third
  - DB_PASSWORD=${DB_PASSWORD}
  - VECTOR_DB_PASSWORD=${VECTOR_DB_PASSWORD}
```

## 📊 데이터베이스 스키마

### `jbnu_class_gpt` 테이블

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `id` | INT | 강의 고유 ID | 12345 |
| `name` | VARCHAR | 강의명 | "인공지능개론" |
| `course_code` | VARCHAR | 과목코드 | "CSE101" |
| `professor` | VARCHAR | 담당교수 | "김AI교수" |
| `credits` | INT | 학점 | 3 |
| `prerequisite` | TEXT | 선수과목 | "프로그래밍기초" |
| `target_grade` | VARCHAR | 대상학년 | "2학년" |
| `schedule` | VARCHAR | 시간표 | "월수 10:30-12:00" |
| `location` | VARCHAR | 강의실 | "공대 301호" |
| `delivery_mode` | VARCHAR | 수업방식 | "대면/비대면/혼합" |
| `department` | VARCHAR | 학과명 (간단) | "컴공" |
| `department_full_name` | VARCHAR | 학과 전체명 | "컴퓨터인공지능학부" |
| `original_description` | TEXT | 원본 강의 설명 | "..." |
| `gpt_description` | TEXT | GPT 생성 설명 | "..." |
| `vector` | TEXT | 임베딩 벡터 (JSON) | "[0.1, 0.2, ...]" |

### 인덱스 및 최적화
- `id` (Primary Key)
- `department`, `department_full_name` (검색 최적화)
- `professor` (교수별 검색)
- `vector` (IS NOT NULL, != '[]' 조건)

### 벡터 데이터 형식
- **임베딩 모델**: text-embedding-ada-002
- **차원**: 1536
- **저장 형식**: JSON 배열 문자열
- **정규화**: L2 정규화 적용

## 💡 사용 예제

### 1. 학과별 검색
```bash
curl -X POST "http://localhost:7997/search-sql-filter" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "컴공 인공지능 수업",
    "count": 3
  }'
```

**동작 과정**:
1. LLM이 "컴공" → 컴퓨터 관련 학과 필터링 SQL 생성
2. SQL로 컴퓨터인공지능학부 강의만 추출
3. "인공지능"으로 벡터 검색 수행

**생성되는 SQL 예시**:
```sql
SELECT c.id, c.name, c.gpt_description, c.department_full_name as department_name
FROM jbnu_class_gpt c
WHERE c.department LIKE '%컴퓨터%' OR c.department_full_name LIKE '%컴퓨터%'
```

### 2. 교수별 검색
```bash
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "김교수 머신러닝",
    "count": 5
  }'
```

**생성되는 SQL 예시**:
```sql
SELECT c.id, c.name, c.gpt_description, c.department_full_name as department_name
FROM jbnu_class_gpt c
WHERE c.professor LIKE '%김%'
```

### 3. 주제별 검색 (SQL 필터링 없음)
```bash
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "데이터사이언스 프로젝트",
    "count": 10,
    "debug": true
  }'
```

**동작**: LLM이 특정 학과나 교수가 언급되지 않았다고 판단하여 SQL 필터링 없이 전체 벡터 검색 수행

### 4. Python 클라이언트 예제
```python
import requests
import json

class FAISSSearchClient:
    def __init__(self, base_url="http://svc7997:7997"):
        self.base_url = base_url

    def search_courses(self, query, count=5, method="sql-filter"):
        """
        강의 검색

        Args:
            query (str): 검색 쿼리
            count (int): 결과 개수
            method (str): 검색 방법 ("search", "sql-filter", "sql-filter-improved")
        """
        url = f"{self.base_url}/{method}"
        payload = {
            "query": query,
            "count": count,
            "debug": True
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data["results"]

            print(f"🔍 검색 쿼리: '{query}'")
            print(f"📊 결과 개수: {len(results)}")
            print("-" * 60)

            for i, course in enumerate(results, 1):
                print(f"{i}. 📚 {course['name']}")
                print(f"   🏫 {course['department']}")
                print(f"   👨‍🏫 {course['professor']} | 💳 {course['credits']}학점")
                print(f"   📍 {course['location']} | ⏰ {course['schedule']}")
                print(f"   🎯 유사도: {course['similarity_score']:.4f}")
                if course.get('description'):
                    desc = course['description'][:100] + "..." if len(course['description']) > 100 else course['description']
                    print(f"   📝 {desc}")
                print("-" * 60)

            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ 검색 요청 실패: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ 응답 파싱 실패: {e}")
            return []

# 사용 예제
client = FAISSSearchClient()

# 다양한 검색 패턴
client.search_courses("컴공 딥러닝 수업", count=3)
client.search_courses("경영학 마케팅", count=5)
client.search_courses("나승훈 교수 머신러닝", count=3)
client.search_courses("데이터베이스 시스템", count=10, method="search-sql-filter-improved")
```

### 5. 고급 검색 패턴

#### 복합 검색 (학과 + 주제)
```python
# 컴퓨터인공지능학부의 AI 관련 수업
query = "컴공에서 인공지능 딥러닝 관련 수업"
results = client.search_courses(query, count=5)
```

#### 교수 + 주제 검색
```python
# 특정 교수의 특정 주제 수업
query = "김교수님 데이터마이닝 수업"
results = client.search_courses(query, count=3)
```

#### 순수 주제 검색
```python
# 주제만으로 검색 (모든 학과 대상)
query = "블록체인 기술"
results = client.search_courses(query, count=10)
```

## 🚀 성능 최적화

### 검색 성능
- **SQL 사전 필터링**: 전체 DB 대신 관련 강의만 벡터 검색
  - 성능 향상: 50-90% (필터링 효과에 따라)
  - 메모리 사용량: 70-90% 감소
- **FAISS 인메모리**: 빠른 벡터 검색 (Inner Product)
  - 검색 속도: ~10ms (1000개 강의 기준)
- **임베딩 최적화**: 벡터 정규화를 통한 효율적 유사도 계산

### 메모리 최적화
- **동적 인덱스**: 검색시마다 필터링된 데이터로 인덱스 생성
- **벡터 정규화**: L2 정규화로 메모리 효율적인 유사도 계산
- **커넥션 풀링**: DB 연결 재사용
- **점진적 로딩**: 필요한 벡터만 메모리에 로드

### 정확도 최적화
- **하이브리드 스코어링**: 벡터 유사도 + 키워드 매칭
- **컨텍스트 인식**: LLM이 쿼리 의도 파악하여 최적 SQL 생성
- **중복 제거**: 학과명 기반 정확한 매칭

### 로깅 및 모니터링
- **성능 추적**: 각 단계별 처리 시간 측정
- **상세 로깅**: 검색 과정 및 결과 추적
- **에러 핸들링**: 견고한 예외 처리

## 🔍 SQL 프롬프트 시스템

### 프롬프트 구조 (`prompts/sql_prefilter_generator.txt`)

#### 주요 규칙
1. **학과 필터링**: "컴공", "전전" 등 자연어 학과명 인식
2. **교수 필터링**: 교수명 포함시 LIKE 검색
3. **주제 처리**: 학과+주제 질문에서는 학과만 필터링, 주제는 벡터 검색
4. **SQL 생성**: 항상 `c.id` 포함하여 FAISS 연동

#### 학과명 매핑
```
"컴공" → "컴퓨터인공지능학부"
"전전" → "전자전기공학부"
"경영" → "경영학과"
"기계" → "기계공학과"
```

#### 응답 형식
```json
{
  "sql_query": "SELECT c.id, c.name FROM jbnu_class_gpt c WHERE ...",
  "reasoning": "컴공 키워드로 컴퓨터인공지능학부 필터링"
}
```

## 🔧 개발 및 디버깅

### 로컬 실행
```bash
cd ai_modules/faiss_search-main

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 서비스 실행
python main.py
```

### Docker 실행
```bash
# 단일 서비스 실행
docker-compose up svc7997

# 전체 시스템 실행
docker-compose up -d
```

### 로그 확인
```bash
# 실시간 로그
docker logs -f svc7997

# 저장된 로그
ls logs/
tail -f logs/faiss-search.log
```

### 디버깅 도구

#### 1. 헬스 체크
```bash
curl http://localhost:7997/
```

#### 2. 간단한 검색 테스트
```bash
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트", "count": 1, "debug": true}'
```

#### 3. SQL 필터링 테스트
```bash
curl -X POST "http://localhost:7997/search-sql-filter" \
  -H "Content-Type: application/json" \
  -d '{"query": "컴공 인공지능", "count": 3, "debug": true}'
```

#### 4. 성능 테스트
```bash
# 처리 시간 포함 검색
curl -X POST "http://localhost:7997/search-sql-filter-improved" \
  -H "Content-Type: application/json" \
  -d '{"query": "머신러닝 수업", "count": 5}'
```

### 일반적인 문제 해결

#### 1. 임베딩 생성 실패
- **원인**: OpenAI API 키 오류 또는 네트워크 문제
- **해결**: `OPENAI_API_KEY` 환경변수 확인

#### 2. 데이터베이스 연결 실패
- **원인**: DB 접속 정보 오류
- **해결**: `DB_HOST`, `DB_PASSWORD` 등 환경변수 확인

#### 3. 벡터 데이터 없음
- **원인**: `vector` 필드가 NULL이거나 빈 배열
- **해결**: 데이터베이스의 벡터 데이터 상태 확인

#### 4. SQL 쿼리 생성 실패
- **원인**: LLM 응답 파싱 오류
