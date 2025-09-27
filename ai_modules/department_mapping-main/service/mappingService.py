import os
import re
import pickle
from typing import List, Dict, Any, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
logger = logging.getLogger(__name__)

class MappingService:
    def __init__(self):
        """학과명 매핑 서비스 초기화"""
        self.departments_data: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.keyword_mapping: Dict[str, str] = {}
        self._name_index: Dict[str, Dict[str, Any]] = {}
        self.load_embedding_data()
        self.setup_keyword_mapping()
        self._build_name_index()
    
    def load_embedding_data(self):
        """임베딩 데이터 로드"""
        try:
            pkl_path = "/app/data/goal_Dataset.pkl"
            if os.path.exists(pkl_path):
                with open(pkl_path, 'rb') as f:
                    data = pickle.load(f)
                self.embeddings = data.get('embeddings')
                self.departments_data = data.get('lookup_index', []) or []
                logger.info(f"✅ 임베딩 데이터 로드 완료: {len(self.departments_data)}개 학과")
            else:
                logger.warning(f"❌ 임베딩 파일을 찾을 수 없습니다: {pkl_path}")
                self.embeddings = None
                self.departments_data = []
        except Exception as e:
            logger.error(f"❌ 임베딩 데이터 로드 실패: {e}")
            self.embeddings = None
            self.departments_data = []
    
    def setup_keyword_mapping(self):
        """키워드 매핑 설정(소문자/공백제거 키 기준)"""
        mapping = {
            # 컴퓨터 관련 - 실제 학과명에 맞춰 수정
            "컴공": "컴퓨터인공지능학부",
            "컴퓨터공학과": "컴퓨터인공지능학부",
            "컴퓨터공학": "컴퓨터인공지능학부",
            "컴퓨터": "컴퓨터인공지능학부",
            "컴퓨터학과": "컴퓨터인공지능학부",
            "ai": "컴퓨터인공지능학부",
            "인공지능": "컴퓨터인공지능학부",
            
            # 전자공학 관련
            "전자공학과": "전자공학부",
            "전자공학": "전자공학부",
            "전자": "전자공학부",
            "전전": "전자공학부",
            
            # 기계공학 관련
            "기계공학과": "기계시스템공학부",
            "기계공학": "기계시스템공학부",
            "기계": "기계시스템공학부",
            "기계설계": "기계설계공학부",
            
            # 경영/경제 관련
            "경영학과": "경영학과",
            "경영학": "경영학과",
            "경제학과": "경제학부",
            "경제학": "경제학부",
            
            # 건축 관련
            "건축공학과": "건축공학과",
            "건축": "건축공학과",
            
            # 문헌정보학과 관련
            "문정과": "문헌정보학과",
            "문헌정보학과": "문헌정보학과",
            "문헌정보학": "문헌정보학과",
            "문헌정보": "문헌정보학과",
            "도서관학": "문헌정보학과",
            "정보학": "문헌정보학과",

            # 기타
            "고분자나노공학과": "고분자나노공학과",
            "고분자": "고분자나노공학과",
            "나노": "고분자나노공학과",
        }
        self.keyword_mapping = {self._norm_key(k): v for k, v in mapping.items()}

    def _build_name_index(self):
        self._name_index = {}
        for dept in self.departments_data or []:
            name = dept.get("department_name")
            if name:
                self._name_index[name] = dept
    
    def find_similar_departments(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        쿼리와 유사한 학과들을 찾습니다.

        Args:
            query: 검색할 학과명 또는 전체 문장 (예: "컴공", "컴공에서 인공지능 수업을 찾아줘")
            top_k: 반환할 상위 k개 결과

        Returns:
            유사한 학과들의 정보와 신뢰도 점수
        """
        logger.info(f"🏫 DEPT MAPPING START (학과 매핑 시작)")
        logger.info(f"  의미: 사용자 입력에서 학과명을 추출하여 표준 학과명으로 정규화")
        logger.info(f"  입력 쿼리: '{query}'")
        logger.info(f"  요청 결과 수: 상위 {top_k}개")

        # 문장에서 학과명 키워드 추출
        extracted_keywords = self._extract_department_keywords(query)
        logger.info(f"  🔍 추출된 학과 키워드: {extracted_keywords}")

        if not self.departments_data:
            logger.warning("  ⚠️ 학과 데이터 없음 - 빈 결과 반환")
            return {"departments": [], "scores": []}
        
        try:
            # 1. 추출된 키워드들로 키워드 매핑 시도
            for keyword in extracted_keywords:
                normalized_keyword = self._norm_key(keyword)
                logger.info(f"  🔄 키워드 매핑 시도: '{keyword}' → '{normalized_keyword}'")

                if normalized_keyword in self.keyword_mapping:
                    target_dept = self.keyword_mapping[normalized_keyword]
                    logger.info(f"  ✅ 키워드 매핑 성공: '{normalized_keyword}' → '{target_dept}'")
                    hit = self.get_department_by_name(target_dept)
                    if hit:
                        result = {
                            "departments": [self._format_dept(hit)],
                            "scores": [0.95]
                        }
                        logger.info(f"  📊 키워드 매핑 결과: {hit.get('department_name', 'Unknown')} (신뢰도: 0.95)")
                        return result
                    else:
                        logger.warning(f"  ⚠️ 매핑된 학과 '{target_dept}' 데이터에서 찾을 수 없음")

            logger.info(f"  ➡️ 모든 키워드 매핑 실패 - 유사도 검색으로 진행")
            
            # 2. 부분 문자열 매칭
            logger.info(f"  🔍 부분 문자열 매칭 시작 ({len(self.departments_data)}개 학과 대상)")
            departments = []
            scores = []

            for dept in self.departments_data:
                dept_name = dept["department_name"].lower()
                query_lower = query.lower()

                # 정확한 매칭
                if query_lower in dept_name or dept_name in query_lower:
                    departments.append(self._format_dept(dept))
                    scores.append(0.9)
                    logger.debug(f"    정확 매칭: {dept['department_name']} (점수: 0.9)")
                # 키워드 포함 매칭
                elif any(keyword in dept_name for keyword in query_lower.split()):
                    departments.append(self._format_dept(dept))
                    scores.append(0.7)
                    logger.debug(f"    키워드 매칭: {dept['department_name']} (점수: 0.7)")

            # 상위 k개 반환
            if departments:
                sorted_results = sorted(zip(departments, scores), key=lambda x: x[1], reverse=True)
                top_results = sorted_results[:top_k]
                result = {
                    "departments": [r[0] for r in top_results],
                    "scores": [r[1] for r in top_results]
                }
                logger.info(f"  📊 유사도 검색 결과: {len(top_results)}개 후보 발견")
                for i, (dept, score) in enumerate(top_results, 1):
                    logger.info(f"    후보 {i}: {dept.get('department_name', 'Unknown')} (신뢰도: {score:.3f})")
                return result

            logger.info(f"  ❌ 매칭 결과 없음 - 빈 결과 반환")
            return {"departments": [], "scores": []}
            
        except Exception as e:
            logger.error(f"  ❌ 학과 매핑 처리 실패: {e}")
            return {"departments": [], "scores": []}
    
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """모든 학과 목록 반환"""
        if not self.departments_data:
            return []
        
        return [
            {
                "department_id": dept["department_id"],
                "department_name": dept["department_name"],
                "description": dept["text"][:100] + "..." if len(dept["text"]) > 100 else dept["text"]
            }
            for dept in self.departments_data
        ]
    
    def normalize_department_name(self, name: str) -> str:
        """
        학과명 정규화
        - 공백 제거
        - 접미어 통일 (과/학부)
        - 동의어 매핑
        """
        # 공백 제거
        normalized = name.replace(" ", "")
        
        # 동의어/별칭 매핑(키워드 매핑과 동일 규칙 사용)
        mapped = self.keyword_mapping.get(self._norm_key(normalized))
        return mapped or normalized
    
    def get_department_by_name(self, name: str) -> Dict[str, Any]:
        """정확한 학과명으로 학과 정보 조회"""
        normalized_name = self.normalize_department_name(name)
        logger.info(f"  🔍 학과명 조회: '{name}' → 정규화: '{normalized_name}'")

        result = self._name_index.get(normalized_name)
        if result:
            logger.info(f"  ✅ 학과 정보 찾음: {result.get('department_name')}")
        else:
            logger.warning(f"  ❌ 학과 정보 찾지 못함. 인덱스 키들: {list(self._name_index.keys())[:5]}...")

        return result

    def _extract_department_keywords(self, query: str) -> List[str]:
        """문장에서 학과명 관련 키워드 추출"""
        keywords = []
        query_lower = query.lower()

        # setup_keyword_mapping()에서 설정한 매핑을 역으로 활용
        # self.keyword_mapping의 키들을 denormalize해서 원본 키워드들 복원
        original_keys = [
            "컴공", "컴퓨터공학과", "컴퓨터공학", "컴퓨터", "컴퓨터학과", "ai", "인공지능",
            "전자공학과", "전자공학", "전자", "전전",
            "기계공학과", "기계공학", "기계", "기계설계",
            "경영학과", "경영학", "경제학과", "경제학",
            "건축공학과", "건축",
            "문정과", "문헌정보학과", "문헌정보학", "문헌정보", "도서관학", "정보학",
            "고분자나노공학과", "고분자", "나노"
        ]

        # 문장에서 키워드 찾기
        for key in original_keys:
            if key.lower() in query_lower and key not in keywords:
                keywords.append(key)
                logger.debug(f"    키워드 발견: '{key}' in '{query}'")

        return keywords if keywords else [query]  # 키워드 없으면 원본 쿼리 반환

    # ===== 내부 유틸 =====
    def _norm_key(self, s: str) -> str:
        return (s or '').replace(' ', '').lower()

    def _format_dept(self, dept: Dict[str, Any]) -> Dict[str, Any]:
        text = dept.get('text', '') or ''
        return {
            "department_id": dept.get("department_id"),
            "department_name": dept.get("department_name"),
            "description": text[:200] + ("..." if len(text) > 200 else "")
        }
