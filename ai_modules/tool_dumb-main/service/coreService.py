"""
LLM Fallback Core Service
시스템 안정성을 위한 폴백 에이전트 코어 서비스
"""

from util.llmClient import LlmClient
from typing import List
import logging

logger = logging.getLogger(__name__)

class CoreService:
    """폴백 에이전트 코어 서비스 - 기본적인 LLM 처리 및 폴백 기능 제공"""

    def __init__(self):
        self.llmClient = LlmClient()
        logger.info("폴백 서비스 코어 서비스 초기화 완료")
        
    def execute(self, messages: List):
        """폴백 에이전트 실행 - 기본적인 LLM 처리 및 폴백 기능"""
        logger.debug(f"폴백 서비스 실행: {len(messages)}개 메시지 처리")

        system_prompt = """
당신은 전북대학교 AI 멘토링 시스템의 폴백 에이전트입니다.
다른 전문 서비스가 사용할 수 없을 때 기본적인 도움을 제공합니다.

다음 단계를 따라 답변해주세요:
1. 대화 기록 우선: 이전 대화에서 답을 찾을 수 있다면 그 정보를 활용하세요.
2. 일반 지식 보조: 대화 기록에 답이 없다면 일반적인 교육 지식으로 도움을 제공하세요.
3. 한국어 응답: 모든 답변은 한국어로 해주세요.

전문 서비스가 정상화되면 더 상세한 도움을 받을 수 있습니다.
"""

        # Pydantic 모델 객체 리스트를 딕셔너리 리스트로 변환
        message_dicts = [msg.dict() for msg in messages]

        # 시스템 프롬프트를 맨 앞에 추가
        request_messages = [
            {"role": "system", "content": system_prompt},
            *message_dicts
        ]

        try:
            # 수정된 LlmClient의 call_llm 함수 호출
            response = self.llmClient.call_llm(request_messages)
            logger.debug("폴백 서비스 LLM 응답 생성 성공")
            return response
        except Exception as e:
            logger.error(f"폴백 서비스 LLM 호출 오류: {e}")
            raise