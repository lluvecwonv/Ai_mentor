import uvicorn
from fastapi import FastAPI
import random
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,HTMLResponse
from types import SimpleNamespace
from contextlib import asynccontextmanager
from pydantic import BaseModel

from dotenv import load_dotenv
import os
from open_ai import initialize_openai_client, query_expansion
from aov import build_prereq_postreq, visualize_and_sort_department_graphs
from dense_retriver import DenseRetriever, classRetriever
from utils import update_json_with_index, read_json
from db.db_search import DatabaseHandler
from pathlib import Path
import logging
import time
from debug_utils import (
    CurriculumDebugger,
    performance_monitor,
    validate_query_data,
    validate_retrieval_result
)

# 전역 변수 (FastAPI startup 이벤트에서 초기화)
global_args = None
client = None
db_handler = None
debugger = None

HERE        = Path(__file__).resolve().parent
DATA_DIR    = HERE / "data"
PROMPT_DIR  = HERE / "prompt"
RESULT_DIR  = HERE / "result"
CHATBOT_DIR = HERE / "chatbot_result"

load_dotenv()  # .env 파일 자동 로드

db_host = os.getenv("DB_HOST")
db_password = os.getenv("DB_PASSWORD")
openai_api_key = os.getenv("OPENAI_API_KEY")

# 로그를 파일에 저장
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='result.log',  # 로그를 파일에 저장
    filemode='w'  # 'w': 덮어쓰기, 'a': 이어쓰기
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# � Seed 고정 (일관된 결과 보장)
def set_seed(seed=42):
    np.random.seed(seed)
    random.seed(seed)

set_seed()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_args, client, db_handler, debugger

    # 디버거 초기화
    debugger = CurriculumDebugger(log_level="INFO", enable_console=True, enable_file=True)
    debugger.logger.info("🚀 Curriculum 서비스 초기화 시작")
    
    CHATBOT_DIR.mkdir(exist_ok=True)
    RESULT_DIR .mkdir(exist_ok=True)
    # 설정값을 argparse 대신 SimpleNamespace로 설정 (실제 환경에 맞게 수정)
    global_args = SimpleNamespace(
        openai_api_key   = openai_api_key,
        query_prompt_path= str(PROMPT_DIR / "query_exp_once.txt"),
        department_path  = str(DATA_DIR   / "depart_info.json"),
        save_path        = str(RESULT_DIR),
        save_path_txt    = str(CHATBOT_DIR),
        goal_index_path  = str(RESULT_DIR / "goal_Dataset.pkl"),
        class_index_path = str(RESULT_DIR / "class_Dataset.pkl"),
        top_k=1,
        reranker=False,
        query_exp=False,
        department_y=False,
    )
    
    # DB 설정 및 연결
    debugger.logger.info("🔗 OpenAI 클라이언트 초기화 중...")
    client = initialize_openai_client(global_args.openai_api_key)
    debugger.logger.info("✅ OpenAI 클라이언트 초기화 완료")

    debugger.logger.info("🗄️ 데이터베이스 연결 중...")
    db_handler = DatabaseHandler(
        host=db_host,
        port=3311,
        user="root",
        password=db_password,
        database="nll",
        charset="utf8mb4"
    )
    db_handler.connect()
    debugger.logger.info("✅ 데이터베이스 연결 완료")

    debugger.logger.info("🎯 FastAPI Startup: 모든 초기화 완료")

    yield

    debugger.logger.info("🛑 서비스 종료 중...")
    db_handler.close()
    debugger.logger.info("✅ 데이터베이스 연결 종료 완료")

app = FastAPI(title="Curriculum Recommendation API", lifespan=lifespan)

