from openai import OpenAI
from typing import List, Dict, Any
import json
from datetime import datetime
import os
import networkx as nx
from pathlib import Path

# ——————————————————————————————————————————
# 프로젝트 구조 상 이 파일이 ai_modules/curriculum-main 폴더 안에 있다고 가정
BASE_DIR    = Path(__file__).resolve().parent        # …/curriculum-main
RESULT_DIR  = BASE_DIR / "result"                    # …/curriculum-main/result
QUERY_DIR   = RESULT_DIR / "query_datetime"          # …/result/query_datetime
SELECT_DIR  = RESULT_DIR / "selected_by_llm"         # …/result/selected_by_llm

# 디렉토리 미리 생성
QUERY_DIR.mkdir(parents=True, exist_ok=True)
SELECT_DIR.mkdir(parents=True, exist_ok=True)
# ——————————————————————————————————————————

#Initialize the OpenAI Client
def initialize_openai_client(api_key:str)->OpenAI:
    return OpenAI(api_key=api_key)


def load_txt(file_path:str)->str:
    with open(file_path,'r')as f:
        return f.read()

    
def create_prerequisite(client, class_info: List[Dict[str,Any]], load_path:str)->str:
    prompot_template = load_txt(load_path)
    class_info = json.dumps(class_info, ensure_ascii=False, indent=4)
    formatted_prompt = prompot_template.replace("{class_info}", class_info)

    
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {"role":"system","content":
                ("You are an educational advisor specializing in curriculum design. "
                "Your task is to carefully analyze the course information provided by the user "
                "and propose a well-thought-out prerequisite structure. "
                "Focus on ensuring that students can progress logically through the curriculum."
                ),
            },
            {'role':'user','content':formatted_prompt},
        ],
        max_tokens = 15000,
        response_format = {'type':"json_object"},
        seed = 1234,
        )

    response= response.choices[0].message.content
    return response


def query_expansion(client, query:str, load_path:str)->str:
    
    prompot_template = load_txt(load_path)
    
    system_prompt = "\n".join([line.strip() for line in prompot_template.split('\n') if line.startswith("### System Prompt")])
    user_prompt = "\n".join([line.strip() for line in prompot_template.split('\n') if not line.startswith("### System Prompt")])
    formatted_prompt = user_prompt.replace("{input_query}", query)
    response = client.chat.completions.create(
        model = "gpt-4o",
        messages =[
            {"role": "system",
             'content': system_prompt
            },
            {'role':'user','content':formatted_prompt},
        ],
        max_tokens = 15000,
        seed = 1234,
        temperature = 0.1,
        top_p = 0.1,
        
    )

    response_text= response.choices[0].message.content
    print(response_text)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")  
    file_name = f"{timestamp}.json"  #  "2024-02-04 14-05-23.json"
    
    save_path = QUERY_DIR / f"{timestamp}.json"
    new_entry = {"query": query, "response": response_text}
    with open(save_path, "w", encoding="utf-8") as file:
        json.dump(new_entry, file, ensure_ascii=False, indent=4)

    return response_text



