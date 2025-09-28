import logging
import os
from typing import Dict, Any, List, Optional

from open_ai import initialize_openai_client, query_expansion
from aov import build_prereq_postreq, visualize_and_sort_department_graphs
from dense_retriver import DenseRetriever, classRetriever
from util.dbClient import DbClient

logger = logging.getLogger(__name__)


class CurriculumService:
    """커리큘럼 추천 서비스 - 비즈니스 로직"""

    def __init__(self, db_client: DbClient):
        """서비스 초기화"""
        self.db_client = db_client
        self.openai_client = None
        self._initialize_openai()

    def _initialize_openai(self):
        """OpenAI 클라이언트 초기화"""
        try:
            self.openai_client = initialize_openai_client(os.getenv("OPENAI_API_KEY"))
            logger.info("✅ OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
            raise

    def process_query(self, query: str, required_dept_count: int = 30) -> Dict[str, Any]:
        """쿼리 처리 - 메인 비즈니스 로직"""
        logger.info(f"쿼리 처리 시작: {query[:50]}...")

        try:
            # 1. 인덱스 준비
            dept_retriever, class_retriever = self._prepare_retrievers()

            # 2. 쿼리 확장 및 임베딩
            query_info = query_expansion(self.openai_client, query, "prompt/query_exp_once.txt")
            query_embedding = dept_retriever.query_embedding(query_info)

            # 3. 학과 검색
            selected_dept_list = dept_retriever.retrieve(query_embedding)

            # 4. 재귀적 과목 선택
            graph = self._recursive_selection(
                query_embedding, selected_dept_list, class_retriever, required_dept_count
            )

            # 5. 결과 생성 (그래프 Base64 포함)
            all_results_json, graph_base64 = visualize_and_sort_department_graphs(
                graph, "result", 0, "result_department_top1"
            )

            logger.info(f"✅ 쿼리 처리 완료: {len(all_results_json)}개 학과 결과")

            return {
                "expanded_query": query_info,
                "all_results_json": all_results_json,
                "graph": graph_base64
            }

        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패: {e}")
            raise

    def _prepare_retrievers(self) -> tuple:
        """Retriever 준비"""
        logger.info("📚 Retriever 초기화 시작")

        dept_retriever = DenseRetriever(self.openai_client, None)
        dept_retriever.doc_embedding()

        class_retriever = classRetriever(self.openai_client, None)
        class_retriever.doc_embedding()

        logger.info("✅ Retriever 초기화 완료")
        return dept_retriever, class_retriever

    def _recursive_selection(self, query_embedding, selected_dept_list, class_retriever,
                           required_dept_count: int, already_selected_classes: Optional[List] = None):
        """재귀적 과목 선택"""
        if already_selected_classes is None:
            already_selected_classes = []

        visited_ids = {c.get("class_id") for c in already_selected_classes}

        # 종료 조건
        if len(visited_ids) >= required_dept_count:
            graph, _ = build_prereq_postreq(
                class_retriever, already_selected_classes, self.db_client,
                query_embedding, logger=logger, existing_visited_ids=visited_ids
            )
            return graph

        # 후보 검색
        candidate_dict = class_retriever.retrieve_by_department(
            query_embedding, selected_dept_list, top_k=1, visited_class_ids=visited_ids
        )

        candidate_list = []
        for dept_results in candidate_dict.values():
            if isinstance(dept_results, list):
                candidate_list.extend(dept_results)

        if not candidate_list:
            graph, _ = build_prereq_postreq(
                class_retriever, already_selected_classes, self.db_client,
                query_embedding, logger=logger, existing_visited_ids=visited_ids
            )
            return graph

        # 상위 후보 선택
        candidate_list = sorted(candidate_list, key=lambda x: x["score"], reverse=True)
        selected_candidates = []
        seen_departments = set()

        for candidate in candidate_list:
            dept_name = candidate["department_name"]
            if dept_name not in seen_departments and len(selected_candidates) < 2:
                selected_candidates.append(candidate)
                seen_departments.add(dept_name)

        # 후보 추가
        for candidate in selected_candidates:
            if candidate.get("class_id") not in visited_ids:
                already_selected_classes.append(candidate)

        # 그래프 업데이트 후 재귀 호출
        graph, visited_ids = build_prereq_postreq(
            class_retriever, already_selected_classes, self.db_client,
            query_embedding, logger=logger, existing_visited_ids=visited_ids
        )

        return self._recursive_selection(
            query_embedding, selected_dept_list, class_retriever,
            required_dept_count, already_selected_classes
        )

    def format_response(self, result: Dict[str, Any]) -> str:
        """응답 포맷팅"""
        lines = [f"{result['expanded_query']}\n"]

        for dept_name, dept_data in result["all_results_json"].items():
            lines.append(f"=== {dept_name} ===")
            for node in dept_data.get("nodes", []):
                lines.append(
                    f"강좌명: {node.get('course_name', '')}\n"
                    f"{node.get('student_grade', '')}학년 {node.get('semester', '')}학기\n"
                    f"선수과목: {node.get('prerequisites', '')}"
                )
            lines.append("")

        return "\n".join(lines).strip()