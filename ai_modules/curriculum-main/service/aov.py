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
    # 기본 학기 순서
    base_semester_order = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"]
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

    # 1.5단계: 7개 이상인 학기의 과목을 재배치
    MAX_COURSES_PER_SEMESTER = 7

    # 연결된 노드 찾기
    def get_connected_nodes(node_id):
        connected = set()
        for source, target in G.edges():
            if source == node_id:
                connected.add(target)
            if target == node_id:
                connected.add(source)
        return connected

    for key in list(semester_nodes.keys()):
        nodes = semester_nodes[key]
        if len(nodes) > MAX_COURSES_PER_SEMESTER:
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

            # 7개를 초과하는 연결되지 않은 노드를 다음 학년으로 이동
            to_move = len(nodes) - MAX_COURSES_PER_SEMESTER
            moved_nodes = unconnected_nodes[:to_move]

            if moved_nodes:
                # 다음 학기 그룹에 추가
                if next_key not in semester_nodes:
                    semester_nodes[next_key] = []
                semester_nodes[next_key].extend(moved_nodes)

                # 원래 학기에서 제거
                semester_nodes[key] = connected_nodes + unconnected_nodes[to_move:]

                logger.info(f"📦 {key}에서 {len(moved_nodes)}개 과목을 {next_key}로 이동")

    # 2단계: 간단한 위치 배치 (학기별 x, 순서대로 y)
    positions = {}

    for key, nodes in semester_nodes.items():
        x_pos = semester_dict.get(key, 0)
        num_nodes = len(nodes)

        # 노드들을 세로로 균등 배치
        y_start = -(num_nodes // 2)
        for i, node in enumerate(nodes):
            y_pos = y_start + i
            positions[node] = (x_pos, y_pos)

    # 3단계: 학기 라벨 생성 (실제 사용된 학기만)
    semester_labels = {}
    max_y = max([pos[1] for pos in positions.values()]) if positions else 0
    label_y = max_y + 3  # 노드들 위쪽에 배치

    for semester, x_pos in semester_dict.items():
        if semester in semester_nodes:  # 실제로 과목이 있는 학기만
            year, sem = semester.split('-')
            label_text = f"{year}학년 {sem}학기"
            semester_labels[label_text] = (x_pos, label_y)

    logger.info(f"✅ 학기별 분포: {dict({k: len(v) for k, v in semester_nodes.items()})}")

    return positions, semester_labels

def visualize_graph_from_data(department_graphs, base_path, index, gt_department):
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


    plt.figure(figsize=(20, 14), facecolor='white')
    ax = plt.gca()
    ax.set_facecolor('#FAFAFA')

    # 1) 엣지 먼저 그리기 (반듯한 선)
    nx.draw_networkx_edges(
        combined_graph, pos,
        edgelist=combined_graph.edges(),
        arrowstyle='-|>',
        arrowsize=20,
        width=3,
        edge_color='#BDBDBD',
        alpha=0.8,
        connectionstyle='arc3,rad=0'  # 반듯한 직선
    )

    # 2) 노드 그리기
    nx.draw_networkx_nodes(
        combined_graph, pos,
        node_shape='o',
        node_size=4000,
        node_color=[department_colors[node_department_map[n]] for n in combined_graph.nodes()],
        edgecolors='white',
        linewidths=4
    )

    # 3) 과목명: 노드 중앙에 (흰색 텍스트로 대비)
    name_labels = {n: combined_graph.nodes[n]['class_name'] for n in combined_graph.nodes()}
    nx.draw_networkx_labels(
        combined_graph, pos,
        labels=name_labels,
        font_size=11,
        font_weight='bold',
        font_family=font_name,
        font_color='white',
        verticalalignment='center',
        horizontalalignment='center'
    )

    # 4) 학기 라벨 추가 (위쪽에 깔끔하게)
    for label_text, label_pos in semester_labels.items():
        plt.text(label_pos[0], label_pos[1], label_text,
                fontsize=16, fontweight='bold', ha='center', va='bottom',
                fontfamily=font_name, color='#424242',
                bbox=dict(boxstyle='round,pad=0.8', facecolor='#E3F2FD',
                         edgecolor='#2196F3', linewidth=2))

    # 4) 범례, 제목, 저장 등 나머지
    legend_patches = [
        plt.Line2D([0], [0], marker='s', color='w',
                markerfacecolor=department_colors[d],
                markeredgecolor='black',
                markersize=12, label=d)
        for d in unique_departments
    ]
    plt.legend(handles=legend_patches, title="학과", loc="upper right",
               fontsize=12, title_fontsize=14, frameon=True, fancybox=True, shadow=True)
    plt.title("커리큘럼 추천 그래프", fontsize=22, fontweight='bold', pad=20, color='#212121')

    plt.axis('off')
    plt.tight_layout()

    # 파일로 저장
    save_path = os.path.join(base_path, f"{index}_{gt_department}_graph.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')

    # Base64 인코딩
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor='white')
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
    """그래프 시각화 및 데이터 정렬 - D3.js HTML 반환"""

    os.makedirs(base_path, exist_ok=True)

    # D3.js 인터랙티브 그래프 HTML 생성
    from service.interactive_graph import create_interactive_graph_html
    graph_html = create_interactive_graph_html(department_graphs)

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

    # D3.js HTML 반환 (기존 PNG 대신)
    return all_departments_data, graph_html 

