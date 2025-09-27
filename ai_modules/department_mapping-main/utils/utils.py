import json
import os
import pickle
import numpy as np
import faiss
from typing import Dict, Any, List, Optional

def load_config() -> Dict[str, str]:
    """JSON 설정 파일에서 키워드 매핑 로드"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "../config/department_mapping.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        keyword_mapping = {}
        for mappings in config.values():
            keyword_mapping.update(mappings)
        return keyword_mapping
    except:
        return {"컴공": "컴퓨터인공지능학부", "ai": "컴퓨터인공지능학부"}

def load_data() -> List[Dict[str, Any]]:
    """PKL 파일에서 학과 데이터 로드"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), "../data/goal_Dataset.pkl")
        with open(data_path, 'rb') as f:
            data = pickle.load(f)
        return data.get('lookup_index', [])
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {str(e)}")
        return []

def load_embeddings() -> Optional[np.ndarray]:
    """실제 임베딩 데이터 로드"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), "../data/goal_Dataset.pkl")
        with open(data_path, 'rb') as f:
            data = pickle.load(f)
        return data.get('embeddings')
    except Exception as e:
        print(f"임베딩 로드 중 오류 발생: {str(e)}")
        return None

def build_faiss_index(embeddings: np.ndarray) -> Optional[faiss.Index]:
    """FAISS 인덱스 구축"""
    if embeddings is not None:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype('float32'))
        return index
    return None

def get_query_embedding(query: str) -> Optional[np.ndarray]:
    """쿼리 임베딩 생성 (실제로는 의미적 임베딩)"""
    # 여기서는 간단한 예시, 실제로는 의미적 임베딩 사용
    return np.random.random(128).astype('float32')