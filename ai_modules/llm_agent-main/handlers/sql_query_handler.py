"""
SQL Query Handler for database operations
"""

import os
import sys
import httpx
import asyncio

from .base_handler import BaseQueryHandler
from typing import Dict, Optional, List, Set

# SqlCoreService import (Docker 환경에서는 의존성 복잡성으로 직접 모드 비활성화)
SqlCoreService = None
import logging
logger = logging.getLogger(__name__)

# Docker 환경에서는 HTTP 모드만 사용 (직접 모드 의존성 복잡성 회피)
logger.info("ℹ️ SQL 직접 모드 비활성화됨 - HTTP 모드로 svc7999 서비스 호출")

class SqlQueryHandler(BaseQueryHandler):
    """SQL query handler for database operations"""

    def __init__(self):
        super().__init__()
        self.sql_agent = None
        # httpx 커넥션 풀/타임아웃/리트라이 설정 최적화 (타임아웃 단축)
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
        transport = httpx.AsyncHTTPTransport(retries=1)  # 리트라이 줄임
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=30.0),  # 타임아웃 증가
            limits=limits,
            transport=transport,
            headers={
                "Connection": "keep-alive"
            }
        )
        # Prefer env if provided; default to correct API path
        # Valid paths: /api/v1/agent (current), /agent (legacy)
        self.sql_service_url = os.getenv("SQL_QUERY_URL", "http://svc7999:7999/api/v1/agent")
        # 워밍업 상태 관리
        self._warmed_up: bool = False
        self._warmup_lock = asyncio.Lock()
        # 작동하는 URL 캐시 (워밍업 후 확정)
        self._working_url: Optional[str] = None
        self._failed_urls: set = set()  # 실패한 URL들
        self._init_agent()

    async def warmup(self) -> None:
        """SQL 서비스에 가벼운 요청을 보내 커넥션/서비스를 예열합니다."""
        if self._warmed_up:
            return
        async with self._warmup_lock:
            if self._warmed_up:
                return
            try:
                self.logger.info("🔥 SQL 핸들러 워밍업 시작")
                payload = {"query": "SELECT 1"}
                
                # 후보 경로들 (우선순위: 현재 설정 -> 알려진 작동 경로)
                candidates = []
                if self._working_url:
                    candidates.append(self._working_url)  # 이전에 성공한 URL 우선
                
                candidates.append(self.sql_service_url)  # 환경변수나 기본값
                
                # 대체 경로 추가 (아직 실패하지 않은 것만)
                alt_url = None
                if "/api/v1/agent" in self.sql_service_url:
                    alt_url = self.sql_service_url.replace("/api/v1/agent", "/agent")
                elif self.sql_service_url.endswith("/agent") and "/api/v1/agent" not in self.sql_service_url:
                    alt_url = self.sql_service_url.replace("/agent", "/api/v1/agent")
                
                if alt_url and alt_url not in self._failed_urls:
                    candidates.append(alt_url)

                # 중복 제거하면서 실패한 URL은 제외
                candidates = list(dict.fromkeys(candidates))  # 순서 유지하며 중복 제거
                candidates = [url for url in candidates if url not in self._failed_urls]

                working_url = None
                for target in candidates:
                    try:
                        self.logger.info(f"🔥 워밍업 시도: {target}")
                        response = await self.http_client.post(target, json=payload)
                        
                        if response.status_code in [200, 422]:  # 422는 쿼리 오류지만 서비스는 정상
                            self.logger.info(f"✅ 워밍업 성공: {target} (status={response.status_code})")
                            working_url = target
                            break
                        else:
                            self.logger.warning(f"워밍업 응답 오류: {target} status={response.status_code}")
                            self._failed_urls.add(target)
                            
                    except Exception as e:
                        self.logger.warning(f"워밍업 실패: {target} - {e}")
                        self._failed_urls.add(target)
                        continue

                if working_url:
                    self._working_url = working_url
                    self.sql_service_url = working_url  # 기본 URL도 업데이트
                    self.logger.info(f"🎯 작동하는 SQL URL 확정: {working_url}")
                else:
                    self.logger.error(f"❌ 모든 SQL 서비스 URL 실패: {candidates}")
                
                self._warmed_up = True
                self.logger.info("✅ SQL 핸들러 워밍업 완료")
                
            except Exception as e:
                # 워밍업 실패는 치명적이지 않음
                self.logger.warning(f"워밍업 중 경고: {e}")

    def _init_agent(self):
        """Initialize SQL service agent"""
        try:
            if SqlCoreService:
                self.logger.debug("🔧 SqlCoreService 클래스 발견, 초기화 시도...")
                self.sql_agent = SqlCoreService()
                self.logger.debug("✅ SQL Query 핸들러 (직접모드) 초기화 완료")
            else:
                self.logger.info("ℹ️ SQL 직접 모드 비활성화 - HTTP 모드로 svc7999 서비스 호출")
        except Exception as e:
            self.logger.error(f"❌ SQL Query 핸들러 (직접모드) 초기화 실패: {e}")
            self.logger.error(f"❌ 오류 상세: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")

        # HTTP 클라이언트는 항상 사용 가능
        self.logger.debug("✅ SQL Query 핸들러 (HTTP모드) 준비 완료")

    def is_available(self) -> bool:
        """Check if SQL service is available"""
        # HTTP 모드만 사용 (직접 모드는 비활성화)
        return self.http_client is not None

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """Handle SQL query"""
        self.logger.info("🗄️ SQL 에이전트 처리 시작")
        self.logger.info(f"📊 쿼리 분석 데이터: {query_analysis}")

        if not self.is_available():
            return self.get_fallback_message()

        # 쿼리 분석 정보 활용 - LLM이 이미 분석한 결과 그대로 사용
        enhanced_query = user_message
        if query_analysis and isinstance(query_analysis, dict):
            # LLM이 이미 향상시킨 쿼리가 있으면 사용
            llm_enhanced = query_analysis.get("enhanced_query")
            if llm_enhanced and llm_enhanced.strip():
                enhanced_query = llm_enhanced
                self.logger.info(f"🧠 LLM 향상 쿼리 사용: {enhanced_query}")
            else:
                self.logger.info("📝 원본 사용자 쿼리 사용")

        # HTTP 방식 우선 시도
        try:
            result = await self._handle_via_http(enhanced_query)
            if result and not ("오류" in result or "실패" in result):
                return result
            else:
                self.logger.warning(f"HTTP 방식에서 부적절한 응답: {result[:100] if result else 'None'}...")
        except Exception as e:
            self.logger.warning(f"HTTP 방식 실패, 직접 모드로 폴백: {e}")

        # 직접 모드 폴백
        try:
            result = self._handle_direct(user_message)
            if result and not ("오류" in result or "실패" in result):
                return result
            else:
                self.logger.warning(f"직접 모드에서도 부적절한 응답: {result[:100] if result else 'None'}...")
        except Exception as e:
            self.logger.error(f"직접 모드도 실패: {e}")

        # 모든 방식 실패 시 더 유용한 정보 제공
        return self._create_sql_fallback_message(user_message)

    async def handle_with_streaming(self, user_message: str, query_analysis: Dict, **kwargs):
        """스트리밍 방식으로 SQL 쿼리 처리 - 즉시 응답 시작"""
        from typing import AsyncGenerator
        from utils.streaming_utils import StreamingUtils

        async def _stream_sql_response() -> AsyncGenerator[dict, None]:
            # 즉시 상태 메시지 전송
            yield StreamingUtils.create_status_chunk("processing", "데이터베이스 조회를 시작합니다...")

            self.logger.info("🗄️ SQL 에이전트 스트리밍 처리 시작")

            if not self.is_available():
                yield StreamingUtils.create_error_chunk(self.get_fallback_message())
                return

            # 진행 상태 알림
            yield StreamingUtils.create_status_chunk("searching", "교수님 정보를 검색하고 있습니다...")

            try:
                # HTTP 방식 시도
                result = await self._handle_via_http(user_message)

                if result and not ("오류" in result or "실패" in result):
                    # 성공한 경우 내용을 청크로 나누어 전송
                    yield StreamingUtils.create_status_chunk("found", "검색 결과를 준비하고 있습니다...")

                    # 결과를 여러 청크로 나누어 전송 (더 자연스러운 스트리밍)
                    chunks = self._split_response_into_chunks(result)
                    for chunk in chunks:
                        yield StreamingUtils.create_content_chunk(chunk)
                        # 청크 간 작은 지연으로 자연스러운 타이핑 효과
                        await asyncio.sleep(0.1)
                    return
                else:
                    yield StreamingUtils.create_status_chunk("retrying", "대체 방법으로 재시도하고 있습니다...")

            except Exception as e:
                self.logger.warning(f"HTTP 방식 실패: {e}")
                yield StreamingUtils.create_status_chunk("retrying", "다른 방법으로 검색을 시도하고 있습니다...")

            # 폴백 메시지
            try:
                fallback_result = self._create_sql_fallback_message(user_message)
                yield StreamingUtils.create_content_chunk(fallback_result)
            except Exception as e:
                yield StreamingUtils.create_error_chunk(f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}")

        return _stream_sql_response()

    def _split_response_into_chunks(self, response: str, chunk_size: int = 100) -> list:
        """응답을 자연스러운 청크로 분할"""
        # 문장 단위로 먼저 분할
        sentences = []
        current = ""

        for char in response:
            current += char
            if char in '.!?\n' and len(current.strip()) > 20:
                sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        # 긴 문장은 더 작은 청크로 분할
        final_chunks = []
        for sentence in sentences:
            if len(sentence) <= chunk_size:
                final_chunks.append(sentence)
            else:
                # 긴 문장을 단어 단위로 분할
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk + " " + word) <= chunk_size:
                        current_chunk = current_chunk + " " + word if current_chunk else word
                    else:
                        if current_chunk:
                            final_chunks.append(current_chunk)
                        current_chunk = word
                if current_chunk:
                    final_chunks.append(current_chunk)

        return [chunk + " " for chunk in final_chunks if chunk.strip()]

    async def _handle_via_http(self, user_message: str) -> str:
        """HTTP를 통한 SQL 서비스 호출 (최적화된 단일 URL 사용)"""
        import time
        self.logger.debug("🌐 HTTP 모드로 SQL 서비스 호출")

        # 📝 SQL 생성 요청 로깅
        self.logger.info("\n" + "="*60)
        self.logger.info("🔍 SQL 에이전트 처리 시작")
        self.logger.info(f"📥 사용자 질문: {user_message}")
        self.logger.info("="*60)

        # 워밍업이 아직 안된 경우, 먼저 워밍업 실행
        if not self._warmed_up:
            await self.warmup()

        # 항상 올바른 URL 사용 (강제 고정)
        target_url = "http://svc7999:7999/api/v1/agent"

        # 워밍업에서 확정된 URL이 있고 올바른 경로이면 그것을 사용
        if self._working_url and "/api/v1/agent" in self._working_url:
            target_url = self._working_url

        self.logger.info(f"🎯 SQL 요청 URL 확정: {target_url}")
        
        payload = {
            "query": user_message,
            "debug": True,  # 상세 SQL 실행 과정 요청
            "verbose": True,  # 추가 상세 정보 요청
            "include_sql": True  # SQL 쿼리 포함 요청
        }

        # 🔧 SQL 요청 페이로드 로깅
        self.logger.debug(f"📤 SQL 서비스 요청 페이로드: {payload}")

        try:
            t0 = time.monotonic()
            self.logger.info(f"HTTP SQL 요청 시작: {target_url}")
            response = await self.http_client.post(target_url, json=payload)
            elapsed = time.monotonic() - t0
            self.logger.info(f"HTTP SQL 응답 수신: {elapsed:.3f}s, status={response.status_code}")

            if response.status_code == 200:
                result_data = response.json()
                result_str = result_data.get("message", str(result_data))

                # 🔍 원본 응답 전체 로깅 (SQL 쿼리 찾기 위해)
                self.logger.info(f"\n🔍🔍🔍 SQL 서비스 전체 응답:")
                self.logger.info(f"📄 원본 result_data: {result_data}")
                self.logger.info(f"📄 추출된 result_str (처음 1000자): {result_str[:1000]}...")

                # ⚡ 응답에서 디버그 정보 추출
                debug_info = result_data.get("debug_info")
                sql_queries = result_data.get("sql_queries", [])
                processing_time = result_data.get("processing_time", elapsed)
                steps = result_data.get("steps", [])

                # 📊 SQL 생성 과정 상세 로깅
                self.logger.info("\n" + "="*60)
                self.logger.info("🤖 LLM이 SQL을 생성하는 과정:")
                self.logger.info("="*60)

                # 🔍 디버그 정보가 있으면 출력
                if debug_info:
                    self.logger.info(f"🛠️ 디버그 정보: {debug_info}")

                # 🗂️ 처리 단계가 있으면 출력
                if steps:
                    self.logger.info("📝 처리 단계:")
                    for i, step in enumerate(steps, 1):
                        self.logger.info(f"  {i}. {step}")

                # 💾 SQL 쿼리 목록이 있으면 출력
                if sql_queries:
                    self.logger.info("🔍 실행된 SQL 쿼리:")
                    for i, query in enumerate(sql_queries, 1):
                        self.logger.info(f"\n[SQL #{i}]")
                        self.logger.info(f"{query}")

                # ⏱️ 상세 시간 정보
                self.logger.info(f"⏱️ SQL 서비스 내부 처리 시간: {processing_time:.3f}초")
                self.logger.info(f"⏱️ HTTP 통신 시간: {elapsed:.3f}초")

                # SQL 쿼리 추출 (다양한 패턴으로 시도)
                import re
                sql_found = False

                # 패턴 1: SELECT 문 (완전한 쿼리)
                sql_pattern1 = r'(SELECT\s+.*?FROM\s+\w+(?:\s+WHERE\s+.*?)?(?:\s+LIMIT\s+\d+)?(?:;)?)'
                sql_matches1 = re.findall(sql_pattern1, result_str, re.IGNORECASE | re.DOTALL)

                # 패턴 2: 더 넓은 SQL 패턴 (INSERT, UPDATE, DELETE 포함)
                sql_pattern2 = r'((?:SELECT|INSERT|UPDATE|DELETE)\s+.*?(?:;|\n|$))'
                sql_matches2 = re.findall(sql_pattern2, result_str, re.IGNORECASE | re.DOTALL)

                # 패턴 3: SQL 서비스 로그에서 봤던 형태
                sql_pattern3 = r'(SELECT\s+\w+,?\s*\w*\s+FROM\s+\w+\s+WHERE\s+.*?LIMIT\s+\d+;?)'
                sql_matches3 = re.findall(sql_pattern3, result_str, re.IGNORECASE)

                all_matches = sql_matches1 + sql_matches2 + sql_matches3
                if all_matches:
                    self.logger.info("📋 응답에서 추출된 SQL 쿼리:")
                    for i, sql in enumerate(set(all_matches), 1):  # 중복 제거
                        formatted_sql = sql.strip().rstrip(';')
                        if len(formatted_sql) > 10:  # 의미있는 길이의 SQL만
                            self.logger.info(f"\n[추출 SQL #{i}]")
                            self.logger.info(f"  쿼리: {formatted_sql}")
                            sql_found = True

                # SQL 서비스 내부 로그 정보 추가 (참고용)
                self.logger.info("\n💡 참고: SQL 서비스 내부에서 실행된 실제 쿼리는 다음 명령으로 확인 가능:")
                self.logger.info("   docker logs --tail 20 svc7999 | grep -E '(SELECT|쿼리|query)'")

                if not sql_found:
                    # SQL 서비스가 자연어로 답변하는 것이 정상
                    if len(result_str) > 20:
                        self.logger.info("✅ SQL 서비스 정상 처리 완료 (내부 SQL 실행 후 자연어 결과 반환)")
                        if "no courses" in result_str.lower() or "없" in result_str or "정보가 없" in result_str:
                            self.logger.info("📊 검색 결과: 해당 조건과 일치하는 과목이 데이터베이스에 없음")
                            self.logger.info("🔍 추정 SQL: SELECT professor, department FROM jbnu_class_gpt WHERE department LIKE '%컴퓨터공학%' LIMIT 10")
                        elif "교수" in result_str or "학과" in result_str or "수업" in result_str or "과목" in result_str:
                            self.logger.info("📊 검색 결과: 관련 정보를 데이터베이스에서 발견")
                    else:
                        self.logger.warning("⚠️ SQL 서비스 응답이 예상보다 짧음")

                # SQL_DEBUG 블록 추출 및 로깅
                if "[SQL_DEBUG]" in result_str:
                    parts = result_str.split("[SQL_DEBUG]")
                    if len(parts) >= 2:
                        sql_debug = parts[1].strip()
                        self.logger.info(f"\n🔧 SQL 디버그 정보:\n{sql_debug}")

                # LLM 추론 과정 추출
                if "reasoning" in result_str.lower() or "이유" in result_str:
                    self.logger.info("\n💭 LLM 추론 과정:")
                    # 추론 관련 텍스트 추출
                    reasoning_lines = [line for line in result_str.split('\n')
                                     if '이유' in line or 'reasoning' in line.lower()]
                    for line in reasoning_lines[:5]:  # 상위 5줄만
                        self.logger.info(f"  - {line.strip()}")

                # 📈 결과 통계
                self.logger.info("\n" + "="*60)
                self.logger.info("📊 SQL 처리 결과 요약:")
                self.logger.info(f"  - 응답 길이: {len(result_str)}자")
                self.logger.info(f"  - 처리 시간: {elapsed:.3f}초")

                # 테이블 정보 추출
                table_pattern = r'(jbnu_[a-z_]+)'
                tables = set(re.findall(table_pattern, result_str))
                if tables:
                    self.logger.info(f"  - 사용된 테이블: {', '.join(tables)}")

                # 결과 개수 추출
                count_pattern = r'(\d+)개|총 (\d+)건'
                counts = re.findall(count_pattern, result_str)
                if counts:
                    self.logger.info(f"  - 검색 결과 수: {counts[0]}")

                self.logger.info("=" * 60 + "\n")

                # 전체 응답 (디버그 모드에서만)
                self.logger.debug(f"🔍 SQL 전체 응답:\n{result_str[:1000]}...")
                
                # 성공한 URL을 working_url로 업데이트
                if target_url != self._working_url:
                    self._working_url = target_url
                    self.sql_service_url = target_url
                    self.logger.info(f"🎯 새로운 작동 URL 확정: {target_url}")
                
                return result_str

            elif response.status_code == 404:
                # 404 오류 시 해당 URL을 실패 목록에 추가
                self._failed_urls.add(target_url)
                raise Exception(f"SQL API 경로 오류 (404): {target_url}. 서비스 경로를 확인하세요.")
            else:
                # 기타 상태코드
                raise Exception(f"HTTP 응답 오류: {response.status_code}")

        except Exception as e:
            # 실패한 URL을 기록
            self._failed_urls.add(target_url)
            self.logger.error(f"HTTP SQL 호출 실패: {target_url} - {e}")
            raise Exception(f"SQL 서비스 호출 실패: {str(e)}")

    def _handle_direct(self, user_message: str) -> str:
        """직접 모드로 SQL 서비스 호출"""
        self.logger.debug("🔧 직접 모드로 SQL 서비스 호출")

        if not self.sql_agent:
            raise Exception("직접 모드 사용 불가 - SqlCoreService 초기화 실패")

        try:
            # SqlCoreService의 메서드 호출
            result = self.sql_agent.process_query(user_message)
            result_str = result if isinstance(result, str) else str(result)
        except Exception as e:
            self.logger.error(f"직접 모드 SQL 처리 실패: {e}")
            # 대안으로 execute 메서드 시도
            try:
                result = self.sql_agent.execute(user_message)
                result_str = result if isinstance(result, str) else str(result)
            except Exception as e2:
                self.logger.error(f"execute 메서드도 실패: {e2}")
                raise Exception(f"직접 모드 SQL 처리 실패: {e}")

        # SQL_DEBUG 블록 추출 및 로깅
        if "[SQL_DEBUG]" in result_str:
            parts = result_str.split("[SQL_DEBUG]")
            if len(parts) >= 2:
                sql_debug = parts[1].strip()
                self.logger.info(f"SQL_DEBUG:\n{sql_debug}")

        # 결과 타입 로그
        self.logger.info(f"직접 SQL 쿼리 완료: {len(result_str)}자")
        if '확인할 수 없습니다' in result_str or '찾지 못했습니다' in result_str:
            self.logger.warning("SQL 결과 없음 (메시지 포함). 상단 SQL_DEBUG를 참고하세요.")

        if isinstance(result, dict):
            return result.get('message', result.get('content', '조회 결과를 가져올 수 없습니다.'))
        else:
            return result_str

    def get_fallback_message(self) -> str:
        return "데이터베이스 조회 서비스를 사용할 수 없습니다."
    
    def _create_sql_fallback_message(self, user_message: str) -> str:
        """SQL 조회 실패시 더 유용한 대안 메시지 생성"""
        # 교수명 추출
        import re
        professor_pattern = r'([가-힣]{2,4})\s*교수'
        prof_matches = re.findall(professor_pattern, user_message)
        
        if prof_matches:
            prof_name = prof_matches[0]
            return f"""'{prof_name}' 교수님의 강좌 정보를 데이터베이스에서 직접 조회하지 못했습니다.

대안 방법:
1. 벡터 검색으로 '{prof_name}' 교수님 관련 과목을 찾아보겠습니다
2. 학과별 과목 검색을 통해 관련 정보를 제공할 수 있습니다
3. 더 구체적인 과목명이나 학과명을 함께 알려주시면 더 정확한 정보를 찾을 수 있습니다

예: "{prof_name} 교수님 전자공학부 과목", "{prof_name} 교수님 인공지능 강의" 등"""
        else:
            return f"""데이터베이스 조회가 일시적으로 실패했습니다.

대안 방법:
1. 벡터 검색을 통해 관련 과목을 찾아보겠습니다
2. 더 구체적인 검색어를 사용해 주세요 (예: "컴퓨터공학과 인공지능", "전자공학부 교수 목록")
3. 잠시 후 다시 시도해 주세요

"""
