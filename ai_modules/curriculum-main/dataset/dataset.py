from torch.utils.data import Dataset
from collections import defaultdict

class goalDataset(Dataset):
    def __init__(self, data, group_by="department_id"):
        """
        Group documents by a specific key (e.g., department_id or college_name).
        
        Args:
            data (list of dict): List of documents.
            group_by (str): The key to group by (e.g., 'department_id').
        """
        self.data = data
        self.groups = defaultdict(list)

        # Group documents by the specified key
        for doc in data:
            group_key = doc[group_by]
            self.groups[group_key].append(doc)

        self.group_keys = list(self.groups.keys())

    def __len__(self):
        return len(self.group_keys)

    def __getitem__(self, index):
        group_key = self.group_keys[index]
        docs = self.groups[group_key]

        # 올바르게 department_name 가져오기
        department_name = docs[0]['department_name'] if docs else "Unknown"

        combined_text = ""
        doc_ids = []
        for doc in docs:
            text = f" curriculum: {doc['curriculum']}\n"
            combined_text += text
            doc_ids.append(doc["class_id"])  # Collect document IDs for this group
        # print(f"department_id: {group_key}, department_name: {department_name}, text: {combined_text}, doc_ids: {doc_ids}")
        
        return {"department_id": group_key, "department_name": department_name, "text": combined_text, "doc_ids": doc_ids}


class goalDatasetjson(Dataset):
    def __init__(self, data, group_by="id"):
        self.data = data
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, index):
        doc = self.data[index]
        
        department_id = doc["department_id"]
        department_name = doc.get("학과", "Unknown")
        description = doc.get("학과설명", "")

        return {
            "department_id": department_id,
            "department_name": department_name,
            "text": description,
        }



class class_depart_Dataset(Dataset):
    def __init__(self,data):
        self.data = data
     
    def __len__(self):
        return len(self.data) 
    
    def __getitem__(self, index):
        
        class_doc = self.data[index]   
        #class_name 
        student_grade = class_doc.get('student_grade',"Unknown")
        semester = class_doc.get('semester', "Unknown") 
        department_name = class_doc.get("department_name", "Unknown")
        class_name = class_doc.get("class_name", "Unknown")
        class_id = class_doc.get("class_id", "Unknown")
        department_id = class_doc.get("department_id", "Unknown")
        # curriculum = class_doc.get("class_curriculum", "")
        # contetnt = class_doc.get("class_content", "")
        description = class_doc.get("class_description","Unknown")
        #R_prerequisite
        prerequisite = class_doc.get('R_prerequisite',"Unknown")
        
        
        combined_text = ""
        text = f"{class_name},{description} "
        combined_text += text
            
        return{
            'department_id': department_id,
            'department_name': department_name,
            'student_grade': student_grade,  
            'semester': semester, 
            'class_name': class_name,
            'class_id': class_id,
            'text': combined_text,
            'prerequisite':prerequisite
        }
            
        
        
        
            
    