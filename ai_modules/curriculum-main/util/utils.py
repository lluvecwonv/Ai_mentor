from openai import OpenAI
from typing import List, Dict, Any

import copy
import os
import json

def read_txt(file_path:str)->str:
    query_list = []
    with open(file_path,'r')as f:
        lines = f.readlines()
        for line in lines:
            query_list.append(line)
        return query_list


def read_json(file_path:str):
    with open(file_path,'r')as f:
        data = json.load(f)
    return data


def update_json_with_index(file_path, idx, query, query_info, selected_depart_list):

    if not os.path.exists(file_path):
        print(f"🔹 {file_path} not found. Creating new JSON file.")
        data = {}  
    else:
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)  
            if not isinstance(data, dict): 
                print(f"🔹 {file_path} is not a valid JSON dictionary. Resetting.")
                data = {} 
        except json.JSONDecodeError:  
            print(f"🔹 {file_path} is empty or invalid. Resetting JSON file.")
            data = {}  

    
    data[idx] = {
        "query": query,
        "query_info": query_info,
        "selected_depart_list": selected_depart_list
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"✅ Successfully updated JSON at index {idx}.")


def save_sorted_courses_as_json(base_path, department, sorted_courses, G):

    sorted_data = []

    for course in sorted_courses:
        course_data = G.nodes[course]  

        sorted_data.append({
            "course_id": course,
            "course_name": course_data.get("class_name", f"Unnamed Node {course}"),
            "department": course_data.get("department", "Unknown Department"),
            "semester": course_data.get("semester", "Unknown"),
            "student_grade": course_data.get("student_grade", "Unknown"),
            "is_mandatory_for_major": course_data.get("is_mandatory_for_major", "Unknown"),  
            'description': course_data.get('description',"Unknown") 
        })
    
    return sorted_data 


def save_merged_json(merged_data, base_path,idx, gt_department):

    merged_path = os.path.join(base_path, f"{idx}_{gt_department}_recommendations.json")
    print(f'saving_path: {merged_path}')
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=4, ensure_ascii=False)
    print(f'save merged json: {merged_path}')


def format_curriculum_response(result: Dict[str, Any]) -> str:
    """JSON 데이터를 사람이 읽기 편한 텍스트로 변환 - 학년-학기 순서대로 정렬"""

    recommended_courses = result.get('recommended_courses', [])

    # 학년-학기 순으로 정렬
    def sort_key(course):
        grade = course.get('student_grade', 99)
        semester = course.get('semester', 99)
        return (grade, semester)

    sorted_courses = sorted(recommended_courses, key=sort_key)

    # 텍스트 응답 생성 - 학년-학기별로 그룹화
    response = "과목을 추천해드리겠습니다.\n\n"

    current_grade = None
    current_semester = None
    course_number = 1

    for course in sorted_courses:
        name = course.get('name', '')
        department = course.get('department', '')
        grade = course.get('student_grade', '')
        semester = course.get('semester', '')
        description = course.get('description', '').strip()

        # 학년-학기가 바뀔 때마다 헤더 출력 (더 크고 진하게)
        if grade != current_grade or semester != current_semester:
            current_grade = grade
            current_semester = semester
            if grade and semester:
                response += f"\n## **📚 {grade}학년 {semester}학기**\n\n"

        # 과목명을 볼드체로 (마크다운 형식)
        response += f"{course_number}. **{name}**\n"
        response += f"   - 학과: {department}\n"

        if description:
            # 설명 전체 출력 (잘리지 않게)
            response += f"   - 설명: {description}\n"

        response += "\n"
        course_number += 1

    print(f"커리큘럼 응답 포맷팅 완료: {len(response)}자")

    return response

