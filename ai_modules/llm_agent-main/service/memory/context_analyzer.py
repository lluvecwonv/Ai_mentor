import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt
from utils.json_utils import extract_json_block, robust_json_parse

logger = logging.getLogger(__name__)

class ConversationContextAnalyzer:
    """대화 히스토리 분석 및 활용 방식 결정 분석기"""

    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    async def analyze_session_context(self, current_query: str, conversation_memory, session_id: str) -> Dict[str, Any]:
        """히스토리 분석 + 질의 재구성 통합 (1번의 LLM 호출)"""
        try:
            session_state = conversation_memory.get_state(session_id)
            history = session_state.get("conversation_history", [])

            if not history:
                return {
                    "is_continuation": False,
                    "reconstructed_query": current_query,
                    "history_usage": {
                        "reuse_previous": False,
                        "relationship": "new_search",
                        "context_integration": "히스토리가 없어 새로운 검색 수행"
                    }
                }

            # 히스토리 포맷팅
            history_context = self._format_history(history)

            # 통합 프롬프트 로드 및 구성 (히스토리 분석 + 질의 재구성)
            prompt = load_prompt('integrated_history_analyzer').format(
                history_context=history_context,
                current_query=current_query
            )

            logger.info(f"🚀 통합 분석 시작 (히스토리 분석 + 질의 재구성)")

            # 1번의 LLM 호출로 모든 것 처리
            response = await self.llm_handler.chat(prompt)

            # JSON 파싱
            analysis_data = robust_json_parse(response)

            if analysis_data and isinstance(analysis_data, dict):
                is_continuation = analysis_data.get("is_continuation", False)
                reconstructed_query = analysis_data.get("reconstructed_query", current_query)

                # 'None' 문자열이나 None이 반환되면 원본 쿼리 사용
                if not reconstructed_query or reconstructed_query == "None" or reconstructed_query.strip() == "":
                    reconstructed_query = current_query

                history_usage = analysis_data.get("history_usage", {
                    "reuse_previous": is_continuation,
                    "relationship": "continuation" if is_continuation else "new_search",
                    "context_integration": analysis_data.get("context_integration", "")
                })

                result = {
                    "is_continuation": is_continuation,
                    "reconstructed_query": reconstructed_query,
                    "history_usage": history_usage
                }

                logger.info(f"✅ 통합 분석 완료: 연속대화={is_continuation}, 재구성='{reconstructed_query}'")
                return result
            else:
                # 파싱 실패 시 기본값
                logger.warning("⚠️ JSON 파싱 실패, 기본값 반환")
                return {
                    "is_continuation": False,
                    "reconstructed_query": current_query,
                    "history_usage": {
                        "reuse_previous": False,
                        "relationship": "new_search",
                        "context_integration": "파싱 실패로 새로운 검색"
                    }
                }

        except Exception as e:
            logger.error(f"❌ 통합 분석 실패: {e}")
            # 예외 발생 시 폴백 - 기본값 반환
            return {
                "is_continuation": False,
                "reconstructed_query": current_query,
                "history_usage": {
                    "reuse_previous": False,
                    "relationship": "new_search",
                    "context_integration": f"분석 오류로 새로운 검색: {str(e)}"
                }
            }

    def _format_history(self, history):
        """히스토리 간단 포맷팅"""
        formatted = []
        for entry in history[-3:]:  # 최근 3턴만
            if entry.get("role") == "user":
                formatted.append(f"사용자: {entry.get('content', '')}")
            elif entry.get("role") == "assistant":
                formatted.append(f"AI: {entry.get('content', '')[:100]}...")
        return "\n".join(formatted)
