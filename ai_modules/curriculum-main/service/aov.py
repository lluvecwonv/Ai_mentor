import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from collections import defaultdict
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import json
import logging
from util.utils import save_sorted_courses_as_json, save_merged_json
import seaborn as sns
from pathlib import Path
import base64
import io

logger = logging.getLogger(__name__)

# Font setup
HERE = Path(__file__).resolve().parent
FONT_PATH = HERE / "NanumGothic-Regular.ttf"
if FONT_PATH.exists():
    mpl.font_manager.fontManager.addfont(str(FONT_PATH))
    font_prop = fm.FontProperties(fname=str(FONT_PATH))
    mpl.rcParams['font.family'] = font_prop.get_name()
    mpl.rcParams['axes.unicode_minus'] = False
else:
    font_prop = None

def assign_positions(G):
    # 기본 학기 순서 (5학년까지 확장)
    base_semester_order = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2", "5-1", "5-2"]
    semester_dict = {semester: i for i, semester in enumerate(base_semester_order)}

    semester_nodes = defaultdict(list)

    # 1단계: 학기별로 노드 분류
    for node, data in G.nodes(data=True):
        student_grade = str(data.get("student_grade", "Unknown"))
        semester = str(data.get("semester", "Unknown"))
        key = f"{student_grade}-{semester}"

        if key in semester_dict:
            semester_nodes[key].append(node)
        else:
            # Unknown 노드는 마지막 학기에 배치
            if not semester_nodes:
                semester_nodes["1-1"].append(node)
            else:
                last_key = max(semester_nodes.keys(), key=lambda k: semester_dict.get(k, 0))
                semester_nodes[last_key].append(node)

    # 1.5단계: 6개 초과 시 과목을 재배치 (마지막 노드들을 다음 학년 같은 학기로 이동)
    MAX_COURSES_PER_SEMESTER = 6

    # 연결된 노드 찾기
    def get_connected_nodes(node_id):
        connected = set()
        for source, target in G.edges():
            if source == node_id:
                connected.add(target)
            if target == node_id:
                connected.add(source)
        return connected

    # 🔥 여러 번 반복하여 모든 학기가 7개 이하가 될 때까지 처리
    max_iterations = 10  # 무한 루프 방지
    for iteration in range(max_iterations):
        moved_any = False

        for key in sorted(semester_nodes.keys(), key=lambda k: semester_dict.get(k, 0)):  # 학기 순서대로
            nodes = semester_nodes[key]
            if len(nodes) > MAX_COURSES_PER_SEMESTER:
                # +1학년 이동 (예: 4-1 -> 5-1, 4-2 -> 5-2)
                grade, sem = key.split('-')
                next_grade = str(int(grade) + 1)
                next_key = f"{next_grade}-{sem}"

                # 연결되지 않은 노드 찾기
                unconnected_nodes = []
                connected_nodes = []

                for node in nodes:
                    connections = get_connected_nodes(node)
                    if len(connections) == 0:
                        unconnected_nodes.append(node)
                    else:
                        connected_nodes.append(node)

                # 7개를 초과하는 노드들을 마지막부터 다음 학년 같은 학기로 이동
                to_move = len(nodes) - MAX_COURSES_PER_SEMESTER
                # 우선순위: 연결되지 않은 노드 마지막부터
                moved_nodes = unconnected_nodes[-to_move:] if len(unconnected_nodes) >= to_move else unconnected_nodes + connected_nodes[-(to_move - len(unconnected_nodes)):]

                if moved_nodes:
                    # 다음 학기 그룹에 추가
                    if next_key not in semester_nodes:
                        semester_nodes[next_key] = []
                    semester_nodes[next_key].extend(moved_nodes)

                    # 원래 학기에서 제거
                    remaining = [n for n in nodes if n not in moved_nodes]
                    semester_nodes[key] = remaining

                    logger.info(f"📦 [반복{iteration+1}] {key}에서 {len(moved_nodes)}개 과목을 {next_key}로 이동")
                    moved_any = True

        # 더 이상 이동할 것이 없으면 종료
        if not moved_any:
            break

    # 2단계: 간단한 위치 배치 (학기별 x, 순서대로 y - 간격 조정)
    positions = {}

    for key, nodes in semester_nodes.items():
        x_pos = semester_dict.get(key, 0)
        num_nodes = len(nodes)

        # 노드들을 세로로 균등 배치 (간격을 1.5배로)
        y_start = -(num_nodes // 2) * 1.5
        for i, node in enumerate(nodes):
            y_pos = y_start + i * 1.5
            positions[node] = (x_pos, y_pos)

    # 3단계: 학기 라벨 생성 (실제 사용된 학기만) - 노드들의 맨 아래에 배치
    semester_labels = {}

    # 각 학기별로 해당 학기의 최소 y값 계산
    semester_min_y = {}
    for key, nodes in semester_nodes.items():
        if nodes:
            x_pos = semester_dict.get(key, 0)
            min_y_in_semester = min([positions[node][1] for node in nodes])
            semester_min_y[key] = min_y_in_semester

    for semester, x_pos in semester_dict.items():
        if semester in semester_nodes:  # 실제로 과목이 있는 학기만
            year, sem = semester.split('-')
            label_text = f"{year}학년 {sem}학기"
            # 해당 학기 노드들의 최소 y값 - 2 (노드 바로 아래)
            label_y = semester_min_y.get(semester, 0) - 2
            semester_labels[label_text] = (x_pos, label_y)

    logger.info(f"✅ 학기별 분포: {dict({k: len(v) for k, v in semester_nodes.items()})}")

    return positions, semester_labels

def visualize_graph_from_data(department_graphs, base_path, index, gt_department):
    # 기본 학기 순서 정의
    base_semester_order = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2", "5-1", "5-2"]

    font_name = None

    font_path = FONT_PATH

    if font_path.exists():
        font_prop = fm.FontProperties(fname=str(font_path))
        font_name = font_prop.get_name()
        plt.rcParams["font.family"] = font_name
        plt.rcParams["axes.unicode_minus"] = False
    else:
        font_prop = None
        font_name = None

    combined_graph = nx.DiGraph()
    node_department_map = {}

    unique_departments = set()
    for department, G in department_graphs.items():
        for node, node_data in G.nodes(data=True):
            unique_departments.add(node_data.get("department", "Unknown Department"))


    # 모던한 파스텔 컬러 팔레트
    modern_colors = [
        '#FF6B6B',  # 산호색 빨강
        '#4ECDC4',  # 청록색
        '#45B7D1',  # 하늘색
        '#FFA07A',  # 연한 주황
        '#98D8C8',  # 민트
        '#F7DC6F',  # 노란색
        '#BB8FCE',  # 보라색
        '#85C1E2',  # 파랑
    ]
    department_colors = {dept: modern_colors[i % len(modern_colors)] for i, dept in enumerate(unique_departments)}

    node_colors = []

    for department, G in department_graphs.items():
        for node, node_data in G.nodes(data=True):
            course_id = node
            course_name = node_data.get("class_name", "Unknown")
            student_grade = node_data.get("student_grade", "Unknown")
            semester = node_data.get("semester", "Unknown")
            node_department = node_data.get("department", "Unknown Department")  

            
            if not combined_graph.has_node(course_id):
                combined_graph.add_node(course_id,
                                        class_name=course_name,
                                        student_grade=student_grade,
                                        semester=semester)
                node_colors.append(department_colors.get(node_department, "gray")) 
                node_department_map[course_id] = node_department 
        for source, target in G.edges():
            combined_graph.add_edge(source, target)

    try:
        sorted_courses = list(nx.topological_sort(combined_graph))
    except nx.NetworkXUnfeasible:
        sorted_courses = []
            
    pos, semester_labels = assign_positions(combined_graph)


    # 🔥 그래프 크기를 더 크게, 여백 추가
    plt.figure(figsize=(24, 16), facecolor='white')
    ax = plt.gca()
    ax.set_facecolor('#F8F9FA')

    # 🔥 여백 설정 (노드가 잘리지 않도록)
    ax.margins(0.15)

    # 1) 엣지 먼저 그리기 (직선으로)
    nx.draw_networkx_edges(
        combined_graph, pos,
        edgelist=combined_graph.edges(),
        arrowstyle='-|>',
        arrowsize=25,
        width=2.5,
        edge_color='#90A4AE',
        alpha=0.6,
        connectionstyle='arc3,rad=0'  # 🔥 직선
    )

    # 2) 노드 그리기 (그림자 효과)
    nx.draw_networkx_nodes(
        combined_graph, pos,
        node_shape='o',
        node_size=5000,  # 🔥 조금 더 크게
        node_color=[department_colors[node_department_map[n]] for n in combined_graph.nodes()],
        edgecolors='white',
        linewidths=5,  # 🔥 테두리 더 두껍게
        alpha=0.95
    )

    # 3) 과목명: 노드 중앙에 (더 읽기 쉽게)
    name_labels = {n: combined_graph.nodes[n]['class_name'] for n in combined_graph.nodes()}
    nx.draw_networkx_labels(
        combined_graph, pos,
        labels=name_labels,
        font_size=13,  # 🔥 조금 작게 (긴 과목명 대응)
        font_weight='bold',
        font_family=font_name,
        font_color='#1A1A1A',
        verticalalignment='center',
        horizontalalignment='center'
    )

    # 범례
    legend_patches = [
        plt.Line2D([0], [0], marker='s', color='w',
                markerfacecolor=department_colors[d],
                markeredgecolor='black',
                markersize=12, label=d)
        for d in unique_departments
    ]
    plt.legend(handles=legend_patches, title="학과", loc="upper right",
               fontsize=12, title_fontsize=14, frameon=True, fancybox=True, shadow=True)

    # 제목: 학과 이름들 포함 (더 크게, 아래로 내림)
    department_list = list(unique_departments)[:2]  # 최대 2개 학과만
    department_names = "_".join(department_list)
    max_y_global = max([pos[1] for pos in pos.values()]) if pos else 0
    # 🔥 제목 크기 증가 (22 → 28), 위치 조정 (+5 → +3)
    plt.text(len(base_semester_order) / 2 - 0.5, max_y_global + 3,
             f"{department_names} 커리큘럼 추천 그래프",
             fontsize=28, fontweight='heavy', ha='center', va='bottom',
             fontfamily=font_name, color='black')  # 🔥 검은색, 더 진하게

    # 학기 라벨 추가 (노드들 아래)
    for label_text, label_pos in semester_labels.items():
        plt.text(label_pos[0], label_pos[1], label_text,
                fontsize=16, fontweight='bold', ha='center', va='top',
                fontfamily=font_name, color='#212121')

    plt.axis('off')
    # 🔥 tight_layout 제거 (margins와 충돌)
    # plt.tight_layout()

    # 파일로 저장
    save_path = os.path.join(base_path, f"{index}_{gt_department}_graph.png")
    # 🔥 pad_inches 추가로 여백 확보
    plt.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.3, facecolor='white')

    # Base64 인코딩
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', pad_inches=0.3, facecolor='white')
    buffer.seek(0)
    graph_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    plt.close()

    return f"data:image/png;base64,{graph_base64}"



