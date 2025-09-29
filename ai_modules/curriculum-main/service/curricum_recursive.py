
import logging
from service.aov import build_prereq_postreq

logger = logging.getLogger(__name__)


def recursive_top1_selection(client, db_handler, query, selected_dept_list,
                            class_retriever, graph_path, gt_department,
                            already_selected_classes=None, graph_visited_ids=None, depth=0):
    """재귀적으로 과목을 선택하는 함수"""
    
    # Initialize already_selected_classes if None or invalid
    if already_selected_classes is None or not isinstance(already_selected_classes, list):
        already_selected_classes = []
        
    if graph_visited_ids is None or not isinstance(graph_visited_ids, set):
        graph_visited_ids = set()
    
    # Track visited nodes
    visited_ids = {c.get("class_id") for c in already_selected_classes}
    graph_visited_ids.update(visited_ids)

    # Retrieve candidate courses using search_class_by_departments
    candidate_dict = class_retriever.search_class_by_departments(query, selected_dept_list, exclude_class_ids=list(visited_ids))

    candidate_list = []
    for dept_name, dept_results in candidate_dict.items():
        if isinstance(dept_results, list) and dept_results:
            candidate_list.extend(dept_results)

    # If no candidates found
    if not candidate_list:
        logger.info("No candidates found. Ending search.")
        G, visited_ids = build_prereq_postreq(already_selected_classes, db_handler, logger=logger, existing_visited_ids=graph_visited_ids)
        graph_visited_ids.update(visited_ids)
        logger.info(f"Final number of visited nodes: {len(visited_ids)}")
        return G

    # Sort by score descending
    candidate_list = sorted(candidate_list, key=lambda x: x["score"], reverse=True)

    # Select candidates from diverse departments
    selected_candidates = []
    seen_departments = set()

    for candidate in candidate_list:
        if candidate["department_name"] not in seen_departments:
            selected_candidates.append(candidate)
            seen_departments.add(candidate["department_name"])
        if len(selected_candidates) >= 2:
            break

    # Add selected candidates
    for candidate in selected_candidates:
        logger.info(f"candidate: {candidate}")
        candidate_id = candidate.get("class_id")

        if candidate_id in visited_ids:
            logger.info(f"Candidate {candidate_id} already selected. Skipping.")
            continue

        already_selected_classes.append(candidate)

    # Update graph
    G, graph_visited_ids = build_prereq_postreq(already_selected_classes, db_handler, logger=logger, existing_visited_ids=graph_visited_ids)
    graph_visited_ids.update(visited_ids)
    
    # Recursive call
    return recursive_top1_selection(
        client, db_handler, query,
        selected_dept_list, class_retriever, graph_path, gt_department,
        already_selected_classes, graph_visited_ids, depth+1
    )