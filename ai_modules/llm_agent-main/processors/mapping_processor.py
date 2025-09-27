"""
학과 매핑 프로세서
Department Mapping Agent와 통신하여 학과명을 정규화
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MappingProcessor:
    """Department Mapping 프로세서"""

    def __init__(self, mapping_handler):
        logger.info("🗺️ MappingProcessor 초기화")
        self.mapping_handler = mapping_handler

    async def process(self, data: Dict[str, Any]) -> Optional[str]:
        """학과명 매핑 처리"""
        try:
            # 사용자 메시지 추출 ('query'가 아닌 'user_message' 사용)
            user_message = data.get('user_message', '') or data.get('query', '')
            logger.info(f"🏫 학과명 매핑 처리 시작 - 쿼리: '{user_message}' (길이: {len(user_message)})")
            logger.info(f"🔍 전달받은 data: {list(data.keys())}")

            if not self.mapping_handler:
                logger.warning("❌ Mapping handler가 없습니다")
                return None

            # Department Mapping Agent 호출
            result = await self.mapping_handler.handle(
                user_message=user_message,
                query_analysis=data.get('query_analysis', {})
            )

            if result:
                logger.info(f"✅ 학과명 매핑 완료 - 결과: {str(result)}...")
                return result
            else:
                logger.warning("⚠️ 학과명 매핑 결과가 없습니다")
                return None

        except Exception as e:
            logger.error(f"❌ 학과명 매핑 처리 중 오류: {e}")
            return None