def build_prereq_postreq(selected_list, db_handler, logger=None,
                         existing_visited_ids=None):

    if isinstance(selected_list, str):
        try:
            selected_list = json.loads(selected_list)  
        except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error: {e}")
            return {}
    

    if isinstance(selected_list, dict):
        if "result" in selected_list:
            courses = selected_list["result"]
        else:  
            courses = []
            for department, course_list in selected_list.items():
                if isinstance(course_list, list):
                    courses.extend(course_list)
                    
    elif isinstance(selected_list, list):
        courses = selected_list  
    else:
        print("⚠️ Unexpected data format:", selected_list)
        return {}
    
    selected_candidates = courses.copy()
    department_courses = defaultdict(list)

    for course in courses:
        if "department_name" in course:
            department_courses[course["department_name"]].append(course)
        
    department_graphs = {}
    class_list = []
    class_name_list = []
    department_list = []
    visited_nodes_total = set(existing_visited_ids) if existing_visited_ids is not None else set()
    logger.info(f"Visited nodes total: {len(visited_nodes_total)}")

    for department, courses in department_courses.items():
        # print(f"Building graph for {department} with {len(courses)} courses.")ㅊ
        G = nx.DiGraph()
       

        def add_course_recursive(course):
            class_id = course['class_id']
            class_name = course['class_name']
                    
            # if class_id in visited_nodes:
            #         return
            # visited_nodes.add(class_id)
            
            G.add_node(
                class_id,
                class_name=course.get('class_name', f"Unnamed Node {class_id}"),
                department=course.get('department_name', "Unknown Department"),
                semester=course.get('semester', "Unknown"),
                student_grade=course.get('student_grade', "Unknown"),
                curriculum=course.get('curriculum', "Unknown"),
                description=course.get('description', "Unknown"),
                prerequisites=course.get('prerequisite', "Unknown")
            )
            class_list.append(class_id)
            class_name_list.append(class_name)
            department_list.append(department)
            visited_nodes_total.add(class_id)
            logger.info(f'현재과목: {class_name}')

            if course.get("prerequisite"):
                prerequisites = db_handler.fetch_prerequisites(course['class_id'])
                logger.info(f'fetcehd prerequisites: {prerequisites}')
                for prereq in prerequisites:
                    prereq_id = prereq['class_id']
                    prereq_name = prereq['class_name']
                
                    # if prereq_id not in visited_nodes:
                    G.add_node(
                        prereq_id,
                        class_name=prereq.get('class_name', f"Unnamed Node {prereq_id}"),
                        department=prereq.get('department_name', "Unknown Department"),
                        semester=prereq.get('semester', "Unknown"),
                        student_grade=prereq.get('student_grade', "Unknown"),
                        curriculum=prereq.get('curriculum', "Unknown"),
                        description=prereq.get('description', "Unknown"),
                        prerequisites=prereq.get('prerequisites', "Unknown")
                    )
                    

                    G.add_edge(prereq_id, class_id)
                    # G.add_edge(class_id, prereq_id)
                    # visited_nodes.add(class_id)
                    
                    class_list.append(prereq_id)
                    class_name_list.append(prereq_name)
                    department_list.append(department)
                    visited_nodes_total.add(prereq_id)
                    logger.info(f'선행과목: {prereq_name}')
                    
                    
                    add_course_recursive(prereq)
                    
        for course in courses:
            add_course_recursive(course)

        department_graphs[department] = G 

    return department_graphs, visited_nodes_total