def get_llm_prediction(client, course1, course2, query=None):

    prompt = f"""
            Based on the information provided below, please analyze and infer the relationship between the two university courses.

            ### **Course 1**
            - **Name**: "{course1['class_name']}"
            - **Department**: {course1['department']}
            - **Year**: {course1['student_grade']} (학년)
            - **Semester**: {course1['semester']} (학기)
            - **Description**: {course1['description']}

            ### **Course 2**
            - **Name**: "{course2['class_name']}"
            - **Department**: {course2['department']}
            - **Year**: {course2['student_grade']} (학년)
            - **Semester**: {course2['semester']} (학기)
            - **Description**: {course2['description']}

            ---

            ### **Key Considerations for Inferring the Relationship:**
            1. **Academic Year & Semester**  
            - A course that is offered in an **earlier year/semester** is **more likely to be a prerequisite** for a course in a later year/semester.  
            - If both courses belong to **different departments**, check whether one logically builds on the other.  

            2. **Departmental & Content Relationship**  
            - If both courses **belong to the same department**, consider whether one is foundational for the other within the curriculum.  
            - If courses **are from different departments**, determine if their core content significantly overlaps.  
            - Some courses may act as **core prerequisites across departments** (e.g., Mathematics → Computer Science, Statistics → AI).  

            3. **Strict Content Relevance for Complementary**  
            - **Complementary** should only be assigned if the courses have **strongly overlapping content** or **directly reinforce each other**.  
            - General interdisciplinary connections (e.g., "both related to AI" or "both useful for business") are **not sufficient** to classify them as complementary.  
            - If there is no strong content similarity, mark the relationship as **Unrelated** instead.  

            ---

            ### **Output Format (One Word Only):**
            Based on the above considerations, determine the relationship and output **only one** of the following terms:
            - **"Prerequisite"** → Course 1 is a required prerequisite for Course 2.  
            - **"Complementary"** → The two courses cover **highly similar** or **reinforcing** content, but one is not a prerequisite for the other.  
            - **"Unrelated"** → The two courses have no meaningful direct relationship in terms of content.  

            (Output **only one word** with no explanation.)
        """

    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages =[
            {"role": "system", "content": "You are an expert in curriculum planning."},
            {'role':'user','content':prompt},
        ],
        seed = 1234,
        max_tokens = 30,
        temperature = 0.1,
        top_p = 0.1,
    )

    response = response.choices[0].message.content
    print(f'✅ Inferred relationship : {response}')
    return response



def selected_edge_by_llm(client, query, department_graphs):
    
    merged_graph = nx.DiGraph()
    course_nodes = {}
    
    for department, G in department_graphs.items():
        for node, node_data in G.nodes(data=True):
            course_nodes[node] = node_data
            merged_graph.add_node(node, **node_data)
        
        for source, target in G.edges():
            merged_graph.add_edge(source, target)
            
    new_edges = []
    all_courses = list(merged_graph.nodes(data=True))

    # ✅ 학과가 다른 강좌들만 비교
    for i in range(len(all_courses)):
        for j in range(i + 1, len(all_courses)):
            course1_id, course1_data = all_courses[i]
            course2_id, course2_data = all_courses[j]

            # ✅ 같은 학과면 건너뜀
            if course1_data.get('department') == course2_data.get('department'):
                continue

            # ✅ 선수과목이 항상 이전 학기로 배정되도록 정렬
            if (
                (course1_data["student_grade"] > course2_data["student_grade"]) or
                (course1_data["student_grade"] == course2_data["student_grade"] and course1_data["semester"] > course2_data["semester"])
            ):
                # ✅ course1이 더 높은 학년/학기면 방향 변경 (무조건 선수과목처럼)
                course1_id, course2_id = course2_id, course1_id
                course1_data, course2_data = course2_data, course1_data
            
            # ✅ 현재 학기가 이전 학기의 선수과목인지 확인 (무조건 이전 학기여야 함)
            if not (
                (course2_data["student_grade"] == course1_data["student_grade"] and course2_data["semester"] == course1_data["semester"] + 1) or
                (course2_data["student_grade"] == course1_data["student_grade"] + 1 and course2_data["semester"] == 1 and course1_data["semester"] == 2)
            ):
                continue  # 학기가 순차적이지 않다면 무시
            
            # ✅ LLM을 호출하여 관계 예측
            relation = get_llm_prediction(client, course1_data, course2_data, query=query)
            
            # ✅ 관계 추가 (Prerequisite 또는 Complementary)
            if relation == "Prerequisite":
                new_edges.append({"from": course1_id, "to": course2_id})
                merged_graph.add_edge(course1_id, course2_id)  # ✅ 선수과목 엣지 추가

            elif relation == "Complementary":
                new_edges.append({"from": course1_id, "to": course2_id})
                merged_graph.add_edge(course1_id, course2_id)


    print(f"✅ 총 {len(new_edges)}개의 새로운 학과 간 관계가 추가되었습니다.")
    
    # ✅ 반환 시 단일 DiGraph가 아닌 딕셔너리 형태로 반환
    return {"merged_graph": merged_graph}


