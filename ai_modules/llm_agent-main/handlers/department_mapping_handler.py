"""
Department Mapping Handler for department name normalization
- 내부 패키지 의존을 제거하고 HTTP로 department-mapping 서비스와 통신
"""

import os
import httpx

from .base_handler import BaseQueryHandler
from typing import Dict, Any


class DepartmentMappingHandler(BaseQueryHandler):
    """Department mapping handler for name normalization"""

    def __init__(self):
        super().__init__()
        self.http = None
        self.mapping_service_url = os.getenv(
            "DEPARTMENT_MAPPING_URL", "http://department-mapping:8000/agent"
        )
        self._init_agent()

    def _init_agent(self):
        """Initialize HTTP client for mapping service"""
        try:
            self.http = httpx.AsyncClient(timeout=10.0)
            self.logger.debug("✅ Department Mapping HTTP 클라이언트 초기화 완료")
        except Exception as e:
            self.logger.warning(f"⚠️ Department Mapping HTTP 클라이언트 초기화 실패: {e}")

    async def warmup(self) -> None:
        """Department Mapping 서비스에 가벼운 요청을 보내 커넥션/서비스를 예열합니다."""
        try:
            self.logger.info("🔥 Department Mapping 핸들러 워밍업 시작")
            if self.http:
                # 간단한 테스트 요청으로 워밍업
                payload = {"query": "테스트", "expanded_keywords": []}
                await self.http.post(self.mapping_service_url, json=payload)
                self.logger.info("✅ Department Mapping 핸들러 워밍업 완료")
            else:
                self.logger.warning("HTTP 클라이언트가 없어 워밍업을 건너뜁니다")
        except Exception as e:
            # 워밍업 실패는 치명적이지 않음
            self.logger.warning(f"Department Mapping 워밍업 중 경고: {e}")

    def is_available(self) -> bool:
        """Check if mapping service is available"""
        return self.http is not None

    def _extract_department_keywords(self, user_message: str) -> str:
        """사용자 메시지에서 학과명 키워드 추출 (주제 기반 매핑 개선)"""
        import re

        text = (user_message or "").strip().lower()
        self.logger.info(f"🔍 키워드 추출 시작: '{text}'")

        # 1. 주제 키워드 → 학과 직접 매핑 (가장 중요!)
        topic_to_dept = {
            '도서관': '문헌정보학과',
            '문헌정보': '문헌정보학과',
            '정보관리': '문헌정보학과',
            '아카이브': '문헌정보학과',
            '컴퓨터': '컴퓨터공학과',
            '컴공': '컴퓨터공학과',
            '프로그래밍': '컴퓨터공학과',
            '소프트웨어': '소프트웨어공학과',
            '소웨공': '소프트웨어공학과',
            '인공지능': '컴퓨터인공지능학부',
            'ai': '컴퓨터인공지능학부',
            '머신러닝': '컴퓨터인공지능학부',
            '전자': '전자공학과',
            '전전': '전자공학과',
            '전기': '전자공학과',
            '기계': '기계공학과',
            '산업': '산업공학과',
            '경영': '경영학과',
            '경제': '경제학과',
            '건축': '건축학과',
            '토목': '토목공학과',
            '화학': '화학과',
            '생명': '생명과학과',
            '물리': '물리학과',
            '수학': '수학과',
            '데이터': '데이터사이언스학과'
        }

        # 주제 키워드 검색
        for topic, dept in topic_to_dept.items():
            if topic in text:
                self.logger.info(f"✅ 주제 키워드 매핑: '{topic}' → '{dept}'")
                return dept

        # 2. 구체적인 학과명 패턴 검색 (기존 로직 유지)
        dept_patterns = [
            r'컴퓨터공학과', r'컴퓨터공학', r'컴퓨터과학', r'전산학', r'전산',
            r'소프트웨어공학과', r'소프트웨어학과', r'정보통신공학', r'정보통신',
            r'전자공학과', r'전기전자공학과', r'전기전자',
            r'기계공학과', r'산업공학과', r'데이터사이언스학과',
            r'경영학과', r'경제학과', r'건축학과', r'토목공학과', r'화학과', r'생명과학과', r'물리학과', r'수학과',
            r'컴퓨터인공지능학부', r'소프트웨어융합대학', r'문헌정보학과'
        ]

        for pattern in dept_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.info(f"🎯 구체적 학과명 발견: '{pattern}'")
                return pattern

        # 3. 전체 텍스트 반환 (의미없는 필터링 제거)
        self.logger.info(f"📝 전체 텍스트 사용: '{text}'")
        return user_message.strip()  # 원본 대소문자 유지

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """Handle department mapping query (async interface)

        간결화: MappingService의 내장 휴리스틱(키워드 매핑/부분 문자열)과 임베딩 유사 검색을 그대로 사용합니다.
        """
        self.logger.info("🏫 Department Mapping 에이전트 처리 시작")

        if not self.is_available():
            return self.get_fallback_message()

        try:
            # 학과명 키워드 추출
            dept_keyword = self._extract_department_keywords(user_message)
            self.logger.info(f"🎯 매핑 대상 키워드: '{dept_keyword}'")
            
            # 1) /agent 엔드포인트 시도(텍스트 결과) - 키워드로 요청
            payload = {"query": dept_keyword, "top_k": 3}
            try:
                resp = await self.http.post(self.mapping_service_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and "message" in data:
                        mapped_result = str(data["message"]) or f"'{dept_keyword}'에 대한 유사한 학과를 찾을 수 없습니다."
                        self.logger.info(f"✅ 학과 매핑 성공: '{dept_keyword}' → {mapped_result}")
                        return mapped_result
            except Exception:
                pass

            # 2) /map 엔드포인트 폴백(구조화 결과)
            base = self.mapping_service_url.rstrip('/')
            if base.endswith('/agent'):
                base = base[: -len('/agent')]
            map_url = base + '/map'
            resp = await self.http.post(map_url, json=payload)
            if resp.status_code != 200:
                return f"학과명 매핑 중 오류가 발생했습니다: HTTP {resp.status_code}"
            data = resp.json()
            depts = data.get("mapped_departments", []) if isinstance(data, dict) else []
            scores = data.get("confidence_scores", []) if isinstance(data, dict) else []
            if not depts:
                return f"'{dept_keyword}'에 대한 유사한 학과를 찾을 수 없습니다."

            best = depts[0]
            best_name = best.get('department_name', '')
            confidence = scores[0] if scores else 0.0
            self.logger.info(f"✅ 학과 매핑 성공: '{dept_keyword}' → {best_name} (신뢰도: {confidence:.2%})")
            lines = [
                f"'{dept_keyword}'에 대한 학과명 매핑 결과:",
                f"✅ 가장 유사한 학과: {best_name or '알 수 없음'}",
                f"📊 신뢰도: {confidence:.2%}"
            ]
            if len(depts) > 1:
                lines.append("🔍 다른 후보들:")
                for i, (dept, score) in enumerate(zip(depts[1:], scores[1:]), start=2):
                    lines.append(f"{i}. {dept.get('department_name', '알 수 없음')} (신뢰도: {score:.2%})")
            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Department Mapping 처리 실패: {e}")
            return f"학과명 매핑 중 오류가 발생했습니다: {str(e)}"

    # 레거시 호환: 과거 호출부에서 사용하던 동기식 인터페이스
    def process_query(self, user_message: str) -> str:
        """Legacy sync API for backward compatibility.
        Delegates to MappingService and returns a plain string message.
        """
        if not self.is_available():
            return self.get_fallback_message()
        try:
            result = self.mapping_agent.find_similar_departments(query=user_message, top_k=3)
            departments = result.get("departments", []) if isinstance(result, dict) else []
            scores = result.get("scores", []) if isinstance(result, dict) else []

            if departments:
                best = departments[0]
                confidence = scores[0] if scores else 0.0
                lines = [
                    f"'{user_message}'에 대한 학과명 매핑 결과:",
                    f"✅ 가장 유사한 학과: {best.get('department_name', '알 수 없음')}",
                    f"📊 신뢰도: {confidence:.2%}"
                ]
                if len(departments) > 1:
                    lines.append("🔍 다른 후보들:")
                    for i, (dept, score) in enumerate(zip(departments[1:], scores[1:]), start=2):
                        lines.append(f"{i}. {dept.get('department_name', '알 수 없음')} (신뢰도: {score:.2%})")
                return "\n".join(lines)
            else:
                return f"'{user_message}'에 대한 유사한 학과를 찾을 수 없습니다."
        except Exception as e:
            self.logger.error(f"Department Mapping 처리 실패(legacy): {e}")
            return f"학과명 매핑 중 오류가 발생했습니다: {str(e)}"

    def get_fallback_message(self) -> str:
        return "학과 매핑 서비스를 사용할 수 없습니다."

    # 로컬 휴리스틱 제거: 모든 로직은 외부 서비스에 위임
