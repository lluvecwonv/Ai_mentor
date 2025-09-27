"""
SQL 쿼리 처리기
- 데이터베이스 쿼리 실행
- 캐시 관리
- 성능 추적
"""

import time
import logging
from typing import Dict, Any
# LangGraph 전용 모드로 간소화

logger = logging.getLogger(__name__)

class SqlProcessor:
    """SQL 쿼리 전담 처리기 (세션 캐시 지원)"""

    def __init__(self, sql_handler, conversation_memory=None):
        self.sql_handler = sql_handler
        self.conversation_memory = conversation_memory
        # LangGraph 전용 모드로 간소화
        self.cache = {}
        self.cache_ttl = 600  # 10분 캐시 (DB 쿼리는 더 오래)
        logger.debug("SqlProcessor 초기화 완료")

    async def process(self, data: Dict[str, Any]) -> str:
        """SQL 쿼리 처리"""
        # LangGraph 전용 모드로 간소화
        try:
            user_message = data.get("user_message", "")
            combined_analysis = data.get("analysis", data.get("combined_analysis", {}))

            logger.debug(f"SQL 쿼리: {user_message}")

            # 세션 엔티티 캐시 확인(교수/과목 중심)
            session_id = data.get("session_id", "default")
            hit = self._check_entity_cache(session_id, user_message, combined_analysis)
            if hit:
                logger.info("SQL 세션 캐시 히트: 엔티티 기반 응답")
                return hit

            # 프로세서 내부 캐시 확인(문자열 키)
            cache_key = self._generate_cache_key(user_message, combined_analysis)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug("SQL 쿼리 캐시 히트")
                return cached_result

            # SQL 쿼리 실행 (스트리밍 지원 확인)
            if hasattr(self.sql_handler, 'handle_with_streaming'):
                logger.info("SQL 스트리밍 모드 사용")
                # 스트리밍 모드는 체인 매니저에서 처리하므로 여기서는 일반 모드 사용
                result = await self.sql_handler.handle(user_message, combined_analysis)
            else:
                result = await self.sql_handler.handle(user_message, combined_analysis)

            result_str = str(result)

            # 캐시 저장
            self._save_to_cache(cache_key, result_str)

            # 엔티티 캐시에 저장 시도
            self._maybe_store_entity_cache(session_id, user_message, combined_analysis, result_str)

            logger.info(f"SQL 쿼리 완료: {len(result_str)}자")
            return result_str

        except Exception as e:
            logger.error(f"SQL 쿼리 실패: {e}")
            return f"SQL 쿼리 오류: {str(e)}"

    async def process_with_streaming(self, data: Dict[str, Any]):
        """스트리밍 방식으로 SQL 쿼리 처리"""
        try:
            user_message = data.get("user_message", "")
            combined_analysis = data.get("analysis", data.get("combined_analysis", {}))
            session_id = data.get("session_id", "default")

            logger.debug(f"SQL 스트리밍 쿼리: {user_message}")

            # 캐시 확인 (즉시 응답 가능한 경우)
            hit = self._check_entity_cache(session_id, user_message, combined_analysis)
            if hit:
                logger.info("SQL 캐시 히트: 즉시 응답")
                from utils.streaming_utils import StreamingUtils
                async def _cached_response():
                    yield StreamingUtils.create_status_chunk("cached", "캐시된 결과를 제공합니다...")
                    # 캐시된 결과를 청크로 나누어 전송
                    chunks = self._split_response_into_chunks(hit)
                    for chunk in chunks:
                        yield StreamingUtils.create_content_chunk(chunk)
                        await asyncio.sleep(0.05)  # 더 빠른 출력
                return _cached_response()

            # 스트리밍 SQL 핸들러 호출
            if hasattr(self.sql_handler, 'handle_with_streaming'):
                return await self.sql_handler.handle_with_streaming(user_message, combined_analysis)
            else:
                # 폴백: 일반 처리 후 스트리밍으로 변환
                result = await self.sql_handler.handle(user_message, combined_analysis)
                return self._convert_to_streaming(result)

        except Exception as e:
            logger.error(f"SQL 스트리밍 쿼리 실패: {e}")
            from utils.streaming_utils import StreamingUtils
            async def _error_response():
                yield StreamingUtils.create_error_chunk(f"SQL 쿼리 오류: {str(e)}")
            return _error_response()

    def _split_response_into_chunks(self, response: str, chunk_size: int = 80) -> list:
        """응답을 청크로 분할 (SQL 프로세서용)"""
        # 문장 단위로 분할
        sentences = []
        current = ""

        for char in response:
            current += char
            if char in '.!?\n' and len(current.strip()) > 10:
                sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        return [sentence + " " for sentence in sentences if sentence.strip()]

    async def _convert_to_streaming(self, result: str):
        """일반 결과를 스트리밍으로 변환"""
        from utils.streaming_utils import StreamingUtils
        import asyncio

        async def _stream_result():
            chunks = self._split_response_into_chunks(result)
            for chunk in chunks:
                yield StreamingUtils.create_content_chunk(chunk)
                await asyncio.sleep(0.1)  # 자연스러운 타이핑 효과

        return _stream_result()

    def _generate_cache_key(self, query: str, analysis: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        return f"sql_{hash(query)}_{hash(str(analysis))}"

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
        if len(self.cache) > 50:  # SQL 캐시는 더 작게
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:10]
            for key in oldest_keys:
                del self.cache[key]

    # --- 세션 엔티티 캐시 로직 ---
    def _extract_entities(self, user_message: str, analysis: Dict[str, Any]) -> Dict[str, str]:
        """구조화된 엔티티 추출 (LLM이 이미 분류한 entities 사용)

        우선순위:
        1. LLM이 구조화한 entities 사용 (professor, course, department)
        2. 실패 시 기존 키워드 기반 추출로 폴백
        """
        entities: Dict[str, str] = {}
        
        # 1) LLM이 구조화한 entities 우선 사용
        llm_entities = analysis.get('entities', {})
        if isinstance(llm_entities, dict):
            if llm_entities.get('professor'):
                entities['professor'] = llm_entities['professor']
            if llm_entities.get('course'):
                entities['course'] = llm_entities['course']
            if llm_entities.get('department'):
                entities['department'] = llm_entities['department']
        
        # 2) LLM entities가 없거나 불완전한 경우 기존 방식으로 폴백
        if not entities.get('professor') or not entities.get('course'):
            entities.update(self._extract_entities_fallback(user_message, analysis))
        
        # 디버깅 로그
        try:
            logger.info(f"CACHE_ENTITY_KEYS: professor={entities.get('professor','')}, course={entities.get('course','')}")
        except Exception:
            pass

        return entities

    def _extract_entities_fallback(self, user_message: str, analysis: Dict[str, Any]) -> Dict[str, str]:
        """기존 키워드 기반 엔티티 추출 (폴백용)"""
        entities: Dict[str, str] = {}
        text = user_message or ""
        keywords = [t.strip() for t in str(analysis.get('expansion_keywords', '')).split(',') if t.strip()]

        # 1) 교수명 정규식 매칭
        import re
        prof = ""
        m = re.search(r"([가-힣A-Za-z]{2,10})\s*(?:교수|교수님|Professor)\b", text)
        if m:
            prof = m.group(1).strip()
        else:
            # 영문 Professor Name 패턴: Professor John Doe
            m2 = re.search(r"Professor\s+([A-Za-z][A-Za-z .'-]{1,40})", text)
            if m2:
                prof = m2.group(1).strip()

        if not prof:
            # 키워드 교차검증: 사용자 문장에 실제로 등장하는 2~6자 한글 토큰 우선
            def is_korean_name(tok: str) -> bool:
                return 2 <= len(tok) <= 6 and all('가' <= ch <= '힣' for ch in tok)
            for k in keywords:
                if is_korean_name(k) and k in text:
                    prof = k
                    break

        if prof:
            entities['professor'] = prof

        # 2) 과목명/코드 후보
        course = ""
        # 과목 코드 패턴 우선 (예: CS101, CSED123)
        code_match = re.search(r"\b[A-Z]{2,4}\d{3}\b", text)
        if code_match:
            course = code_match.group(0)
        else:
            # 키워드 중 사용자 문장에 등장하고 일반어/교수명 제외, 공백 포함 우선
            GENERIC = ('교수','교수님','학과','학부','전공','과목','강의','수업')
            # 교수명도 제외 (이미 추출된 교수명은 과목명이 될 수 없음)
            prof_name = prof if prof else ""
            candidates = [k for k in keywords if k in text and not any(g in k for g in GENERIC) and k != prof_name]
            # 공백 포함 우선, 길이 우선
            candidates.sort(key=lambda s: (0 if ' ' in s else 1, -len(s)))
            if candidates:
                course = candidates[0]

        if course:
            entities['course'] = course

        return entities

    def _check_entity_cache(self, session_id: str, user_message: str, analysis: Dict[str, Any]) -> str:
        if not self.conversation_memory:
            return ""
        ents = self._extract_entities(user_message, analysis)
        # 조합(prof+course) → 코스 → 교수 순으로 조회
        if 'professor' in ents and 'course' in ents:
            combo_key = f"{ents['professor']}|{ents['course']}"
            data = self.conversation_memory.get_entity(session_id, 'combos', combo_key)
            if data:
                logger.info(f"SESSION_CACHE_HIT: combo='{combo_key}'")
                return data if isinstance(data, str) else str(data)
        if 'course' in ents:
            data = self.conversation_memory.get_entity(session_id, 'courses', ents['course'])
            if data:
                logger.info(f"SESSION_CACHE_HIT: course='{ents['course']}'")
                return data if isinstance(data, str) else str(data)
        if 'professor' in ents:
            data = self.conversation_memory.get_entity(session_id, 'professors', ents['professor'])
            if data:
                logger.info(f"SESSION_CACHE_HIT: professor='{ents['professor']}'")
                return data if isinstance(data, str) else str(data)
        return ""

    def _maybe_store_entity_cache(self, session_id: str, user_message: str, analysis: Dict[str, Any], result_str: str) -> None:
        if not self.conversation_memory:
            return
        ents = self._extract_entities(user_message, analysis)
        # 간단히 원문 문자열을 캐시에 저장(추후 JSON 구조화 가능)
        if 'professor' in ents and 'course' in ents:
            combo_key = f"{ents['professor']}|{ents['course']}"
            self.conversation_memory.cache_entity(session_id, 'combos', combo_key, result_str)
            logger.info(f"SESSION_CACHE_STORE: combo='{combo_key}'")
        if 'course' in ents:
            self.conversation_memory.cache_entity(session_id, 'courses', ents['course'], result_str)
            logger.info(f"SESSION_CACHE_STORE: course='{ents['course']}'")
        if 'professor' in ents:
            self.conversation_memory.cache_entity(session_id, 'professors', ents['professor'], result_str)
            logger.info(f"SESSION_CACHE_STORE: professor='{ents['professor']}'")

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            "processor_type": "SqlProcessor",
            "cache_size": len(self.cache),
            "performance": {}  # self.# performance_tracker.get_performance_stats("sql_query")
        }

    def _extract_sql_queries(self, output: str) -> list:
        """SQL 쿼리 추출 (출력에서 SQL 구문 패턴 찾기)"""
        import re

        # SQL 패턴들
        sql_patterns = [
            r'SELECT\s+.*?(?=;|\n\n|\Z)',
            r'INSERT\s+.*?(?=;|\n\n|\Z)',
            r'UPDATE\s+.*?(?=;|\n\n|\Z)',
            r'DELETE\s+.*?(?=;|\n\n|\Z)',
            r'CREATE\s+.*?(?=;|\n\n|\Z)',
            r'DROP\s+.*?(?=;|\n\n|\Z)',
            r'ALTER\s+.*?(?=;|\n\n|\Z)'
        ]

        queries = []
        for pattern in sql_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE | re.DOTALL)
            queries.extend([match.strip() for match in matches if match.strip()])

        return queries
