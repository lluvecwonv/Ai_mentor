# curriculumService.py
import os, sys, json
from typing import Any, List

# 1) curriculumplan 경로를 파이썬 import 경로에 추가
THIS_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(THIS_DIR, "curriculumplan"))

# 2) curriculumplan 내부 모듈 import
from db.db_search import DatabaseHandler
from dataset.dataset import goalDatasetjson, class_depart_Dataset
from dense_retriver import DenseRetriever, classRetriever
from reranker import ReRanker
from aov import build_prereq_postreq
from open_ai import initialize_openai_client
from utils import read_json

class CurriculumService:
    def __init__(self, openai_api_key: str, db_config_path: str):
        # OpenAI 클라이언트 초기화
        self.client = initialize_openai_client(openai_api_key)

        # DB 핸들러 초기화 & 연결
        db_cfg = read_json(db_config_path)
        self.db = DatabaseHandler(**db_cfg)
        self.db.connect()

        # 1) 학과 임베딩 준비
        depart_path = os.path.join(THIS_DIR, "curriculumplan", "data", "depart_info.json")
        depart_data = json.load(open(depart_path, "r", encoding="utf-8"))
        depart_dataset = goalDatasetjson(depart_data)
        self.retriever = DenseRetriever(self.client, None, depart_dataset)
        self.retriever.doc_embedding()

        # 2) 수업 임베딩 준비
        class_info = self.db.fetch_classes_info_by_department()
        class_dataset = class_depart_Dataset(class_info)
        self.class_retriever = classRetriever(self.client, None, class_dataset)
        self.class_retriever.doc_embedding()

    def generate(self, goal: str, level: str, top_k: int = 5) -> List[Any]:
        """
        goal: 사용자 목표 (예: "AI 전문가")
        level: 초급/중급/고급
        top_k: 부서별 상위 k개 추천
        """
        # 1) 목표 → 임베딩
        query_emb = self.retriever.query_embedding(goal)

        # 2) 유사 학과 추출
        selected_depts = self.retriever.retrieve(query_emb)

        # 3) 그래프 기반 강좌 탐색 (전수요/후수요)
        G = build_prereq_postreq(self.class_retriever, [], self.db, query_emb)

        # 4) 랭커로 재순위 (예시: 상위 top_k개만)
        #    재순위 로직이 필요하면 ReRanker 활용하세요.

        # 5) 결과 추출
        curriculum = []
        for node_id, data in G.nodes(data=True):
            curriculum.append({
                "class_id": node_id,
                **data
            })

        # 6) 필요하면 top_k로 자르기
        return curriculum[:top_k]
