import logging
import os
from typing import Dict, Any, List, Optional

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
            
            # 3. recursive_top1_selection으로 과목 선택
            graph = recursive_top1_selection(
                client=None,  # 필요시 db_client 전달
                db_handler=self.db_client,
                query=query_info,
                selected_dept_list=dept_results,
                class_retriever=self.class_retriever,
                graph_path="result",
                gt_department=None,
                already_selected_classes=None,
                graph_visited_ids=None,
                depth=0
            )
            
            # 5. 그래프 시각화
            all_results_json, graph_base64 = visualize_and_sort_department_graphs(
                graph, "result", 0, "result_department_top1"
            )

            logger.info(f"처리 완료: {len(dept_results)}개 학과")

            return {
                "expanded_query": query_info,
                "all_results_json": all_results_json,
                "graph": graph_base64
            }

        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}")
            raise
