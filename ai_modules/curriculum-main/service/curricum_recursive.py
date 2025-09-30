
import logging
from service.aov import build_prereq_postreq

logger = logging.getLogger(__name__)

def recursive_top1_selection(client, db_handler, query, selected_dept_list,
                            class_retriever, graph_path, gt_department,
                            already_selected_classes=None, graph_visited_ids=None,
                            max_total_courses=30, depth=0):
    """재귀적으로 과목을 선택하는 함수 (전체 최대 30과목)"""

    # Initialize parameters
    if already_selected_classes is None or not isinstance(already_selected_classes, list):
        already_selected_classes = []

    if graph_visited_ids is None or not isinstance(graph_visited_ids, set):
        graph_visited_ids = set()

    # 종료 조건 1: 전체 과목 수가 30개 이상이면 종료
    if len(already_selected_classes) >= max_total_courses:
        logger.info(f"✅ 전체 과목 수 {len(already_selected_classes)}개 달성. 검색 종료.")
        G, _ = build_prereq_postreq(already_selected_classes, db_handler,
                                    logger=logger, existing_visited_ids=graph_visited_ids)
        logger.info(f"최종 선택된 과목 수: {len(already_selected_classes)}")
        return G

    # Track visited nodes (안전하게 처리)
    visited_ids = set()
    for c in already_selected_classes:
        if isinstance(c, dict):
            class_id = c.get("class_id")
            if class_id is not None:
                visited_ids.add(class_id)
        elif isinstance(c, (int, str)):
            visited_ids.add(c)
    graph_visited_ids.update(visited_ids)

    # 모든 학과에서 검색 (제한 없음)
    candidate_dict = class_retriever.search_class_by_departments(
        query, selected_dept_list, exclude_class_ids=list(visited_ids)
    )

    candidate_list = []
    for dept_name, dept_results in candidate_dict.items():
        if isinstance(dept_results, list) and dept_results:
            candidate_list.extend(dept_results)

    # 종료 조건 2: 후보가 없으면 종료
    if not candidate_list:
        logger.info("더 이상 후보 과목이 없음. 검색 종료.")
        G, _ = build_prereq_postreq(already_selected_classes, db_handler,
                                    logger=logger, existing_visited_ids=graph_visited_ids)
        logger.info(f"최종 선택된 과목 수: {len(already_selected_classes)}")
        return G

    # Sort by score descending
    candidate_list = sorted(candidate_list, key=lambda x: x["score"], reverse=True)

    # 다양한 학과에서 최대 2개 선택
    selected_candidates = []
    seen_departments = set()

    for candidate in candidate_list:
        dept_name = candidate["department_name"]

        if dept_name not in seen_departments:
            selected_candidates.append(candidate)
            seen_departments.add(dept_name)

        if len(selected_candidates) >= 2:
            break

    # Add selected candidates
    for candidate in selected_candidates:
        candidate_id = candidate.get("class_id")
        dept_name = candidate["department_name"]

        if candidate_id in visited_ids:
            logger.info(f"Candidate {candidate_id} already selected. Skipping.")
            continue

        already_selected_classes.append(candidate)

        logger.info(f"✅ 선택: {candidate_id} ({dept_name}) - "
                   f"전체 {len(already_selected_classes)}/{max_total_courses}과목 | "
                   f"점수: {candidate.get('score', 0):.3f}")

    # Update graph
    G, new_visited = build_prereq_postreq(already_selected_classes, db_handler,
                                          logger=logger, existing_visited_ids=graph_visited_ids)
    graph_visited_ids.update(new_visited)

    # Recursive call
    return recursive_top1_selection(
        client, db_handler, query, selected_dept_list,
        class_retriever, graph_path, gt_department,
        already_selected_classes, graph_visited_ids,
        max_total_courses, depth + 1
    )