def construct_prompt(self, query: str, selected_depart_names ,retrieved_items):
    
    prompt =  f""" Your task is to analyze the query '{query}', which pertains to career planning for interdisciplinary majors, and rank the following courses based on their relevance.

    ### Step 1: Selecting Relevant Departments
    - Use {selected_depart_names} to identify departments that are most relevant to the query.
    - Rank departments based on their similarity score to the query.
    - Exclude departments with low relevance scores, ensuring only the most relevant ones are selected.

    ### Step 2: Extracting Relevant Courses from Selected Departments
    - For each {retrieved_items}, extract courses (`class_name`) that are most relevant to the query.
    - Consider both the `text` description and its similarity score when selecting courses.
    - Exclude courses that are completely unrelated to the query.
    - If course descriptions are insufficient or unclear, infer their relevance based on department context and course title.

    ### Constraints:

    1. **Exclusion Rule**: If a department has no relevant courses, it should be excluded.
    2. **Minimum Department Requirement**: At least two different departments must be included in the final selection.
    3. **Minimum Course Requirement**: The final selection must include at least 5-12 courses.
    4. **Output Format**: Return the ranked list in JSON format, sorted in descending order of relevance.


    Example output:
    ```json
        {{
        "result": [
            {{
                "class_id": <int>, 
                "class_name": <string>,
                "student_grade": <int>,
                "semester": <int>,
                "department_id": <int>,
                "department_name": <string>,
                "prerequisite": <string>,
                "score": <float>
            }},
            {{
                "class_id": <int>, 
                "class_name": <string>,
                "student_grade": <int>,
                "semester": <int>,
                "department_id": <int>,
                "department_name": <string>,
                "prerequisite": <string>,
                "score": <float>
            }}
        ]
    }}
    ```
    """
    return prompt
    

def selected_by_llm(client, query, selected_depart_names, retrieved_items):
    prompt = construct_prompt(query, selected_depart_names, retrieved_items)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an academic course recommendation expert specializing in interdisciplinary academic advising."},
            {"role": "user", "content": prompt},
        ],
        response_format = {'type':"json_object"},
        seed = 1234,
        temperature = 0,
        top_p = 0.1,
    )
    response_text= response.choices[0].message.content
    print(response_text)
    
    # 현재 시간 기록
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")  # 파일명에 사용할 형식 (":" 제거)
    save_path = SELECT_DIR / f"{timestamp}.json"
    new_entry = {"query": query, "response": response_text}
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(new_entry, f, ensure_ascii=False, indent=4)

    return response_text



def  get_llm_predictions(client, courses, query=None):
    
    query_info = f"User's query of interest: {query}" if query else "No specific user query provided."


    prompt = f"""
        query_info = f"User's query of interest: {query}" if query else "No specific user query provided."

        Based on the provided information and the given user query, analyze the relationship between university courses and generate ID mappings only if specific conditions are met.

        ### Course Information ###
        {courses}

        ### Objective ###
        The goal is to classify the relationship between two given courses as **"Prerequisite"**, **"Complementary"**, or **"None"**.

        ### Criteria for Classification ###

        1️ **Prerequisite**
        - Course 1 must contain essential foundational knowledge or skills required to understand Course 2.
        - Course 2 **cannot be fully understood** without having taken Course 1.
        - If the description of Course 2 **explicitly mentions** that concepts from Course 1 are needed, the prerequisite relationship is established.
        - **Do not classify based on mere similarity.**

        2️ **Complementary (Query-Dependent)**
        - If the two courses cover **different aspects** of a **shared topic** and **enhance each other**, they are considered complementary.
        - Course 1 is not strictly required, but taking both courses together provides additional benefits.
        - Example: "Medical Data Analysis" and "AI for Healthcare" cover different techniques but can be complementary due to the common goal of utilizing medical data.
        - **When evaluating complementary relationships, consider the user’s query ({query_info}).**
        - If the user has a specific research interest or goal, evaluate whether the courses are complementary in that context.
        - For example, if the user expresses interest in "Medical Image Analysis", then courses like "Medical Imaging" and "AI Image Analysis" are likely to be complementary.
        - However, **do not classify as complementary just because both courses are related to AI**.

        3️⃣ **None**
        Output `"None"` if the following conditions are met:
        - The courses are **not related academically or professionally**.
        - The relationship cannot be determined from **superficial keyword similarity**.
        - If the courses are from **completely different domains** and have no interdisciplinary connections, output `"None"`.

        **Example:**
        **"Shakespearean Literature" (English Literature, 2nd year) ↔ "Data Structures" (Computer Science, 2nd year)**
        Output: `"None"`
        (*These courses are not connected academically, technically, or professionally.*)

        {{"from": <Course 1 ID>, "to": <Course 2 ID>}},
        {{"from": <Course 1 ID>, "to": <Course 2 ID>}},
        {{"from": <Course 1 ID>, "to": <Course 2 ID>}},
        {{"from": <Course 1 ID>, "to": <Course 2 ID>}},
        {{"from": <Course 1 ID>, "to": <Course 2 ID>}}
    """

    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages =[
            {"role": "system", "content": "You are an expert in curriculum planning."},
            {'role':'user','content':prompt},
        ],
        seed = 1234,
        temperature = 0.1,
        top_p = 0.1,
    )

    response = response.choices[0].message.content
    print(f'✅ Inferred relationship : {response}')
    return response