# CORS for browser/ proxy preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def recursive_top1_selection(client, db_handler, query_embedding, query, selected_dept_list,  
                             class_retriever, graph_path, required_dept_count, gt_department, 
                             already_selected_classes=None, depth=0):

    # 🔥 이미 선택된 과목 리스트가 None이면 빈 리스트로 초기화
    if already_selected_classes is None or not isinstance(already_selected_classes, list):
        already_selected_classes = []
    
    # 🔥 방문한 노드 개수 확인
    visited_ids = {c.get("class_id") for c in already_selected_classes}
    visited_count = len(visited_ids)

    logger.info(f"현재 방문한 노드 개수: {visited_count}")

    # ✅ 종료 조건 체크
    if visited_count >= required_dept_count:
        print(f'current depth: {depth}')
        logger.info(f"종료 조건 도달: 선택된 후보 {visited_count}개 (목표: {required_dept_count})")
        
        # 🔥 최종 그래프 생성 (이미 방문한 노드만 포함)
        G, visited_ids = build_prereq_postreq(class_retriever, already_selected_classes, db_handler, 
                                              query_embedding, logger=logger, existing_visited_ids=visited_ids)
        return G

    # ✅ 후보 검색
    candidate_dict = class_retriever.retrieve_by_department(query_embedding, selected_dept_list, top_k=1, visited_class_ids=visited_ids)
    logger.info(f"Candidate dict retrieved: {candidate_dict}")
    print("DEBUG ▶ candidate_dict:", candidate_dict)

    candidate_list = []
    for dept_name, dept_results in candidate_dict.items():
        if isinstance(dept_results, list) and dept_results:
            candidate_list.extend(dept_results)

    # ✅ 만약 후보가 없다면 종료
    if not candidate_list:
        logger.info("후보 없음. 재귀 종료.")
        G, visited_ids = build_prereq_postreq(class_retriever, already_selected_classes, db_handler, 
                                              query_embedding, logger=logger, existing_visited_ids=visited_ids)
        return G

    # ✅ 가장 점수가 높은 과목 선택 (여러 개 고려)
    candidate_list = sorted(candidate_list, key=lambda x: x["score"], reverse=True)

    # ✅ 여러 학과에서 균형 있게 후보 선택
    selected_candidates = []
    seen_departments = set()

    for candidate in candidate_list:
        if candidate["department_name"] not in seen_departments:
            selected_candidates.append(candidate)
            seen_departments.add(candidate["department_name"])

        # ✅ 예: 최대 2개의 학과에서 선택
        if len(selected_candidates) >= 2:
            break

    print(f"🔹 선택된 후보들: {selected_candidates}")

    # ✅ 선택된 강의들을 추가
    for candidate in selected_candidates:
        logger.info(f"candidate: {candidate}")
        candidate_id = candidate.get("class_id")

        if candidate_id in visited_ids:
            logger.info(f"Candidate {candidate_id} 이미 선택됨. 건너뜀.")
            continue

        already_selected_classes.append(candidate)
        logger.info(f"후보 추가: {candidate_id} (총 {len(already_selected_classes)}개)")
        logger.info(f'alreay_selected_classes: {already_selected_classes}')

    # 🔥 **매번 그래프 업데이트**
    G, visited_ids = build_prereq_postreq(class_retriever, already_selected_classes, db_handler, query_embedding, logger=logger, existing_visited_ids=visited_ids)

    # ✅ 재귀 호출 (리스트 유지)
    return recursive_top1_selection(client, db_handler, query_embedding, query, 
                                    selected_dept_list, class_retriever, graph_path, required_dept_count, gt_department,
                                    already_selected_classes, depth+1)

query_counter = 0

