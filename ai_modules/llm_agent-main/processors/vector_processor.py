"""
벡터 검색 처리기
- 확장된 키워드 기반 검색
- 캐시 관리
- 성능 추적
"""

import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VectorProcessor:
    """벡터 검색 전담 처리기"""

    def __init__(self, vector_handler):
        self.vector_handler = vector_handler
        # LangGraph 전용 모드로 간소화
        self.cache = {}
        self.cache_ttl = 300  # 5분 캐시
        logger.debug("VectorProcessor 초기화 완료")

    async def process(self, data: Dict[str, Any]) -> str:
        """벡터 검색 처리"""
        # LangGraph 전용 모드로 간소화
        try:
            user_message = data.get("user_message", "")
            combined_analysis = data.get("analysis", data.get("combined_analysis", {}))

            # 확장된 키워드 추출
            expanded_keywords = combined_analysis.get("expansion_keywords", user_message)
            search_query = expanded_keywords if expanded_keywords else user_message

            # 옵션 A 확장: 쿼리/키워드/매핑에서 학과 힌트 추출 후 보강
            dept_hint = self._extract_department_hint(user_message, combined_analysis, data.get("mapping_context"))
            if dept_hint:
                # 여러 개면 첫 번째만 사용 (필요시 조합 가능)
                if isinstance(dept_hint, list):
                    dept_hint = dept_hint[0] if dept_hint else None
            if isinstance(dept_hint, str) and dept_hint and dept_hint not in str(search_query):
                search_query = f"{search_query},{dept_hint}"
            # 핸들러에서도 사용할 수 있도록 분석 딕셔너리에 주입
            if isinstance(dept_hint, str) and dept_hint:
                combined_analysis = dict(combined_analysis or {})
                combined_analysis['dept_hint'] = dept_hint

            logger.debug(f"벡터 검색 쿼리: {search_query}")

            # 캐시 확인
            cache_key = self._generate_cache_key(search_query, combined_analysis)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug("벡터 검색 캐시 히트")
                return cached_result

            # 벡터 검색 실행 (보강된 분석 전달)
            result = await self.vector_handler.handle(search_query, combined_analysis)
            result_str = str(result)

            # 캐시 저장
            self._save_to_cache(cache_key, result_str)

            logger.info(f"벡터 검색 완료: {len(result_str)}자")
            return result_str

        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return f"벡터 검색 오류: {str(e)}"

    def _extract_department_hint(self, user_message: str, analysis: Dict[str, Any], mapping_ctx: Any) -> Any:
        """사용자 입력/분석/매핑 결과에서 학과 힌트 추출"""
        import re

        # 1) 매핑 컨텍스트에서 추출
        if isinstance(mapping_ctx, str) and mapping_ctx:
            m = re.search(r"가장 유사한 학과\s*:\s*([^\n]+)", mapping_ctx)
            if m:
                return m.group(1).strip()

        # 2) 분석 키워드에서 추출 (예: "컴퓨터공학과, 인공지능, ...")
        kw = analysis.get("expansion_keywords") or ""
        candidates = []
        for token in [t.strip() for t in str(kw).split(',') if t.strip()]:
            if token.endswith("학과") or token.endswith("학부") or token.endswith("전공"):
                candidates.append(token)
            elif any(s in token for s in ["컴퓨터공학", "전기전자", "소프트웨어", "데이터사이언스", "수학", "통계"]):
                # 흔한 학과 키워드 휴리스틱
                if not token.endswith("학과"):
                    candidates.append(token + ("학과" if not token.endswith("학부") else ""))
        if candidates:
            return candidates

        # 3) 사용자 메시지에서 추출 (간단 정규식)
        m2 = re.search(r"([가-힣A-Za-z]+?(?:학과|학부|전공))", user_message)
        if m2:
            return m2.group(1)

        # 4) 별칭 치환 (컴공 등)
        if "컴공" in user_message and "컴퓨터공학" not in user_message:
            return "컴퓨터공학과"

        return None

    def _generate_cache_key(self, query: str, analysis: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        return f"vector_{hash(query)}_{hash(str(analysis))}"

    def _get_from_cache(self, cache_key: str) -> str:
        """캐시에서 결과 조회"""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self.cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, result: str):
        """캐시에 결과 저장"""
        self.cache[cache_key] = (result, time.time())
        self._cleanup_cache()

    def _cleanup_cache(self):
        """오래된 캐시 정리"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]

        # 캐시 크기 제한
        if len(self.cache) > 100:
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:20]
            for key in oldest_keys:
                del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            "processor_type": "VectorProcessor",
            "cache_size": len(self.cache),
            "performance": self.performance_tracker.get_performance_stats("vector_search")
        }
