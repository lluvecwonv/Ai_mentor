"""
핸들러 워밍업 유틸리티
서비스 초기화 시 핸들러들을 백그라운드에서 워밍업
"""

import logging
import asyncio
from typing import List, Any

logger = logging.getLogger(__name__)


async def warmup_handlers(*handlers) -> bool:
    """
    여러 핸들러들을 병렬로 워밍업

    Args:
        *handlers: 워밍업할 핸들러들 (warmup() 메서드를 가진 객체들)

    Returns:
        bool: 모든 워밍업이 성공했는지 여부
    """
    try:
        logger.info(f"🔥 {len(handlers)}개 핸들러 워밍업 시작")

        # 워밍업 메서드가 있는 핸들러들만 필터링
        warmup_tasks = []
        for handler in handlers:
            if hasattr(handler, 'warmup') and callable(getattr(handler, 'warmup')):
                warmup_tasks.append(handler.warmup())
            else:
                logger.debug(f"핸들러 {type(handler).__name__}에 warmup 메서드가 없습니다")

        if not warmup_tasks:
            logger.info("워밍업할 핸들러가 없습니다")
            return True

        # 병렬 워밍업 실행 (예외 무시)
        results = await asyncio.gather(*warmup_tasks, return_exceptions=True)

        # 결과 확인
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"핸들러 {i+1} 워밍업 실패: {result}")
            else:
                success_count += 1

        logger.info(f"✅ 워밍업 완료: {success_count}/{len(warmup_tasks)} 성공")
        return success_count == len(warmup_tasks)

    except Exception as e:
        logger.error(f"❌ 워밍업 프로세스 실패: {e}")
        return False


def start_background_warmup(*handlers) -> None:
    """
    백그라운드에서 워밍업 시작 (이벤트 루프가 있을 때만)

    Args:
        *handlers: 워밍업할 핸들러들
    """
    try:
        asyncio.create_task(warmup_handlers(*handlers))
        logger.info("🚀 백그라운드 워밍업 태스크 시작")
    except RuntimeError:
        logger.info("이벤트 루프가 없어 워밍업을 나중에 실행합니다")


async def warmup_with_retry(*handlers, max_retries: int = 2) -> bool:
    """
    재시도를 포함한 워밍업

    Args:
        *handlers: 워밍업할 핸들러들
        max_retries: 최대 재시도 횟수

    Returns:
        bool: 워밍업 성공 여부
    """
    for attempt in range(max_retries + 1):
        try:
            success = await warmup_handlers(*handlers)
            if success:
                return True
            elif attempt < max_retries:
                logger.info(f"🔄 워밍업 재시도 {attempt + 1}/{max_retries}")
                await asyncio.sleep(1)  # 1초 대기 후 재시도
        except Exception as e:
            logger.error(f"워밍업 시도 {attempt + 1} 실패: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2)  # 2초 대기 후 재시도

    logger.warning("⚠️ 모든 워밍업 재시도 실패")
    return False