@performance_monitor("full_query_processing")
def process_query(query, args, client, db_handler, idx=0):
    global query_counter, debugger
    query_counter += 1  # 쿼리 요청마다 카운터 증가

    # 쿼리 시작 로깅
    debugger.log_query_start(query, query_counter)

    # 입력 데이터 검증
    validation_issues = validate_query_data(query, getattr(args, 'required_dept_count', 30))
    if validation_issues:
        debugger.log_data_validation("입력 쿼리", query, validation_issues)
        # 경고만 하고 계속 진행
    else:
        debugger.log_data_validation("입력 쿼리", query, [])

    # 1) 학과·강좌 인덱스 준비
    debugger.logger.info("📚 학과·강좌 인덱스 임베딩 시작")
    dept_retriever = DenseRetriever(client, args)
    dept_retriever.doc_embedding()
    class_retriever = classRetriever(client, args)
    class_retriever.doc_embedding()
    debugger.logger.info("✅ 강의·학과 인덱스 임베딩 완료")

    # 2) 쿼리 확장 & 임베딩
    original_query = query
    debugger.logger.info("🔄 쿼리 확장 시작")
    query_info = query_expansion(client, query, args.query_prompt_path)
    debugger.log_query_expansion(original_query, query_info)

    debugger.logger.info("🧠 쿼리 임베딩 생성 중")
    query_embedding = dept_retriever.query_embedding(query_info)
    debugger.logger.info("✅ 쿼리 임베딩 생성 완료")

    # 3) 관련 학과 top-k
    try:
        debugger.logger.info("🏫 관련 학과 검색 시작")
        selected_depart_list = dept_retriever.retrieve(query_embedding)

        # 검색 결과 검증
        dept_issues = validate_retrieval_result(selected_depart_list, "department")
        debugger.log_data_validation("학과 검색 결과", selected_depart_list, dept_issues)

        debugger.log_department_selection(selected_depart_list)
    except Exception as e:
        debugger.log_error(e, "학과 검색")
        raise

    # 4) 시각화 저장 경로 설정 (args.save_path_txt 기반)
    graph_dir  = args.save_path_txt
    graph_name = f"recommendations_query{'_exp' if args.query_exp else '_no_exp'}_similar_top{args.top_k}"
    graph_path = os.path.join(graph_dir, graph_name)
    os.makedirs(graph_path, exist_ok=True)
    gt_department = "result_department_top1"
    logger.info(f"그래프 저장 경로: {graph_path}")

    # 5) 재귀적으로 후보 클래스 선택 후 전제/후제 그래프 생성
    debugger.logger.info("🔄 재귀적 강의 선택 및 그래프 생성 시작")
    start_time = time.time()

    G = recursive_top1_selection(
        client,
        db_handler,
        query_embedding,
        query,
        selected_depart_list,
        class_retriever,
        graph_path,
        required_dept_count=args.required_dept_count,
        gt_department=gt_department
    )

    graph_time = time.time() - start_time
    debugger.log_performance("그래프 생성", graph_time)

    # 6) 그래프 시각화 및 정렬
    debugger.logger.info("🎨 그래프 시각화 및 정렬 시작")
    start_time = time.time()

    all_results_json = visualize_and_sort_department_graphs(G, graph_path, idx, gt_department)

    viz_time = time.time() - start_time
    debugger.log_performance("시각화 및 정렬", viz_time)

    # 7) 최종 추천 강좌 목록으로 변환
    flat_nodes = []
    for dept_name, dept_data in all_results_json.items():
        # dept_data는 {"nodes": [...], "edges": [...]}
        flat_nodes.extend(dept_data.get("nodes", []))

    recommended = [
        {
            "class_id": node["course_id"],      # all_results_json uses "course_id"
            "name":     node["course_name"],
            "department": node["department"],
            "score":    node.get("score", None)  # score는 없을 수도 있으니 get()
        }
        for node in flat_nodes
    ]

    # 최종 결과 로깅
    total_time = time.time() - start_time if 'start_time' in locals() else 0
    debugger.log_final_result(all_results_json, total_time)

    return {
        "expanded_query": query_info,
        "all_results_json": all_results_json
    }

class QueryRequest(BaseModel):
    query: str
    required_dept_count: int = 30  # 기본값 30, 클라이언트에서 원하는 값을 전달할 수 있음


@app.get("/chat")
def chat_get():
    return {"message": "이 엔드포인트는 POST 방식으로 쿼리를 처리합니다. POST 요청을 보내세요."}

@app.post("/chat")
def process_query_endpoint(request: QueryRequest):
    global global_args, client, db_handler, debugger

    try:
        debugger.logger.info(f"📨 API 요청 수신: '{request.query[:100]}{'...' if len(request.query) > 100 else ''}' (요구 과목 수: {request.required_dept_count})")

        global_args.required_dept_count = request.required_dept_count
        result = process_query(request.query, global_args, client, db_handler)
        # ── 여기서 언패킹 ──
        expanded = result["expanded_query"]
        all_json = result["all_results_json"]
        
        lines = [f"{expanded}\n"]

        # 🎓 all_results_json 풀어서
        for dept_name, dept_data in all_json.items():
            lines.append(f"=== {dept_name} ===")
            for node in dept_data.get("nodes", []):
                # 원하는 필드만 뽑아서, 중괄호 없이
                course = node.get("course_name", "")
                grade  = node.get("student_grade", "")
                sem    = node.get("semester", "")
                prereq = node.get("prerequisites", "")
                lines.append(
                    f"강좌명: {course}\n"
                    f"{grade}학년 {sem}학기\n"
                    f"선수과목: {prereq}"
                )
            lines.append("")  # 한 과목군 끝나고 빈 줄

    
        message_text = "\n".join(lines).strip()

        debugger.logger.info(f"✅ API 응답 완료: {len(message_text)}자 응답 생성")

        return JSONResponse(
            status_code=200,
            content={"message": message_text}
        )

    except Exception as e:
        debugger.log_error(e, "API 요청 처리")
        return JSONResponse(
            status_code=500,
            content={"message": {"error": str(e)}}
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7996)