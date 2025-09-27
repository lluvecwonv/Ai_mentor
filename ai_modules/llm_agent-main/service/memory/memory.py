import logging
from typing import Dict, List, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """LangChain 호환 대화 메모리 관리"""

    def __init__(self, max_history_length: int = 20):
        self.max_history_length = max_history_length
        self.sessions = {}  # 세션별 메모리 저장
        logger.info("ConversationMemory 초기화 완료")

    def get_state(self, session_id: str) -> Dict:
        """세션 상태 조회"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "conversation_history": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

        return self.sessions[session_id]

    def add_exchange(self, session_id: str, user_message: str, assistant_response: str):
        """대화 교환 추가"""
        session_state = self.get_state(session_id)

        # 새 대화 추가
        timestamp = datetime.now().isoformat()
        session_state["conversation_history"].extend([
            {"role": "user", "content": user_message, "timestamp": timestamp},
            {"role": "assistant", "content": assistant_response, "timestamp": timestamp}
        ])

        # 길이 제한
        if len(session_state["conversation_history"]) > self.max_history_length * 2:
            session_state["conversation_history"] = session_state["conversation_history"][-self.max_history_length * 2:]

        session_state["updated_at"] = datetime.now()
        logger.debug(f"세션 {session_id}에 대화 교환 추가")

    def get_messages(self, session_id: str, limit_turns: int = 5) -> List[BaseMessage]:
        """LangChain 호환 메시지 형태로 반환"""
        state = self.get_state(session_id)
        history = state["conversation_history"]

        # 최근 N턴 가져오기 (1턴 = user + assistant 메시지 2개)
        recent_messages = history[-(limit_turns * 2):]

        messages = []
        for msg in recent_messages:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

        return messages

    def get_recent_context(self, session_id: str, max_turns: int = 5) -> str:
        """최근 대화를 문자열로 반환"""
        messages = self.get_messages(session_id, max_turns)

        context_parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                context_parts.append(f"사용자: {msg.content}")
            elif isinstance(msg, AIMessage):
                context_parts.append(f"AI: {msg.content}")

        return "\n".join(context_parts)


    def clear_session(self, session_id: str):
        """세션 초기화"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"세션 {session_id} 초기화 완료")

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """세션 통계 조회"""
        state = self.get_state(session_id)
        return {
            "session_id": session_id,
            "total_messages": len(state["conversation_history"]),
            "created_at": state["created_at"].isoformat() if isinstance(state["created_at"], datetime) else str(state["created_at"]),
            "updated_at": state["updated_at"].isoformat() if isinstance(state["updated_at"], datetime) else str(state["updated_at"])
        }