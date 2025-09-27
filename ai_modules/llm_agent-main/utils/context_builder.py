"""
컨텍스트 빌더 유틸리티 (통합)
SQL/벡터/분석 컨텍스트 문자열 생성 및 대화 히스토리 관리를 중앙집중화
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ContextBuilder:
    """컨텍스트 문자열 생성 유틸리티"""

    @staticmethod
    def build_combined_context(
        sql_context: str = "",
        vector_context: str = "",
        expansion_context: str = "",
        max_length: int = 2000
    ) -> str:
        """통합 컨텍스트 문자열 생성"""
        ctx_parts = []

        if sql_context:
            ctx_parts.append(f"이전 SQL 결과:\n{sql_context}")

        if vector_context:
            ctx_parts.append(f"이전 벡터 검색 결과:\n{vector_context}")

        if expansion_context:
            ctx_parts.append(f"분석 컨텍스트: {expansion_context}")

        combined = "\n\n".join(ctx_parts)

        # 길이 제한 (너무 길면 자르기)
        if len(combined) > max_length:
            combined = combined[:max_length] + "..."
            logger.debug(f"컨텍스트가 {max_length}자를 초과하여 잘림")

        return combined

    @staticmethod
    def build_contextual_prompt(
        conversation_history: List[Dict[str, Any]],
        search_results: Optional[List[Dict]] = None,
        current_topic: Optional[str] = None,
        current_query: str = "",
        max_turns: int = 3
    ) -> str:
        """맥락을 포함한 프롬프트 생성"""
        prompt_parts = [
            "다음은 사용자와의 대화 맥락입니다:",
            ""
        ]

        # 최근 대화 히스토리 추가
        recent_history = conversation_history[-(max_turns * 2):] if conversation_history else []
        if recent_history:
            prompt_parts.append("=== 최근 대화 ===")
            for msg in recent_history:
                role_kr = "사용자" if msg.get("role") == "user" else "AI멘토"
                content = msg.get("content", "")
                prompt_parts.append(f"{role_kr}: {content}")
            prompt_parts.append("")

        # 검색 결과 추가
        if search_results:
            prompt_parts.append("=== 최근 검색 결과 ===")
            for i, result in enumerate(search_results[:5], 1):
                name = result.get('name', result.get('과목명', ''))
                dept = result.get('department', result.get('학과', ''))
                if name:
                    prompt_parts.append(f"{i}. {name} ({dept})")
            prompt_parts.append("")

        # 현재 주제 추가
        if current_topic:
            prompt_parts.append(f"=== 현재 주제: {current_topic} ===")
            prompt_parts.append("")

        # 현재 질문
        if current_query:
            prompt_parts.extend([
                "=== 현재 사용자 질문 ===",
                current_query,
                "",
                "위 맥락을 고려하여 질문을 분석해주세요."
            ])

        return "\n".join(prompt_parts)

    @staticmethod
    def build_history_directive(user_message: str = "", mode: str = "auto", context_analysis: Dict = None) -> str:
        """히스토리 사용 정책을 LLM에 명확히 지시하는 시스템 프롬프트 생성

        Args:
            user_message: 현재 사용자 질문
            mode: 'auto' | 'ignore' | 'force'
            context_analysis: ConversationContextAnalyzer의 분석 결과
        """
        if mode == "ignore":
            return (
                "[히스토리 사용 규칙]\n"
                "- 이 요청은 이전 대화/검색/SQL 히스토리를 절대 사용하지 마십시오.\n"
                "- 현재 질문만으로 답변하고, 과거 맥락이나 추론을 섞지 마십시오.\n"
            )
        if mode == "force":
            return (
                "[히스토리 사용 규칙]\n"
                "- 이 요청은 최근 대화 히스토리를 적극 반영하여 일관성을 유지하십시오.\n"
                "- 다만 현재 질문과 직접 관련된 정보만 선별하여 사용하십시오.\n"
            )

        # auto mode - ConversationContextAnalyzer 결과 사용 가능
        if context_analysis:
            needs_history = context_analysis.get("needs_history", False)
            context_type = context_analysis.get("context_type", "independent")
            reasoning = context_analysis.get("reasoning", "")

            if needs_history:
                if context_type == "continuation":
                    return f"이전 대화의 연속선상에서 답변해주세요. (이유: {reasoning})"
                elif context_type == "reference":
                    return f"이전 대화 내용을 참고하여 답변해주세요. (이유: {reasoning})"
                else:
                    return f"이전 대화 맥락을 고려하여 답변해주세요. (이유: {reasoning})"
            else:
                return f"독립적인 질문으로 처리하여 답변해주세요. (이유: {reasoning})"

        # 기본 auto 모드
        return (
            "[히스토리 사용 규칙]\n"
            "- 아래 조건에 해당하면 최근 대화 히스토리를 참고하십시오: '그것/그거/이전/앞서/위 내용/방금/위 질문' 등\n"
            "  지시어나 대명사로 과거 발화를 명시적으로 참조하는 경우.\n"
            "- 위 조건에 해당하지 않으면 이전 히스토리를 사용하지 말고 현재 질문만으로 답하십시오.\n"
            "- 어떠한 경우에도 과거 주제와 현재 주제를 혼동하거나 혼합하지 마십시오.\n"
        )

    @staticmethod
    def extract_keywords_from_analysis(query_analysis: Dict[str, Any]) -> List[str]:
        """쿼리 분석에서 키워드 추출 - 다중 소스 지원"""
        keywords = []

        # 1. expansion_keywords에서 추출 (기존 방식)
        expansion_keywords = query_analysis.get('expansion_keywords', '')
        if expansion_keywords:
            expansion_list = [k.strip() for k in str(expansion_keywords).split(',') if k.strip()]
            keywords.extend(expansion_list)

        # 2. entities에서 키워드 추출
        entities = query_analysis.get('entities', {})
        if isinstance(entities, dict):
            for entity_value in entities.values():
                if entity_value and str(entity_value).strip():
                    keywords.append(str(entity_value).strip())

        # 3. category나 주제에서 키워드 추출
        category = query_analysis.get('category', '')
        if category and category.strip():
            keywords.append(category.strip())

        # 4. resolved_query나 원본 쿼리에서 주요 키워드 추출 (최후 수단)
        if not keywords:
            query_text = query_analysis.get('resolved_query') or query_analysis.get('original_query', '')
            if query_text:
                # 간단한 한국어 키워드 추출 (교수, 과목, 학과 등 중요 단어)
                import re
                key_patterns = [
                    r'교수(?:님)?', r'선생님', r'컴공', r'컴퓨터공학', r'전자공학', r'경영학',
                    r'강의', r'과목', r'수업', r'강좌', r'학점', r'커리큘럼', r'수강'
                ]
                for pattern in key_patterns:
                    matches = re.findall(pattern, query_text)
                    keywords.extend(matches)

        # 중복 제거 및 정리
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword and keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)

        return unique_keywords[:10]  # 최대 10개까지 제한

    @staticmethod
    def format_plan_display(plan: List[Dict[str, Any]], max_steps: int = 4) -> str:
        """플랜을 사용자 친화적으로 포맷"""
        if not plan:
            return ""

        try:
            def _display_agent(agent_hint: str) -> str:
                agent_mapping = {
                    'SQL_QUERY': 'SQL-Agent',
                    'FAISS_SEARCH': 'FAISS-Search-Agent',
                    'DEPARTMENT_MAPPING': 'Department-Mapping-Agent',
                    'CURRICULUM_PLAN': 'Curriculum-Agent',
                    'LLM_FALLBACK': 'LLM-Fallback-Agent',
                }
                return agent_mapping.get(agent_hint.upper(), agent_hint)

            plan_parts = []
            for step in plan[:max_steps]:
                step_num = step.get('step', '?')
                agent = _display_agent(str(step.get('agent', '')))
                goal = step.get('goal', '')
                goal_part = f"({goal})" if goal else ""
                plan_parts.append(f"{step_num}:{agent}{goal_part}")

            return "; ".join(plan_parts)
        except Exception:
            return str(plan)[:200]


    @staticmethod
    def build_context_prompt(
        user_message: str,
        contexts: Dict[str, str],
        directive: str = ""
    ) -> str:
        """컨텍스트 정보를 포함한 프롬프트 구성"""
        parts = []

        # 지시사항 추가
        if directive:
            parts.append(directive)
            parts.append("")

        # 컨텍스트 정보 추가
        if contexts:
            parts.append("=== 참고 정보 ===")

            for context_type, content in contexts.items():
                if content and content.strip():
                    parts.append(f"[{context_type.upper()}]")
                    parts.append(content.strip())
                    parts.append("")

            parts.append("=== 질문 ===")

        # 사용자 질문
        parts.append(user_message)

        return "\n".join(parts)

    @staticmethod
    def extract_conversation_context(
        conversation_history: List[Dict[str, str]],
        limit: int = 3
    ) -> str:
        """대화 히스토리에서 컨텍스트 추출"""
        if not conversation_history:
            return ""

        # 최근 대화만 선택
        recent_history = conversation_history[-limit:] if len(conversation_history) > limit else conversation_history

        context_parts = []
        for i, exchange in enumerate(recent_history, 1):
            user_msg = exchange.get('user_message', '').strip()
            ai_msg = exchange.get('assistant_message', '').strip()

            if user_msg:
                context_parts.append(f"대화 {i} - 사용자: {user_msg}")
            if ai_msg:
                context_parts.append(f"대화 {i} - AI: {ai_msg[:200]}...")  # AI 응답은 200자로 제한

        return "\n".join(context_parts) if context_parts else ""


def build_combined_context(*args, **kwargs) -> str:
    """편의 함수: ContextBuilder.build_combined_context의 단축형"""
    return ContextBuilder.build_combined_context(*args, **kwargs)