import json
import networkx as nx

def selected_edge_by_llm(client, query, department_graphs, logger=None):
    merged_graph = nx.DiGraph()
    course_nodes = {}

    # Merge all department graphs
    for department, G in department_graphs.items():
        for node, node_data in G.nodes(data=True):
            course_nodes[node] = node_data
            merged_graph.add_node(node, **node_data)
        for source, target in G.edges():
            merged_graph.add_edge(source, target)

    all_courses = list(merged_graph.nodes(data=True))
    course_pairs = []

    # Compare only courses from different departments
    for i in range(len(all_courses)):
        for j in range(i + 1, len(all_courses)):
            course1_id, course1_data = all_courses[i]
            course2_id, course2_data = all_courses[j]

            # Skip if they belong to the same department
            if course1_data.get('department') == course2_data.get('department'):
                continue

            if (
                (course1_data["student_grade"] > course2_data["student_grade"]) or
                (course1_data["student_grade"] == course2_data["student_grade"] and course1_data["semester"] > course2_data["semester"])
            ):
                course1_id, course2_id = course2_id, course1_id
                course1_data, course2_data = course2_data, course1_data


            if not (
                (course2_data["student_grade"] == course1_data["student_grade"] and course2_data["semester"] == course1_data["semester"] + 1) or
                (course2_data["student_grade"] == course1_data["student_grade"] + 1 and course2_data["semester"] == 1 and course1_data["semester"] == 2)
            ):
                continue

            # Add candidate relationships
            course_pairs.append((course1_id, course2_id, course1_data, course2_data))

    raw_relations = get_llm_predictions(client, course_pairs, query=query)

    new_edges = []

    try:
        # **Ensure the response is wrapped in square brackets**
        cleaned_json_string = raw_relations.strip()
        if not cleaned_json_string.startswith("["):
            cleaned_json_string = "[" + cleaned_json_string
        if not cleaned_json_string.endswith("]"):
            cleaned_json_string = cleaned_json_string + "]"

        # **Attempt to parse JSON**
        parsed_relations = json.loads(cleaned_json_string)

        # ✅ Handle both list and dictionary cases
        if isinstance(parsed_relations, list):
            for edge in parsed_relations:
                if isinstance(edge, dict) and "from" in edge and "to" in edge:
                    new_edges.append(edge)
                else:
                    print(f"⚠️ Invalid JSON structure received: {edge}")
        else:
            print(f"⚠️ Unexpected JSON format: {parsed_relations}")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        print(f"⚠️ Raw LLM Output: {raw_relations}")


    for edge in new_edges:
        merged_graph.add_edge(int(edge["from"]), int(edge["to"]))  # Ensure IDs are integers
        print(edge)  # Print each edge in the required format

    print(f"{len(new_edges)} new interdepartmental relationships have been added.")

    return {"merged_graph": merged_graph}
