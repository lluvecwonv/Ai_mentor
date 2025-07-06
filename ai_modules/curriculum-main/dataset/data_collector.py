from transformers import DataCollatorWithPadding, DefaultDataCollator
import torch    

def collect_goal(batch):
    batch_dict ={
        'text' : [item['text'] for item in batch],
        'department_id' : [item['department_id'] for item in batch],
        'department_name' : [item['department_name'] for item in batch],  
    }
    return batch_dict
     

def collect_class(batch):
    return {
        "class_id": [item.get("class_id", "Unknown") for item in batch],  
        "class_name": [item.get("class_name", "Unknown") for item in batch], 
        "department_id": [item.get("department_id", "Unknown") for item in batch],
        "department_name": [item.get("department_name", "Unknown") for item in batch],
        "student_grade": [item.get("student_grade", "Unknown") for item in batch],  # ✅ 추가됨
        "semester": [item.get("semester", "Unknown") for item in batch],  # ✅ 추가됨
        "text": [item.get("text", "") for item in batch],
        "prerequisite": [item.get("prerequisite", "") for item in batch]
    }
