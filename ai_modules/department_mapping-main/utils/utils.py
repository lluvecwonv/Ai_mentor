import json
import os
import pickle
import numpy as np
import faiss
from typing import Dict, Any, List, Optional
from langchain_openai import OpenAIEmbeddings

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
        print(f"✅ 저장된 임베딩 차원: {embeddings.shape}")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype('float32'))
        return index
    return None

def get_query_embedding(query: str) -> Optional[np.ndarray]:
    """쿼리 임베딩 생성 (OpenAI 임베딩 사용)"""
    # OpenAI 임베딩 모델 초기화 - 저장된 데이터와 일치하는 3072 차원 모델 사용
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # 쿼리 임베딩 생성
    query_embedding = embeddings.embed_query(query)
    result = np.array(query_embedding, dtype='float32')
    print(f"✅ 쿼리 임베딩 차원: {result.shape}")
    return result