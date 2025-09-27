# FAISS 기반 벡터 검색 서비스 🔍

전북대학교 강의 검색을 위한 고성능 하이브리드 검색 엔진

## 🎯 주요 기능

### 🔍 지능형 검색
- **OpenAI embedding** 기반 의미 유사도 검색
- **FAISS 라이브러리** 활용 고성능 벡터 검색
- **LLM 기반 SQL 쿼리** 자동 생성으로 정확한 필터링
- **하이브리드 검색**: SQL 필터링 + 벡터 검색 결합

### 🎛️ 고급 필터링
- **학과별 필터링**: "컴공", "전전" 등 자연어 입력 지원
- **교수별 검색**: 특정 교수의 강의 검색
- **키워드 부스팅**: 관련 키워드 포함 결과 우선순위 상승
- **다중 쿼리 가중 병합**: 여러 검색어의 결과를 최적 조합

### 📊 메타데이터 보강
- **정확한 메타데이터 매칭**: 과목명 + 학과명 기반 중복 방지
- **완전한 강의 정보**: 교수명, 시간표, 강의실, 학점, 선수과목 등
- **실시간 데이터 동기화**: MySQL 데이터베이스와 실시간 연동

## 🏗️ 아키텍처

### 핵심 컴포넌트

```
📁 service/
├── 🚀 searchService.py      # 메인 하이브리드 검색 엔진
├── 🔍 queryService.py       # SQL 쿼리 생성 및 실행
└── ⚙️ search_core.py        # 검색 결과 후처리 유틸리티
```

### 데이터 플로우

```mermaid
graph TB
    A[사용자 쿼리: "컴공에서 인공지능 관련 수업"] --> B[LLM SQL 쿼리 생성]
    B --> C["SQL: WHERE department LIKE '%컴퓨터%'"]
    C --> D[MySQL에서 관련 강의 사전 필터링]
    D --> E[OpenAI Embedding 생성]
    E --> F[FAISS 벡터 검색]
    F --> G[키워드 부스팅 + 정렬]
    G --> H[메타데이터 병합]
    H --> I[최종 검색 결과 반환]
```

## 🔧 주요 클래스 및 함수

### SearchService
메인 하이브리드 검색 엔진

#### 핵심 메서드
- `search_hybrid()`: **SQL+벡터 하이브리드 검색** (최적화됨)
- `search_simple()`: 단순 벡터 검색
- `_search_in_filtered_courses()`: 필터링된 범위에서만 벡터 검색
- `generate_embedding()`: 텍스트 임베딩 생성

### QueryService
SQL 쿼리 생성 및 실행 서비스

#### 핵심 메서드
- `generate_sql()`: LLM으로 SQL 쿼리 생성
- `get_filtered_courses()`: SQL 쿼리 생성 → 실행 → 벡터 데이터 반환
- `_execute_sql_with_vectors()`: 벡터 데이터 포함한 SQL 실행

### search_core 유틸리티
검색 결과 후처리 및 메타데이터 병합

#### 핵심 함수
- `build_candidates()`: FAISS 결과를 구조화된 후보로 변환
- `filter_and_sort_candidates()`: 키워드 기반 필터링 및 정렬
- `attach_sql_metadata()`: **SQL 메타데이터 병합** (과목명+학과명 매칭)
- `apply_department_filter()`: 학과 기반 필터링

## 🚀 성능 최적화

### 검색 성능
- **FAISS IndexFlatIP**: 내적 기반 고속 벡터 검색
- **개선된 SQL 사전 필터링**: 전체 벡터 검색 → 필터링된 범위에서만 검색
- **임시 FAISS 인덱스**: SQL로 추려진 강의들만으로 최적화된 벡터 검색
- **메모리 효율성**: 불필요한 벡터 검색 제거로 50-90% 성능 향상

### 정확도 개선
- **스마트 스코어링**: 유사도(80%) + 키워드 매칭(20%) 가중 조합
- **중복 제거**: 학과명 기반 정확한 메타데이터 매칭
- **컨텍스트 인식**: LLM이 쿼리 의도를 파악하여 최적 SQL 생성

### 메모리 효율성
- **벡터 캐싱**: 자주 사용되는 임베딩 캐시
- **연결 풀링**: 데이터베이스 연결 재사용
- **점진적 로딩**: 필요한 데이터만 메모리에 로드

## 📊 사용 예시

### 기본 검색
```python
# 컴퓨터인공지능학부의 인공지능 관련 수업 검색
curl -X POST "http://localhost:7997/search-sql-filter" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "컴공에서 인공지능 관련 수업",
    "top_k": 10
  }'
```

### 고급 검색
```python
# 특정 교수의 머신러닝 관련 수업
curl -X POST "http://localhost:7997/search-sql-filter" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "나승훈 교수님 머신러닝 수업",
    "count": 5
  }'
```

### 🚀 최적화된 하이브리드 검색
```python
# 간단하고 빠른 하이브리드 검색 (권장)
curl -X POST "http://localhost:7997/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "컴공에서 딥러닝 관련 강의",
    "count": 10,
    "department": "컴퓨터인공지능학부"
  }'
```

