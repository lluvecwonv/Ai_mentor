"""
간단한 결과 통합기 - OpenAI 호환 형식으로 변환
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResultIntegrator:
    """간단한 결과 통합기"""

    def integrate(self, results: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """결과를 OpenAI 형식으로 변환"""
        processing_type = results.get("processing_type", "unknown")
        logger.info(f"📋 ResultIntegrator 입력: processing_type={processing_type}, results_keys={list(results.keys())}")

        # processing_info에서도 확인
        if processing_type == "unknown" and "processing_info" in results:
            alt_type = results["processing_info"].get("processing_type", "unknown")
            logger.info(f"📋 processing_info에서 대체 타입 발견: {alt_type}")
            processing_type = alt_type
        
        # 학과 필터 세이프가드 적용
        if context and "department_filter" in context:
            dept_whitelist = set(context["department_filter"])
            if dept_whitelist:
                # 결과에서 학과 필터링 (문자열 결과인 경우)
                content = self._get_content(results, processing_type)
                if isinstance(content, str) and "과목들을 찾았습니다" in content:
                    # 벡터 검색 결과인 경우 추가 필터링
                    lines = content.split('\n')
                    filtered_lines = []
                    for line in lines:
                        if '**' in line and '**' in line:
                            # 과목명이 포함된 줄인 경우 학과 확인
                            dept_match = False
                            for dept in dept_whitelist:
                                if dept in line:
                                    dept_match = True
                                    break
                            if dept_match:
                                filtered_lines.append(line)
                        else:
                            filtered_lines.append(line)
                    content = '\n'.join(filtered_lines)
                    logger.info(f"[integrate] 학과 필터 적용: {len(dept_whitelist)}개 학과만 허용")
                results["final_result"] = content
        
        content = self._get_content(results, processing_type)
        
        # 상세 로그 출력
        logger.info(f"🔧 ResultIntegrator 시작: processing_type={processing_type}")
        logger.info(f"📥 입력 results 키: {list(results.keys()) if isinstance(results, dict) else type(results)}")
        logger.info(f"📤 생성된 content 타입: {type(content)}, 길이: {len(str(content)) if content else 0}")
        
        # content 미리보기
        if content and isinstance(content, str):
            # 교수명 표기 일관화: "교수: 김평" → "교수: 김평 교수" (이미 접미사가 있는 경우/정보 없음은 제외)
            try:
                import re
                lines = content.split('\n')
                normalized_lines = []
                professor_line_regex = re.compile(r"^(\s*-\s*교수:\s*)(.+?)\s*$")
                for line in lines:
                    m = professor_line_regex.match(line)
                    if m:
                        prefix, name = m.groups()
                        name_stripped = name.strip()
                        if (
                            name_stripped
                            and name_stripped not in ["정보없음", "정보 없음"]
                            and not (name_stripped.endswith("교수") or name_stripped.endswith("교수님"))
                        ):
                            line = f"{prefix}{name_stripped} 교수"
                    normalized_lines.append(line)
                content = "\n".join(normalized_lines)
            except Exception:
                pass

            if len(content) < 2000:
                logger.info(f"📄 Content 전체: {content}")
            else:
                preview = content[:2000] + "... (총 " + str(len(content)) + "자)"
                logger.info(f"📄 Content 전체: {preview}")
        
        try:
            logger.info(f"FINAL: 처리 유형={processing_type}, 콘텐츠 길이={len(content) if isinstance(content, str) else 'N/A'}")
        except Exception:
            pass

        # contexts 정보 추출 및 로그
        contexts = results.get("contexts", {})
        logger.info(f"🔗 ResultIntegrator contexts: {list(contexts.keys()) if contexts else 'None'}")

        # contexts 내용 확인
        if contexts:
            for ctx_type, ctx_data in contexts.items():
                ctx_size = len(str(ctx_data)) if ctx_data else 0
                logger.info(f"  - {ctx_type}: {ctx_size} 문자 ({bool(ctx_data)})")

        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "processing_info": {
                "processing_type": processing_type
            },
            "processing_type": processing_type,  # 추가 호환성
            "final_result": content,  # 추가 호환성
            "contexts": contexts
        }

    def _get_content(self, results: Dict[str, Any], processing_type: str) -> str:
        """처리 타입에 따른 콘텐츠 생성"""
        # 기본 처리 타입들
        if processing_type in ["llm_only", "tot", "default", "llm_fallback"]:
            return results.get("final_result", "응답을 생성할 수 없습니다.")

        # 특화 처리 타입들
        elif processing_type == "vector_focused":
            llm_result = results.get("final_result", "")
            return llm_result

        elif processing_type == "sql_focused":
            llm_result = results.get("final_result", "")
            # SQL 결과가 에러인 경우 LLM이 종합하도록 강제 실행
            if "Agent stopped due to max iterations" in llm_result or "SQL 쿼리 오류" in llm_result:
                logger.warning("SQL 결과가 실패했지만 LLM 종합을 강제 실행합니다")
                return "죄송합니다. 데이터베이스에서 정보를 가져오는 중에 문제가 발생했습니다. 다른 방법으로 도움을 드리겠습니다."
            return llm_result

        elif processing_type in ["mapping_focused", "curriculum_focused", "cache_only", "owner_hint_combo"]:
            return results.get("final_result", "처리 중 오류가 발생했습니다.")

        # 에러 처리 타입들
        elif processing_type == "error":
            error_msg = results.get("error", "알 수 없는 오류")
            final_result = results.get("final_result", "")
            if final_result:
                return final_result
            return f"죄송합니다. 처리 중 오류가 발생했습니다. ({error_msg})"

        elif processing_type == "error_fallback":
            return results.get("final_result", "일시적인 오류로 인해 기본 처리를 수행했습니다. 다시 시도해 주세요.")

        elif processing_type == "unknown_fallback":
            return results.get("final_result", "요청을 정확히 이해하지 못했지만 최선의 답변을 제공해드렸습니다.")

        # 알 수 없는 처리 타입 (최후 수단)
        else:
            final_result = results.get("final_result", "")
            if final_result:
                # final_result가 있으면 그것을 사용
                return final_result
            else:
                # final_result도 없으면 사용자 친화적 메시지 제공
                logger.warning(f"알 수 없는 처리 타입: {processing_type}")
                return "죄송합니다. 요청을 처리하는 중에 예상치 못한 문제가 발생했습니다. 다시 질문해 주시면 더 나은 답변을 드리겠습니다."

    def _create_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """폴백 응답 생성"""
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"처리 중 오류가 발생했습니다: {error_message}"
                },
                "finish_reason": "stop"
            }],
            "error": error_message,
            "processing_info": {
                "handler": "chain_manager_fallback",
                "processing_type": "error",
                "version": "4.0"
            }
        }
