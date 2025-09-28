import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from collections import defaultdict
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import json
from utils import save_sorted_courses_as_json, save_merged_json
import seaborn as sns
from pathlib import Path
import base64
import io

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

    semester_order = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"]
    semester_dict = {semester: i for i, semester in enumerate(semester_order)}  

    semester_counts = defaultdict(int)
    semester_nodes = defaultdict(list)  

    for node, data in G.nodes(data=True):
        student_grade = str(data.get("student_grade", "Unknown"))
        semester = str(data.get("semester", "Unknown"))
        key = f"{student_grade}-{semester}"
        
        if key in semester_dict:
            semester_counts[key] += 1
            semester_nodes[key].append(node)

    positions = {}

    for key, nodes in semester_nodes.items():
        x_pos = semester_dict[key]  
        num_nodes = len(nodes)  
        
        y_start = -(num_nodes // 2)  
        y_positions = [y_start + i for i in range(num_nodes)]  

        for i, node in enumerate(nodes):
            y_pos = y_positions[i]  
            positions[node] = (x_pos, y_pos)  

    
    semester_labels = {}
    for semester, x_pos in semester_dict.items():
        semester_labels[f"학기_{semester}"] = (x_pos, 2) 

    positions.update(semester_labels)  

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

    
    custom_colors = sns.color_palette("Set3", n_colors=len(unique_departments))
    department_colors = {dept: custom_colors[i % len(custom_colors)] for i, dept in enumerate(unique_departments)}

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

    
    plt.figure(figsize=(16, 10))

    # 1) 노드 + 엣지 그리기 (레이블은 모두 끔)
    nx.draw_networkx_nodes(
        combined_graph, pos,
        node_shape='o',            # 직사각형 노드
        node_size=2400,
        node_color=[department_colors[node_department_map[n]] for n in combined_graph.nodes()],
        edgecolors='black',
        linewidths=1.2
    )
    nx.draw_networkx_edges(
        combined_graph, pos,
        edgelist=combined_graph.edges(),
        arrowstyle='-|>',
        arrowsize=12,
        width=1.0,
        edge_color='gray'
    )

    # 2) 과목명: 노드 중앙에
    name_labels = {n: combined_graph.nodes[n]['class_name'] for n in combined_graph.nodes()}
    nx.draw_networkx_labels(
        combined_graph, pos,
        labels=name_labels,
        font_size=10,
        font_weight='heavy',
        font_family=font_name,
        verticalalignment='center',
        horizontalalignment='center'
    )

    # 3) ID: 노드 바로 아래에
    id_labels = {n: str(n) for n in combined_graph.nodes()}
    id_pos = {n: (pos[n][0], pos[n][1] - 0.1) for n in combined_graph.nodes()}  # y-offset 조정
    nx.draw_networkx_labels(
        combined_graph, id_pos,
        labels=id_labels,
        font_size=8,
        font_weight='bold',
        font_family=font_name,
        verticalalignment='top',
        horizontalalignment='center'
    )

    # 4) 범례, 제목, 저장 등 나머지
    legend_patches = [
        plt.Line2D([0], [0], marker='s', color='w',
                markerfacecolor=department_colors[d],
                markeredgecolor='black',
                markersize=12, label=d)
        for d in unique_departments
    ]
    plt.legend(handles=legend_patches, title="학과별 색상", loc="upper right", fontsize=10, title_fontsize=12)
    plt.title(f"{index} · {gt_department} 통합 선수과목 그래프", fontsize=18, fontweight='bold')

    plt.axis('off')

    # 파일로 저장
    save_path = os.path.join(base_path, f"{index}_{gt_department}_graph.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')

    # Base64 인코딩
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    graph_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    plt.close()

    return f"data:image/png;base64,{graph_base64}"



def build_prereq_postreq(class_retriever, selected_list, db_handler,query_embbeding=None,logger=None, 
                         existing_visited_ids=None,required_dept_count=None):

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



def visualize_and_sort_department_graphs(department_graphs, base_path="./graphs/",index =None, gt_department =None):
    
    os.makedirs(base_path, exist_ok=True)
    
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

    save_merged_json(merged_data, base_path,index,gt_department)
    # visualize_graph_from_merged_data(merged_data,base_path,idx,gt_department)

    graph_base64 = visualize_graph_from_data(department_graphs,base_path,index,gt_department)

    return all_departments_data, graph_base64 