def visualize_and_sort_department_graphs(department_graphs, base_path="./graphs/", index=None, gt_department=None):
    """그래프 시각화 및 데이터 정렬 - PNG 이미지 반환"""

    os.makedirs(base_path, exist_ok=True)

    # PNG 그래프 이미지 생성
    graph_base64 = visualize_graph_from_data(department_graphs, base_path, index, gt_department)

    # 기존 JSON 데이터 생성 로직 유지
    merged_data = []
    all_departments_data = {}
    for department, G in department_graphs.items():
        try:
            sorted_courses = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            sorted_courses = []

        department_data = {
            "nodes": [],
            "edges": []
        }

        for node in G.nodes():
            node_data = G.nodes[node] if isinstance(G.nodes[node], dict) else {}
            course_id = node
            course_name = node_data.get("class_name", "Unknown")
            department = node_data.get("department", "Unknown Department")
            student_grade = node_data.get("student_grade", "Unknown")
            semester = node_data.get("semester", "Unknown")
            description = node_data.get("description", "Unknown")
            prerequisites = node_data.get("prerequisites", "Unknown")

              
            department_data["nodes"].append({
                "course_id": course_id,
                "course_name": course_name,
                "department": department,  
                "student_grade": student_grade,
                "semester": semester,
                "description": description,
                "prerequisites": prerequisites
            })
 
                
        for source, target in G.edges():
            department_data["edges"].append({
                "from": source,
                "to": target
            })
            
        all_departments_data[department] = department_data
        sorted_courses_data = save_sorted_courses_as_json(base_path, department, sorted_courses, G)
        merged_data.extend(sorted_courses_data)

    all_json_path = os.path.join(base_path, f"{index}_{gt_department}.json")
    with open(all_json_path, "w", encoding="utf-8") as f:
        json.dump(all_departments_data, f, indent=4, ensure_ascii=False)

    save_merged_json(merged_data, base_path, index, gt_department)

    # PNG base64 이미지 반환
    return all_departments_data, graph_base64 

