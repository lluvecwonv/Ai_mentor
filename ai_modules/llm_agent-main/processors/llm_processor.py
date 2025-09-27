"""
LLM 처리기
- 컨텍스트 최적화
- 메시지 길이 관리
- 성능 추적
"""

import logging
from typing import Dict, Any, List
import json
from utils.json_utils import extract_json_block
from utils.context_builder import ContextBuilder
# LangGraph 전용 모드로 간소화

logger = logging.getLogger(__name__)

class LlmProcessor:
    """LLM 처리 전담 클래스"""

    def __init__(self, llm_handler, settings=None):
        self.llm_handler = llm_handler
        self.settings = settings
        # LangGraph 전용 모드로 간소화
        self.max_context_length = getattr(settings, 'max_message_length', 10000) if settings else 10000
        # Chat model direct reference (LangChain ChatOpenAI)
        self._chat_model = None
        try:
            # LlmClientLangChain 클래스에서 llm 속성을 직접 접근
            self._chat_model = getattr(self.llm_handler, "llm", None)
            if self._chat_model is None:
                logger.warning("Chat 모델 참조를 찾지 못해 기존 체인 폴백 경로 사용")
        except Exception as e:
            logger.warning(f"Chat 모델 초기화 실패(폴백 사용): {e}")
        logger.debug("LlmProcessor 초기화 완료")

    async def process(self, data: Dict[str, Any]) -> str:
        """LLM 처리"""
        # LangGraph 전용 모드로 간소화
        try:
            # LLM 핸들러가 None인 경우 처리
            if self.llm_handler is None:
                logger.warning("LLM 핸들러가 사용할 수 없습니다. 기본 응답을 반환합니다.")
                return "죄송합니다. 현재 AI 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
            
            user_message = data.get("user_message", "")
            ignore_history = bool(data.get("ignore_history", False))

            # 컨텍스트 수집 및 최적화
            contexts = self._collect_contexts(data)
            optimized_context = self._optimize_context(contexts, self.max_context_length)

            logger.debug(f"LLM 처리: 메시지={len(user_message)}자, 컨텍스트={len(optimized_context)}자")

            # LLM 처리 - LangGraph(세션 히스토리) 우선, 실패 시 기존 체인 폴백
            session_id = data.get("session_id", "default")
            result: str
            if self._chat_model is not None:
                try:
                    # LangGraph 스타일: RunnableWithMessageHistory 사용
                    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
                    from langchain_core.runnables import RunnableWithMessageHistory
                    from langchain.schema import HumanMessage, SystemMessage
                    from service.memory.memory import ConversationMemory

                    cm: ConversationMemory = data.get("conversation_memory")  # injected by service
                    if cm is None:
                        cm = ConversationMemory(max_history_length=10)

                    # 히스토리 전용 지시 프롬프트
                    history_directive = ContextBuilder.build_history_directive(user_message, mode=("ignore" if ignore_history else "auto"))

                    if ignore_history:
                        # 히스토리 완전 배제: 메시지 직접 호출
                        current: List[Any] = [SystemMessage(content=history_directive)]
                        if optimized_context:
                            current.append(SystemMessage(content=optimized_context))
                        current.append(HumanMessage(content=user_message))
                        ai_msg = self._chat_model.invoke(current)
                        result = getattr(ai_msg, "content", str(ai_msg))
                    else:
                        # 히스토리 허용: RunnableWithMessageHistory 사용
                        prompt = ChatPromptTemplate.from_messages([
                            MessagesPlaceholder(variable_name="messages")
                        ])
                        chain = prompt | self._chat_model

                        history = cm.get_history_adapter(session_id, max_turns=10)
                        runnable = RunnableWithMessageHistory(
                            chain,
                            lambda cfg: history,
                            input_messages_key="messages",
                        )

                        current: List[Any] = [SystemMessage(content=history_directive)]
                        if optimized_context:
                            current.append(SystemMessage(content=optimized_context))
                        current.append(HumanMessage(content=user_message))

                        ai_msg = runnable.invoke({"messages": current}, config={"configurable": {"session_id": session_id}})
                        result = getattr(ai_msg, "content", str(ai_msg))
                except Exception as _e:
                    logger.warning(f"Chat 모델 경로 실패, 체인 폴백 사용: {_e}")
                    result = await self._fallback_chain(user_message, optimized_context, data)
            else:
                result = await self._fallback_chain(user_message, optimized_context, data)

            result_str = str(result)
            logger.info(f"LLM 처리 완료: {len(result_str)}자")
            return result_str

        except Exception as e:
            logger.error(f"LLM 처리 실패: {e}")
            return f"AI 처리 중 오류가 발생했습니다: {str(e)}"

    async def _fallback_chain(self, user_message: str, optimized_context: str, data: Dict[str, Any]) -> str:
        """기존 LangChain 체인 경로 폴백"""
        if optimized_context:
            aug_user_message = user_message
            if 'tot_context' in data and data['tot_context']:
                aug_user_message = (
                    f"{user_message}\n\n요청: 위 중간 결과를 바탕으로 상위 5개 항목을 번호를 붙여 자세히 서술해 주세요."
                )

            # SQL 컨텍스트가 있으면 히스토리 없는 정확한 체인 사용
            if "sql_context" in data:
                return await self.llm_handler.run_chain("context_only", aug_user_message, context=optimized_context)
            else:
                return await self.llm_handler.run_chain("context", aug_user_message, context=optimized_context)
        else:
            return await self.llm_handler.run_chain("basic", user_message)

    def _collect_contexts(self, data: Dict[str, Any]) -> List[str]:
        """컨텍스트 수집"""
        contexts = []

        # 검색 컨텍스트
        if "search_context" in data:
            contexts.append(f"검색 결과: {data['search_context']}")

        # SQL 컨텍스트
        if "sql_context" in data:
            contexts.append(f"데이터 결과: {data['sql_context']}")

        # 통합 컨텍스트
        if "combined_context" in data:
            contexts.append(data["combined_context"])

        # 분석 컨텍스트
        combined_analysis = data.get("analysis", data.get("combined_analysis", {}))
        if combined_analysis:
            expansion_context = combined_analysis.get("expansion_context", "")
            if expansion_context:
                contexts.append(f"분석 컨텍스트: {expansion_context}")

        # ToT 결과 컨텍스트
        if "tot_context" in data and data["tot_context"]:
            contexts.append(f"중간 결과: {data['tot_context']}")

        return contexts

    def _optimize_context(self, contexts: List[str], max_length: int) -> str:
        """컨텍스트 최적화"""
        if not contexts:
            return ""

        # 모든 컨텍스트 합치기
        full_context = "\n\n".join(contexts)

        # 길이 제한 적용
        if len(full_context) <= max_length:
            return full_context

        # 길이 초과시 중요한 부분만 유지
        logger.warning(f"컨텍스트 길이 초과: {len(full_context)} > {max_length}, 자동 축약")

        # 각 컨텍스트를 균등하게 축약
        target_length_per_context = max_length // len(contexts)
        optimized_contexts = []

        for context in contexts:
            if len(context) <= target_length_per_context:
                optimized_contexts.append(context)
            else:
                # 앞부분과 뒷부분을 유지하는 방식
                half_length = target_length_per_context // 2
                truncated = context[:half_length] + "...(중략)..." + context[-half_length:]
                optimized_contexts.append(truncated)

        return "\n\n".join(optimized_contexts)

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            "processor_type": "LlmProcessor",
            "max_context_length": self.max_context_length,
            "performance": {}  # self.# performance_tracker.get_performance_stats("llm_process")
        }

    async def cache_adequacy_check(self, user_message: str, cache_summary: Dict[str, Any], combined_context: str = "") -> Dict[str, Any]:
        """캐시만으로 답변 가능한지 경량 판단(JSON)

        Returns dict with keys: can_answer(bool), rationale(str), needed_fields(list), targets(list), disambiguation_needed(bool)
        """
        prompt = f"""
        질문: {user_message}

        현재 캐시 정보(요약):
        {json.dumps(cache_summary, ensure_ascii=False)[:2000]}

        이전 결과(요약):
        {(combined_context or '')[:2000]}

        다음 JSON 스키마로만 답변하세요(다른 텍스트 금지):
        {{
            "can_answer": true|false,
            "rationale": "짧은 이유",
            "needed_fields": ["schedule","goal","room","credit","semester"],
            "targets": ["course:<과목명|코드>", "professor:<정확한이름>"] ,
            "disambiguation_needed": false
        }}

        엄격한 규칙:
        - targets는 오직 사용자 질문과 캐시 요약에서 직접 추출한 항목만 포함합니다.
        - 질문에 특정 교수명이 나오면 정확히 그 이름만 포함합니다. (예: "송현제" → "professor:송현제")
        - 예시 문구를 그대로 복사하지 마세요. 존재하지 않는 교수/과목명을 생성하지 마세요.
        - 확실하지 않으면 targets는 빈 배열([])로 둡니다.
        - 캐시에 없는 사실은 추측 금지 → can_answer=false
        """
        # 간단 호출: 컨텍스트 없이 기본 체인. (JSON 파싱은 별도 처리)
        result = await self.llm_handler.run_chain("basic", prompt)
        data = extract_json_block(result) or {}
        return {
            "can_answer": bool(data.get("can_answer", False)),
            "rationale": data.get("rationale", ""),
            "needed_fields": data.get("needed_fields", []),
            "targets": data.get("targets", []),
            "disambiguation_needed": bool(data.get("disambiguation_needed", False))
        }
