import logging
import os
from typing import Dict, Any, List, Optional
import networkx as nx

from service.open_ai import query_expansion
from service.aov import build_prereq_postreq, visualize_and_sort_department_graphs
from util.dbClient import DbClient
from service.search import DepartmentRetriever, ClassRetriever
from service.curricum_recursive import recursive_top1_selection

logger = logging.getLogger(__name__)


class CurriculumService:
    """커리큘럼 추천 서비스 - 간소화된 버전 (FAISS 서비스 활용)"""

    def __init__(self, db_client: DbClient):
        """서비스 초기화"""
        self.db_client = db_client
        self.department_retriever = DepartmentRetriever(db_client)  # 학과 검색 서비스
        self.class_retriever = ClassRetriever(db_client)  # 과목 검색 서비스

    def process_query(self, query: str, required_dept_count: int = 30) -> Dict[str, Any]:
        """쿼리 처리 - recursive_top1_selection 기반"""
        logger.info(f"쿼리 처리: {query}...")

        try:
            # 1. 쿼리 확장
            query_info = query_expansion(None, query, "service/prompt/query_exp_once.txt")

            # 2. 학과 검색
            dept_results = self.department_retriever.search_department(query_info, count=required_dept_count)
            
            # 3. recursive_top1_selection으로 과목 선택 (전체 최대 30과목)
            # already_selected_classes를 초기화하고 추적
            already_selected_classes = []
            graph_visited_ids = set()

            department_graphs = recursive_top1_selection(
                client=None,
                db_handler=self.db_client,
                query=query_info,
                selected_dept_list=dept_results,
                class_retriever=self.class_retriever,
                graph_path="result",
                gt_department=None,
                already_selected_classes=already_selected_classes,
                graph_visited_ids=graph_visited_ids,
                max_total_courses=30,
                depth=0
            )

            # 4. department_graphs는 dict of DiGraph
            # {"학과1": DiGraph, "학과2": DiGraph, ...}
            # 만약 빈 dict이거나 그래프가 없으면 기본 구조 생성
            if not department_graphs or not isinstance(department_graphs, dict):
                logger.warning("⚠️ department_graphs가 비어있거나 잘못된 형식입니다.")
                department_graphs = {"통합커리큘럼": nx.DiGraph()}

            # 5. 그래프 시각화
            all_results_json, graph_base64 = visualize_and_sort_department_graphs(
                department_graphs, "result", 0, "result_department_top1"
            )

            logger.info(f"✅ 이미지 생성 완료 - base64 길이: {len(graph_base64) if graph_base64 else 0}자")

            # 선택된 과목 리스트를 JSON 포맷으로 변환
            recommended_courses = []
            for course in already_selected_classes:
                recommended_courses.append({
                    "class_id": course.get("class_id"),
                    "name": course.get("class_name"),
                    "department": course.get("department_name"),
                    "score": round(course.get("score", 0.0), 2),
                    "student_grade": course.get("student_grade"),
                    "semester": course.get("semester"),
                    "description": course.get("description", "")
                })

            return {
                "expanded_query": query_info,
                "all_results_json": all_results_json,
                "graph": graph_base64,
                "selected_departments": [d.get("department_name") for d in dept_results] if dept_results else [],
                "recommended_courses": recommended_courses
            }

        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}")
            raise
