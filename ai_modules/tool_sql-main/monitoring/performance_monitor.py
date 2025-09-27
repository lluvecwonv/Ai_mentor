"""
성능 모니터링 클래스
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.logger = logger
        self._stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0
        }
    
    def record_query(self, execution_time: float, success: bool):
        """쿼리 실행 기록"""
        self._stats["total_queries"] += 1
        
        if success:
            self._stats["successful_queries"] += 1
            self._update_avg_execution_time(execution_time)
        else:
            self._stats["failed_queries"] += 1
        
        self.logger.debug(f"📊 [성능 모니터] 쿼리 기록: 성공={success}, 시간={execution_time:.3f}초")
    
    def _update_avg_execution_time(self, execution_time: float):
        """평균 실행 시간 업데이트"""
        total = self._stats["successful_queries"]
        current_avg = self._stats["avg_execution_time"]
        self._stats["avg_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """성능 통계 조회"""
        return {
            **self._stats,
            "success_rate": (
                self._stats["successful_queries"] / 
                max(self._stats["total_queries"], 1) * 100
            )
        }
    
    def reset_stats(self):
        """성능 통계 초기화"""
        self._stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0
        }
        self.logger.info("🔄 [성능 모니터] 통계 초기화 완료")
    
    def get_success_rate(self) -> float:
        """성공률 조회"""
        return (
            self._stats["successful_queries"] / 
            max(self._stats["total_queries"], 1) * 100
        )
    
    def get_avg_execution_time(self) -> float:
        """평균 실행 시간 조회"""
        return self._stats["avg_execution_time"]
    
    def get_total_queries(self) -> int:
        """총 쿼리 수 조회"""
        return self._stats["total_queries"]
