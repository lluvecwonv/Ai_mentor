import logging
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from service.sqlCoreService import SqlCoreService

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

# 전역 서비스 인스턴스 (싱글톤 패턴)
core_service: Optional[SqlCoreService] = None

@dataclass
class RequestContext:
    """요청 컨텍스트 정보"""
    request_id: str
    session_id: Optional[str]
    timestamp: datetime
    user_agent: Optional[str]
    client_ip: Optional[str]

class RequestBody(BaseModel):
    """요청 본문 모델"""
    query: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    session_id: Optional[str] = Field(None, description="세션 ID")
    include_debug: bool = Field(False, description="디버그 정보 포함 여부")

class ResponseBody(BaseModel):
    """응답 본문 모델"""
    message: str
    request_id: str
    processing_time: float
    success: bool
    debug_info: Optional[Dict[str, Any]] = None

class SqlController:
    """LangChain 기반 SQL 처리 컨트롤러"""

    def __init__(self):
        self.logger = logger
        self._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_processing_time": 0.0
        }

    def _get_services(self):
        """서비스 인스턴스 가져오기 (지연 초기화)"""
        global core_service
        
        if core_service is None:
            logger.info("🔧 [서비스 초기화] SqlCoreService 생성")
            core_service = SqlCoreService()
            core_service.create_agent()
        
        return core_service

    def _create_request_context(self, request: Request, session_id: Optional[str] = None) -> RequestContext:
        """요청 컨텍스트 생성"""
        return RequestContext(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.now(),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )

    def _log_request_start(self, context: RequestContext, query: str):
        """요청 시작 로깅"""
        logger.info(f"🚀 [요청 시작] ID: {context.request_id}, 세션: {context.session_id}")
        logger.info(f"📝 [질문] {query[:100]}{'...' if len(query) > 100 else ''}")
        logger.debug(f"🌐 [클라이언트] IP: {context.client_ip}, UA: {context.user_agent}")

    def _log_request_end(self, context: RequestContext, success: bool, processing_time: float):
        """요청 완료 로깅"""
        status = "성공" if success else "실패"
        logger.info(f"✅ [요청 완료] ID: {context.request_id}, 상태: {status}, 시간: {processing_time:.3f}초")

    def _update_request_stats(self, processing_time: float, success: bool):
        """요청 통계 업데이트"""
        self._request_stats["total_requests"] += 1
        if success:
            self._request_stats["successful_requests"] += 1
        else:
            self._request_stats["failed_requests"] += 1
        
        # 평균 처리 시간 업데이트
        total = self._request_stats["total_requests"]
        current_avg = self._request_stats["avg_processing_time"]
        self._request_stats["avg_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )

    def get_request_stats(self) -> Dict[str, Any]:
        """요청 통계 조회"""
        return {
            **self._request_stats,
            "success_rate": (
                self._request_stats["successful_requests"] / 
                max(self._request_stats["total_requests"], 1) * 100
            )
        }

# 컨트롤러 인스턴스
controller = SqlController()

@router.post("/agent", response_model=ResponseBody)
async def agent_api(request: Request, data: RequestBody):
    """SQL 에이전트 API 엔드포인트"""
    start_time = time.monotonic()
    context = controller._create_request_context(request, data.session_id)
    
    try:
        # 요청 시작 로깅
        controller._log_request_start(context, data.query)
        
        # 서비스 가져오기
        core_service = controller._get_services()
        
        # SQL 쿼리 실행
        logger.info(f"🔧 [SQL 실행] 시작")
        sql_start = time.monotonic()
        
        sql_result = core_service.execute(data.query)
        sql_time = time.monotonic() - sql_start

        logger.info(f"📋 [2단계] SQL 결과: {sql_result[:200]}..." if len(sql_result) > 200 else f"📋 [2단계] SQL 결과: {sql_result}")
        logger.info(f"📊 [2단계] SQL 결과 길이: {len(sql_result)}자")
        logger.info(f"✅ [2단계] SQL 실행 완료: {sql_time:.3f}초")
        
        # 전체 처리 시간 계산
        total_time = time.monotonic() - start_time
        
        # 성공 로깅
        controller._log_request_end(context, True, total_time)
        controller._update_request_stats(total_time, True)
        
        # 디버그 정보 준비
        debug_info = None
        if data.include_debug:
            debug_info = {
                "sql": {
                    "processing_time": sql_time,
                    "performance_stats": core_service.get_performance_stats()
                },
                "request": {
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "total_processing_time": total_time
                }
            }
        
        # 응답 반환
        return ResponseBody(
            message=sql_result,
            request_id=context.request_id,
            processing_time=total_time,
            success=True,
            debug_info=debug_info
        )
        
    except Exception as e:
        total_time = time.monotonic() - start_time
        logger.error(f"❌ [요청 실패] ID: {context.request_id}, 오류: {e}")
        
        # 실패 로깅
        controller._log_request_end(context, False, total_time)
        controller._update_request_stats(total_time, False)
        
        # HTTP 예외 발생
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"SQL 처리 중 오류가 발생했습니다: {str(e)}",
                "request_id": context.request_id,
                "processing_time": total_time
            }
        )

@router.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    logger.info("🔍 [헬스 체크] 요청됨")
    
    try:
        # 서비스 상태 확인
        core_service = controller._get_services()
        
        # 성능 통계 수집
        sql_stats = core_service.get_performance_stats()
        request_stats = controller.get_request_stats()
        
        logger.info("✅ [헬스 체크] 모든 서비스 정상")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "sql": {
                    "status": "healthy", 
                    "stats": sql_stats
                }
            },
            "requests": request_stats
        }
        
    except Exception as e:
        logger.error(f"❌ [헬스 체크] 실패: {e}")
        raise HTTPException(status_code=503, detail=f"서비스 상태 불량: {str(e)}")

@router.get("/stats")
async def get_stats():
    """통계 조회 엔드포인트"""
    logger.info("📊 [통계 조회] 요청됨")
    
    try:
        core_service = controller._get_services()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "sql_service": core_service.get_performance_stats(),
            "request_stats": controller.get_request_stats()
        }
        
    except Exception as e:
        logger.error(f"❌ [통계 조회] 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.post("/reset-stats")
async def reset_stats():
    """통계 초기화 엔드포인트"""
    logger.info("🔄 [통계 초기화] 요청됨")
    
    try:
        core_service = controller._get_services()
        
        core_service.reset_stats()
        controller._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_processing_time": 0.0
        }
        
        logger.info("✅ [통계 초기화] 완료")
        return {"message": "통계가 초기화되었습니다", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"❌ [통계 초기화] 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 초기화 실패: {str(e)}")