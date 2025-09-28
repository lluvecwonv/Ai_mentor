import logging
import sqlite3
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """LangChain 호환 대화 메모리 관리 (SQLite 지속성)"""

    def __init__(self, max_history_length: int = 20, db_path: str = "memory.db"):
        self.max_history_length = max_history_length
        self.db_path = db_path
        self.sessions = {}  # 메모리 캐시
        self._init_database()
        self._load_sessions_from_db()
        logger.info(f"ConversationMemory 초기화 완료 (DB: {db_path})")

    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 세션 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    conversation_history TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("데이터베이스 초기화 완료")
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")

    def _load_sessions_from_db(self):
        """데이터베이스에서 세션 로드"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM sessions')
            rows = cursor.fetchall()
            
            for row in rows:
                session_id, created_at, updated_at, history_json = row
                history = json.loads(history_json) if history_json else []
                
                self.sessions[session_id] = {
                    "session_id": session_id,
                    "conversation_history": history,
                    "created_at": datetime.fromisoformat(created_at),
                    "updated_at": datetime.fromisoformat(updated_at)
                }
            
            conn.close()
            logger.info(f"데이터베이스에서 {len(self.sessions)}개 세션 로드 완료")
        except Exception as e:
            logger.error(f"세션 로드 실패: {e}")

    def _save_session_to_db(self, session_id: str):
        """세션을 데이터베이스에 저장"""
        try:
            if session_id not in self.sessions:
                return
                
            session_data = self.sessions[session_id]
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # JSON 직렬화를 위해 datetime을 문자열로 변환
            history_json = json.dumps(session_data["conversation_history"], ensure_ascii=False)
            created_at = session_data["created_at"].isoformat() if isinstance(session_data["created_at"], datetime) else str(session_data["created_at"])
            updated_at = session_data["updated_at"].isoformat() if isinstance(session_data["updated_at"], datetime) else str(session_data["updated_at"])
            
            cursor.execute('''
                INSERT OR REPLACE INTO sessions (session_id, created_at, updated_at, conversation_history)
                VALUES (?, ?, ?, ?)
            ''', (session_id, created_at, updated_at, history_json))
            
            conn.commit()
            conn.close()
            logger.debug(f"세션 {session_id} 데이터베이스 저장 완료")
        except Exception as e:
            logger.error(f"세션 저장 실패: {e}")

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
        
        # 데이터베이스에 저장
        self._save_session_to_db(session_id)
        
        logger.debug(f"세션 {session_id}에 대화 교환 추가 및 저장 완료")

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
            
            # 데이터베이스에서도 삭제
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                conn.close()
                logger.info(f"세션 {session_id} 초기화 완료 (DB에서도 삭제)")
            except Exception as e:
                logger.error(f"세션 DB 삭제 실패: {e}")
                logger.info(f"세션 {session_id} 메모리에서만 초기화 완료")

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """세션 통계 조회"""
        state = self.get_state(session_id)
        return {
            "session_id": session_id,
            "total_messages": len(state["conversation_history"]),
            "created_at": state["created_at"].isoformat() if isinstance(state["created_at"], datetime) else str(state["created_at"]),
            "updated_at": state["updated_at"].isoformat() if isinstance(state["updated_at"], datetime) else str(state["updated_at"])
        }