"""
Vector Search Handler for FAISS-based course search via HTTP
"""

import httpx
import asyncio
from .base_handler import BaseQueryHandler
from config.settings import settings
from typing import Dict, Any, Optional

class VectorSearchHandler(BaseQueryHandler):
    """FAISS 벡터 검색 에이전트 - 전북대학교 과목 검색 전용

    이 에이전트는 다음 기능을 수행합니다:
    - 과목명, 과목 내용, 설명을 기반으로 한 의미적 검색
    - 학과 필터링과 결합된 과목 검색 (SQL 사전 필터링 지원)
    - 교수명, 강의실, 시간표 등 과목 상세 정보 제공

    주요 사용 사례:
    - "인공지능 관련 수업 찾아줘"
    - "머신러닝 과목 추천해줘"
    - "컴공에서 프로그래밍 수업"
    - "데이터사이언스 관련 강의"
    """

    def __init__(self):
        super().__init__()
        # httpx 클라이언트 설정
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
        transport = httpx.AsyncHTTPTransport(retries=2)
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=30.0),
            limits=limits,
            transport=transport,
            headers={"Connection": "keep-alive"}
        )
        # FAISS 검색 서비스 URL (LLM 기반 SQL 사전 필터링 포함)
        self.faiss_service_url = f"{settings.search_service_url}-sql-filter"
        self._warmed_up: bool = False
        self._warmup_lock = asyncio.Lock()

    async def warmup(self) -> None:
        """Vector 서비스에 가벼운 요청을 보내 커넥션/서비스를 예열합니다."""
        if self._warmed_up:
            return
        async with self._warmup_lock:
            if self._warmed_up:
                return
            try:
                self.logger.info("🔥 Vector Search 핸들러 워밍업 시작")
                payload = {"query": "테스트", "count": 1}

                response = await self.http_client.post(self.faiss_service_url, json=payload)

                if response.status_code == 200:
                    self.logger.info("✅ Vector Search 핸들러 워밍업 완료")
                else:
                    self.logger.warning(f"Vector Search 워밍업 응답 오류: status={response.status_code}")

                self._warmed_up = True

            except Exception as e:
                # 워밍업 실패는 치명적이지 않음
                self.logger.warning(f"Vector Search 워밍업 중 경고: {e}")

    def is_available(self) -> bool:
        """Check if vector search service is available"""
        return self.http_client is not None

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """Handle vector search query via HTTP"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🔍 FAISS 벡터 검색 에이전트 처리 시작")
        self.logger.info(f"📥 사용자 질문: {user_message}")
        self.logger.info(f"📊 쿼리 분석 데이터: {query_analysis}")
        self.logger.info(f"🔧 추가 인자: {kwargs}")

        if not self.is_available():
            self.logger.error("❌ 벡터 검색 서비스를 사용할 수 없음")
            return self.get_fallback_message()

        try:
            # 워밍업이 아직 안된 경우, 먼저 워밍업 실행
            if not self._warmed_up:
                self.logger.info("🔥 벡터 검색 서비스 워밍업 실행")
                await self.warmup()

            # 기본 쿼리 텍스트: 사용자 원문
            query_text = user_message
            self.logger.info(f"📝 기본 쿼리 텍스트: '{query_text}'")

            # 교수명 추출 (전체 스코프에서 사용)
            import re
            professor_pattern = r'([가-힣]{2,4})\s*교수'
            prof_matches = re.findall(professor_pattern, user_message)
            if prof_matches:
                self.logger.info(f"👨‍🏫 교수명 추출: {prof_matches}")
            else:
                self.logger.info("👨‍🏫 교수명 없음")

            # 확장 쿼리를 연결된 단일 쿼리로 변환
            expanded_queries = query_analysis.get('expanded_queries') if isinstance(query_analysis, dict) else None
            self.logger.info(f"🔍 확장 쿼리 분석 결과: {expanded_queries}")

            # 연결된 쿼리 텍스트 생성
            concatenated_query = query_text
            keywords_used = []

            if expanded_queries:
                self.logger.info(f"🔗 확장 쿼리를 연결된 단일 쿼리로 변환: {len(expanded_queries)}개 쿼리")

                # base 쿼리 제외하고 키워드들만 추출
                for eq in expanded_queries:
                    kind = eq.get('kind', 'unknown')
                    text = eq.get('text', '').strip()

                    if kind != 'base' and text and text not in concatenated_query:
                        keywords_used.append(text)
                        self.logger.info(f"  📝 키워드 추가: '{text}' (종류: {kind})")

                # 기본 쿼리에 키워드들을 연결
                if keywords_used:
                    concatenated_query = f"{query_text} {' '.join(keywords_used)}"
                    self.logger.info(f"✅ 연결된 쿼리 생성: '{concatenated_query}'")

            else:
                self.logger.info("🔄 확장 쿼리 생성 - expansion_keywords 기반")
                # fallback: expansion_keywords로 간단 생성
                kw_raw = str(query_analysis.get('expansion_keywords', '') or '') if isinstance(query_analysis, dict) else ''
                kws = [k.strip() for k in kw_raw.split(',') if k.strip()]
                self.logger.info(f"📋 추출된 키워드: {kws}")

                # 교수명을 키워드에 추가
                if prof_matches:
                    for prof_name in prof_matches:
                        if prof_name not in kws:
                            kws.append(prof_name)
                            self.logger.info(f"교수명 키워드 추가: {prof_name}")

                if kws:
                    # 키워드들을 기본 쿼리에 연결
                    concatenated_query = f"{query_text} {' '.join(kws)}"
                    keywords_used = kws
                    self.logger.info(f"✅ fallback 연결된 쿼리 생성: '{concatenated_query}'")

            # 최종 쿼리 텍스트 업데이트
            if concatenated_query != query_text:
                query_text = concatenated_query
                self.logger.info(f"🔗 최종 쿼리: '{query_text}' (키워드 {len(keywords_used)}개 연결)")
            else:
                self.logger.info("🔍 단일 쿼리 검색 실행 (연결할 키워드 없음)")

            # expanded_queries를 None으로 설정하여 단일 쿼리 검색 강제
            expanded_queries = None

            # 학과 힌트: 분석 단계에서 주입된 dept_hint 우선 사용
            dept_hint = query_analysis.get('dept_hint', '') if isinstance(query_analysis, dict) else ''
            self.logger.info(f"🏫 학과 힌트: '{dept_hint}'")

            # 학과 매핑이 실행되었는지 확인하고 상위 2개 학과 추출
            mapping_context = kwargs.get('mapping_context', '') if isinstance(kwargs, dict) else ''
            selected_departments = []

            # previous_results에서 학과 매핑 결과 확인
            previous_results = kwargs.get('previous_results', {}) if isinstance(kwargs, dict) else {}
            if previous_results and 'step_1' in previous_results:
                step1_result = previous_results['step_1']
                if isinstance(step1_result, dict) and 'result' in step1_result:
                    mapping_context = step1_result['result']
                    self.logger.info(f"🔍 previous_results에서 학과 매핑 결과 발견")

            self.logger.info(f"🗺️ 학과 매핑 컨텍스트 존재: {bool(mapping_context)}")
            if mapping_context:
                self.logger.info(f"📄 매핑 컨텍스트 내용: {mapping_context[:200]}...")

            # 학과 매핑이 실행되었는지 확인
            if mapping_context and '가장 유사한 학과' in mapping_context:
                self.logger.info("🎯 학과 매핑 에이전트 실행됨 - 매핑된 학과만 엄격 필터링")
                try:
                    import re
                    # "가장 유사한 학과: XXX" 패턴에서 학과명 추출
                    best_match = re.search(r"가장 유사한 학과:\s*([^\n]+)", mapping_context)
                    if best_match:
                        best_dept = best_match.group(1).strip()
                        selected_departments.append(best_dept)
                        self.logger.info(f"🥇 매핑된 학과: {best_dept}")

                    # 사용자가 특정 학과를 명시한 경우, 해당 학과만 엄격하게 필터링
                    # "다른 후보들"은 포함하지 않음 (컴공 = 컴퓨터인공지능학부만)
                    self.logger.info(f"✅ 엄격 학과 필터링: {selected_departments} (다른 학과 제외)")
                except Exception as e:
                    self.logger.error(f"❌ 학과 매핑 컨텍스트 파싱 실패: {e}")
            else:
                self.logger.info("🌐 학과 매핑 에이전트 미실행 - 전체 학과에서 검색")

            # 학과 힌트가 있으면 추가
            if dept_hint and dept_hint not in selected_departments:
                selected_departments.append(dept_hint)
                self.logger.info(f"➕ 학과 힌트 추가: {dept_hint}")

            self.logger.info(f"🎯 최종 학과 필터: {selected_departments if selected_departments else '전체 학과'}")

            # HTTP API 호출로 Vector Search 서비스 호출
            self.logger.info("🌐 FAISS 벡터 검색 서비스 HTTP 호출 준비")
            try:
                # 교수명이 포함된 경우 더 많은 결과 검색
                search_count = 50 if prof_matches else 30
                self.logger.info(f"📊 검색 결과 수: {search_count} (교수명 기반 조정: {bool(prof_matches)})")

                # API 요청 페이로드 구성 (연결된 단일 쿼리 사용)
                payload = {
                    "query": query_text,
                    "count": search_count,
                    "department_filter": selected_departments if selected_departments else None,
                    "expanded_queries": None,  # 연결된 단일 쿼리로 변경했으므로 None
                    "debug": True,
                    "keywords": keywords_used if keywords_used else None  # 키워드 정보는 디버깅용으로 전달
                }

                self.logger.info(f"📦 FAISS 서비스 요청 페이로드:")
                self.logger.info(f"  🔍 연결된 쿼리: {payload['query']}")
                self.logger.info(f"  📊 결과 수: {payload['count']}")
                self.logger.info(f"  🏫 학과 필터: {payload['department_filter']}")
                self.logger.info(f"  🔄 검색 방식: 단일 쿼리 (연결된 키워드: {len(keywords_used) if keywords_used else 0}개)")
                self.logger.info(f"  🐛 디버그 모드: {payload['debug']}")
                if keywords_used:
                    self.logger.info(f"  📋 연결된 키워드: {keywords_used}")

                # HTTP 요청 전송 (SQL 사전 필터링 포함)
                self.logger.info(f"🌐 HTTP 요청 전송: POST {self.faiss_service_url}")
                self.logger.info("🎯 SQL 사전 필터링 활성화됨 - FAISS 서비스에서 LLM 기반 SQL 생성 수행")
                self.logger.info("💡 FAISS 서비스에서 수행될 작업:")
                self.logger.info("   1️⃣ 쿼리 분석 및 SQL 조건 추출")
                self.logger.info("   2️⃣ LLM을 통한 SQL WHERE 절 생성")
                self.logger.info("   3️⃣ 데이터베이스에서 관련 과목 사전 필터링")
                self.logger.info("   4️⃣ 필터링된 과목들에 대해 벡터 유사도 계산")
                response = await self.http_client.post(self.faiss_service_url, json=payload)
                self.logger.info(f"📡 HTTP 응답 수신: {response.status_code}")

                if response.status_code == 200:
                    response_data = response.json()
                    self.logger.info(f"🔍 응답 타입: {type(response_data)}, 내용: {str(response_data)[:200]}")

                    # 응답이 dict 형태면 results 키에서 추출
                    if isinstance(response_data, dict):
                        results = response_data.get('results', [])
                        self.logger.info(f"📦 딕셔너리 응답에서 결과 추출: {len(results)}개 항목")

                        # SQL 정보가 있으면 로깅
                        if 'sql_info' in response_data:
                            sql_info = response_data['sql_info']
                            self.logger.info("🛠️ SQL 쿼리 생성 정보:")
                            if sql_info.get('generated_sql'):
                                self.logger.info(f"   📝 생성된 SQL: {sql_info.get('generated_sql')}")
                                self.logger.info("✅ SQL 쿼리 실행됨 - FAISS 서비스에서 LLM 기반 SQL 생성 및 실행 완료")
                            if sql_info.get('filtered_count') is not None:
                                self.logger.info(f"   🎯 SQL 필터링 결과: {sql_info.get('filtered_count')}개 과목")
                            if sql_info.get('total_courses'):
                                self.logger.info(f"   📊 전체 과목 수: {sql_info.get('total_courses')}개")
                        else:
                            # SQL 정보가 없는 경우에도 SQL이 실행되었는지 결과를 통해 분석
                            if results and len(results) > 0:
                                # 결과가 있으면 SQL 사전 필터링이 작동했을 가능성이 높음
                                self.logger.info("💡 SQL 실행 여부 분석: 검색 결과 존재 → SQL 사전 필터링 정상 작동")
                            else:
                                self.logger.warning("⚠️ SQL 실행 여부 분석: 검색 결과 없음 → SQL 필터링 확인 필요")
                    elif isinstance(response_data, list):
                        results = response_data
                        self.logger.info(f"📋 리스트 응답 직접 사용: {len(results)}개 항목")
                    elif isinstance(response_data, str):
                        self.logger.error(f"❌ 예상치 못한 문자열 응답: {response_data}")
                        results = []
                    else:
                        self.logger.error(f"❌ 예상치 못한 응답 형태: {type(response_data)}")
                        results = []

                    self.logger.info(f"✅ 벡터 검색 성공: {len(results)}개 결과")

                    # 결과 상세 분석
                    if results and isinstance(results, list):
                        similarities = [r.get('similarity_score', 0.0) if isinstance(r, dict) else 0.0 for r in results]
                        max_sim = max(similarities) if similarities else 0.0
                        min_sim = min(similarities) if similarities else 0.0
                        avg_sim = sum(similarities) / len(similarities) if similarities else 0.0

                        self.logger.info(f"📈 유사도 통계: 최대={max_sim:.3f}, 최소={min_sim:.3f}, 평균={avg_sim:.3f}")

                        # 상위 3개 결과 상세 로깅
                        self.logger.info("🔍 상위 3개 검색 결과 상세:")
                        for i, r in enumerate(results[:3]):
                            if isinstance(r, dict):
                                name = r.get('name', '알수없음')
                                dept = r.get('department_full_name', r.get('department', '알수없음'))
                                score = r.get('similarity_score', 0.0)
                                prof = r.get('professor', '정보없음')
                                self.logger.info(f"   {i+1}. {name} (학과: {dept}, 교수: {prof}, 점수: {score:.3f})")

                        departments = [r.get('department_full_name', '알수없음') if isinstance(r, dict) else '알수없음' for r in results[:5]]
                        dept_counts = {}
                        for dept in departments:
                            dept_counts[dept] = dept_counts.get(dept, 0) + 1
                        self.logger.info(f"🏫 상위 5개 결과 학과 분포: {dept_counts}")
                else:
                    self.logger.error(f"❌ Vector Search API 오류: status={response.status_code}")
                    try:
                        error_detail = response.text
                        self.logger.error(f"❌ 오류 상세: {error_detail[:200]}...")
                    except:
                        pass
                    return f"벡터 검색 서비스 오류: {response.status_code}"

            except Exception as e:
                self.logger.error(f"❌ Vector Search HTTP 호출 실패: {e}")
                import traceback
                self.logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
                return f"벡터 검색 중 오류가 발생했습니다: {str(e)}"

            if results and len(results) > 0:
                self.logger.info(f"📋 결과 포맷팅 시작: {len(results)}개 결과 → 전체 표시")
                formatted_content = f"'{user_message}'와 관련된 과목들을 찾았습니다:\n\n"

                # 모든 결과 포맷팅
                for i, item in enumerate(results):
                    name = item.get('name', '알 수 없음')
                    dept = item.get('department_full_name', item.get('department', '알 수 없음'))
                    desc = item.get('gpt_description', '설명 없음')
                    similarity = item.get('similarity_score', 0.0)

                    # SQL 메타데이터 추출
                    professor = item.get('professor', '정보없음')
                    credits = item.get('credits', 0)
                    course_code = item.get('course_code', '')
                    prerequisite = item.get('prerequisite', '없음')
                    target_grade = item.get('target_grade', '')
                    schedule = item.get('schedule', '정보없음')
                    location = item.get('location', '정보없음')
                    delivery_mode = item.get('delivery_mode', '정보없음')

                    formatted_content += f"{i+1}. **{name}**\n"
                    formatted_content += f"   - 학과: {dept}\n"
                    formatted_content += f"   - 교수: {professor}\n"
                    if location != '정보없음':
                        formatted_content += f"   - 강의실: {location}\n"
                    if schedule != '정보없음':
                        formatted_content += f"   - 시간표: {schedule}\n"
                    formatted_content += f"   - 학점: {credits}학점\n"
                    if course_code:
                        formatted_content += f"   - 과목코드: {course_code}\n"
                    formatted_content += f"   - 선수과목: {prerequisite}\n"
                    if target_grade:
                        formatted_content += f"   - 대상학년: {target_grade}\n"
                    if delivery_mode != '정보없음':
                        formatted_content += f"   - 수업방식: {delivery_mode}\n"
                    formatted_content += f"   - 유사도: {similarity:.3f}\n"
                    formatted_content += f"   - 설명: {desc[:200]}...\n\n"

                # 학과 필터 정보 추가
                if selected_departments and mapping_context and '가장 유사한 학과' in mapping_context:
                    dept_list = ", ".join(selected_departments)
                    formatted_content += f"(참고: 학과 매핑 결과 '{dept_list}' 학과에서 검색한 결과입니다)\n\n"
                    self.logger.info(f"🎯 학과 매핑 기반 필터링 적용: {dept_list}")
                elif dept_hint:
                    formatted_content += f"(참고: '{dept_hint}' 관련 결과를 우선 표기했습니다)\n\n"
                    self.logger.info(f"💡 학과 힌트 기반 필터링: {dept_hint}")


                self.logger.info(f"✅ FAISS 벡터 검색 완료: {len(results)}개 결과 반환")
                self.logger.info("="*60)
                return formatted_content
            else:
                self.logger.warning(f"⚠️ 검색 결과 없음: '{user_message}'")
                self.logger.info("="*60)
                return f"'{user_message}'와 관련된 과목을 찾지 못했습니다."

        except Exception as e:
            self.logger.error(f"❌ Vector Search 전체 처리 실패: {e}")
            import traceback
            self.logger.error(f"❌ 전체 스택 트레이스: {traceback.format_exc()}")
            self.logger.info("="*60)
            return f"검색 중 오류가 발생했습니다: {str(e)}"

    def get_fallback_message(self) -> str:
        return "벡터 검색 서비스를 사용할 수 없습니다."

    async def search(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """
        Legacy compatibility method that calls handle()

        This method exists for backward compatibility with code that might
        still be calling the old .search() method instead of .handle()
        """
        return await self.handle(user_message, query_analysis, **kwargs)

    # 더 이상의 학과 추출은 상위 라우터/프로세서에서 수행
