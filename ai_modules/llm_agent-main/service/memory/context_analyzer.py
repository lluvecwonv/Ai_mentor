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
        """히스토리 사용 여부와 상세 활용 방식 분석"""
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

            # 프롬프트 로드 및 구성
            prompt = load_prompt('history_aware_query_analyzer').format(
                history_context=history_context,
                current_query=current_query
            )

            # LLM 호출
            response = await self.llm_handler.chat(prompt)

            # JSON 파싱 (더 강화된 파싱 사용)
            history_data = robust_json_parse(response)


            if history_data and isinstance(history_data, dict):
                if "history_usage" in history_data:
                    # 정상적인 JSON 파싱 성공
                    history_usage = history_data["history_usage"]
                    is_continuation = history_usage.get("reuse_previous", False)

                    result = {
                        "is_continuation": is_continuation,
                        "history_usage": history_usage
                    }

                            # 연속대화일 경우 질의 재구성 수행
                    if is_continuation:
                        reconstructed_query = await self._reconstruct_query(current_query, history_context)
                        result["reconstructed_query"] = reconstructed_query
                    else:
                        result["reconstructed_query"] = current_query

                    logger.info(f"🎯 히스토리 분석 완료: 연속대화={is_continuation}, 관계={history_usage.get('relationship', 'unknown')}")
                    return result
                
        except Exception as e:
            logger.error(f"❌ 히스토리 분석 실패: {e}")
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
        return " | ".join(formatted)
    

    async def _reconstruct_query(self, current_query: str, history_context: str) -> str:
        # 질의 재구성 프롬프트 로드
        reconstruction_prompt = load_prompt('query_reconstruction').format(
            history_context=history_context,
            current_query=current_query
        )

        reconstructed = await self.llm_handler.chat(reconstruction_prompt)
        reconstructed = reconstructed.strip()

        logger.info(f"🔧 질의 재구성: '{current_query}' → '{reconstructed}'")
        return reconstructed
