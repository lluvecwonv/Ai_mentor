# Curriculum Recommendation & Graph Builder

> **모델·그래프 기반 학과‧강좌 추천 파이프라인**
>
> * OpenAI Embedding / Chat Completion API
> * FAISS 기반 Dense Retriever & Class Retriever
> * MySQL/MariaDB 강좌 메타데이터
> * NetworkX 그래프 + SVG/PNG 시각화

---

* Renranker 인자ㅏ 파일은 지워주시길 바랍니다. 

## 📁 프로젝트 구조

```
├─ aov.py                   # 그래프 생성·시각화 모듈
├─ dense_retriver.py        # 학과/강좌 임베딩 인덱스 & 검색
├─ db/
│   └─ db_search.py         # DB 연결·조회 래퍼
├─ dataset/
│   ├─ dataset.py           # Dataset 클래스 모음
│   └─ data/                # department, query, db 설정 JSON
├─ open_ai.py               # OpenAI API 유틸 (Embedding, LLM 질의확장)
├─ utils.py                 # 공용 함수 모음
├─ main.py                  # **실행 진입점**
└─ result/                  # 로그 & 그래프 결과물 출력 폴더
```

---

## 🚀 빠른 실행 예시

```bash
python main.py \
  --openai_api_key $OPENAI_API_KEY \
  --query_prompt_path data/query_prompt.txt \
  --query_path data/val_expand_random.json \
  --department_path data/depart_info.json \
  --save_path result \
  --prerequisite_path prerequisities/result_hyun_j \
  --top_k 5 \
  --query_exp         # 쿼리 확장 사용
```

실행 후 `result/` 아래에 다음 파일들이 생성됩니다.

| 파일/폴더                      | 설명                               |
| -------------------------- | -------------------------------- |
| `result.log`               | INFO 로그 (후보 점수, 그래프 노드 수 등)      |
| `recommendations_*/*.svg`  | NetworkX → Graphviz 렌더링 결과       |
| `recommendations_*/*.json` | 노드·엣지 정보 (원본 / LLM‑선택 / refined) |

---

## 🧩 주요 컴포넌트 설명

### 1. DenseRetriever / classRetriever

| 기능                   | 설명                                     |
| -------------------- | -------------------------------------- |
| 인덱스 구축               | OpenAI Embedding → FAISS L2 인덱스 저장·재사용 |
| 검색 (`retrieve`)      | 쿼리 벡터와 top‑k 유사 학과/강좌 반환               |
| department diversity | 동일 학과 편중 방지를 위해 후처리                    |

### 2. `recursive_top1_selection()`

1. **학과별 top‑1 강좌 후보**를 가져와 스코어 내림차순 정렬
2. 최고 스코어 < **0.43** → 탐색 종료, 그래프 확장만 수행
3. 서로 다른 학과 2개까지 선택해 `already_selected_classes`에 추가
4. `build_prereq_postreq()`로 선수·후수 과목 그래프 확장
5. 아직 방문하지 않은 노드가 있으면 재귀 반복

### 3. 그래프 시각화

* **`visualize_and_sort_department_graphs`** – 학과별 부분 그래프 정렬·SVG 렌더
* **`selected_edge_by_llm`** – LLM이 엣지 중요도를 평가해 서브그래프 추출

---

## 🔑 주요 CLI 인자

| 인자               | 기본값     | 의미                    |
| ---------------- | ------- | --------------------- |
| `--query_exp`    | *False* | 확장 쿼리(LLM) 사용 여부      |
| `--department_y` | *False* | GT 학과 고정 vs. FAISS 검색 |
| `--top_k`        | 1       | 학과 검색 시 최근접 k         |


전체 인자 목록은 `python main.py -h` 로 확인하세요.

---

## 📝 로깅 & 디버깅 팁

* 모든 INFO 수준 메시지는 **result.log**에 기록됩니다.
* `recursive_top1_selection` 단계별 노드 수·최고 점수·선택 학과가 찍히므로, 임계값(0.43) 튜닝 시 참고하세요.
* DB 연결은 예외 발생 시 `finally: db_handler.close()` 패턴으로 감싸는 것을 권장합니다.

---

## 🔌 FastAPI Inference Service

### 구조 개요

```
main.py                # FastAPI 앱
└─ process_query()      # 한‧글 쿼리 → 추천 파이프라인 호출
```

| 단계 | 함수                    | 설명                                                                                  |
| -- | --------------------- | ----------------------------------------------------------------------------------- |
| 1  | **`/chat` POST**      | QueryRequest(질문, `required_dept_count`) 수신                                          |
| 2  | **`process_query()`** | • 쿼리 확장 → 임베딩<br>• 학과 선택 → TF‑IDF / GPT‑Emb / 그래프 기반 추천<br>• 결과 JSON + 그래프 + TXT 저장 |
| 3  | **재귀 탐색**             | `recursive_top1_selection()`로 선수·후수 연결 그래프 구축                                       |

### 주요 환경 변수 & 인자

| 이름               | 기본값  | 설명                          |
| ---------------- | ---- | --------------------------- |
| `OPENAI_API_KEY` | –    | OpenAI Embed & Chat 사용 토큰   |
| `PORT`           | 6006 | uvicorn 서비스 포트              |
| `db.json`        | –    | DB 접속 정보 (host, user, pwd…) |

### 실행 예시

```bash
export OPENAI_API_KEY="sk-..."
uvicorn main:app --host 0.0.0.0 --port 6006
```

#### 요청

```bash
curl -X POST http://localhost:6006/chat \
     -H "Content-Type: application/json" \
     -d '{"query":"데이터 사이언스 기반 스타트업 창업에 필요한 지식", "required_dept_count":30}'
```

#### 응답 예시 (JSON)

```json
{
  "meta_info": {
    "user_query": "데이터 사이언스 기반 스타트업 창업에 필요한 지식",
    "expanded_query": "...",
    "selected_departments": ["산업공학과", "경영학과"]
  },
  "recommended_courses": [
    {
      "class_id": "IE4010",
      "name": "데이터사이언스프로젝트",
      "department": "산업공학과",
      "score": 0.91
    },
    {
      "class_id": "BA3002",
      "name": "벤처창업론",
      "department": "경영학과",
      "score": 0.88
    }
  ]
}
```

#### 실시간 HTML 미리보기

`/chat/ui` 엔드포인트를 호출하면 추천 리스트가 브라우저에 바로 표 형태로 렌더링됩니다.

```bash
curl -X POST http://localhost:6006/chat/ui \
     -H "Content-Type: application/json" \
     -d '{"query":"데이터 사이언스 기반 스타트업 창업에 필요한 지식", "required_dept_count":30}'
```

(엔드포인트는 `<table>` + 부서 색상 칩으로 시각화된 HTML을 반환합니다.)
