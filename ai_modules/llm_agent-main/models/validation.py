"""
입력 검증 모델들
Pydantic을 사용한 데이터 검증 및 직렬화
"""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, Field
from datetime import datetime
import json


class Message(BaseModel):
    """메시지 모델"""
    role: str = Field(..., description="메시지 역할 (user, assistant, system)")
    content: str = Field(..., min_length=1, max_length=10000, description="메시지 내용")
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'assistant', 'system']
        if v not in allowed_roles:
            raise ValueError(f'role must be one of {allowed_roles}')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('content cannot be empty')
        return v.strip()


class RequestBody(BaseModel):
    """API 요청 본문 모델"""
    stream: bool = Field(default=False, description="스트리밍 모드 여부")
    model: str = Field(..., min_length=1, max_length=100, description="사용할 모델명")
    messages: List[Message] = Field(..., min_items=1, max_items=100, description="메시지 목록")
    format: Optional[str] = Field(default=None, description="응답 포맷 (plain, markdown)")
    session_id: Optional[str] = Field(default="default", description="세션 ID")
    ignore_history: Optional[bool] = Field(default=False, description="이전 히스토리 무시 여부")
    processing_type: Optional[str] = Field(default=None, description="처리 유형 (tot, simple 등)")
    
    @validator('model')
    def validate_model(cls, v):
        allowed_models = ['ai-mentor']
        if v not in allowed_models:
            raise ValueError(f'model must be one of {allowed_models}')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        if v is not None:
            allowed_formats = ['plain', 'markdown']
            if v not in allowed_formats:
                raise ValueError(f'format must be one of {allowed_formats}')
        return v
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('session_id must contain only alphanumeric characters, underscores, and hyphens')
        if len(v) > 100:
            raise ValueError('session_id must be 100 characters or less')
        return v
    
    @validator('messages')
    def validate_messages(cls, v):
        if len(v) > 100:
            raise ValueError('Too many messages (max 100)')
        
        # 연속된 같은 역할의 메시지 체크
        for i in range(len(v) - 1):
            if v[i].role == v[i + 1].role:
                raise ValueError('Consecutive messages cannot have the same role')
        
        return v


class ChainRequest(BaseModel):
    """체인 실행 요청 모델"""
    chain_type: str = Field(..., description="체인 타입")
    user_input: str = Field(..., min_length=1, max_length=10000, description="사용자 입력")
    context: Optional[str] = Field(default="", max_length=50000, description="컨텍스트")
    session_id: Optional[str] = Field(default="default", description="세션 ID")
    
    @validator('chain_type')
    def validate_chain_type(cls, v):
        allowed_types = ['basic', 'context', 'analysis', 'parallel']
        if v not in allowed_types:
            raise ValueError(f'chain_type must be one of {allowed_types}')
        return v


class AgentRequest(BaseModel):
    """에이전트 실행 요청 모델"""
    user_input: str = Field(..., min_length=1, max_length=10000, description="사용자 입력")
    session_id: Optional[str] = Field(default="default", description="세션 ID")


class QueryAnalysisResult(BaseModel):
    """쿼리 분석 결과 모델"""
    category: str = Field(..., description="복잡도 카테고리")
    owner_hint: str = Field(..., description="담당 에이전트 힌트")
    reasoning: str = Field(..., description="분석 근거")
    is_complex: bool = Field(..., description="복잡한 질문 여부")
    analysis_time: float = Field(..., ge=0, description="분석 소요 시간")
    expansion_context: Optional[str] = Field(default="", description="확장 컨텍스트")
    expansion_keywords: Optional[str] = Field(default="", description="확장 키워드")
    subject_area: Optional[str] = Field(default="", description="과목 영역")
    department_std: Optional[str] = Field(default="", description="표준화된 학과명")
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="제약사항")
    plan: Optional[List[Dict[str, Any]]] = Field(default=None, description="실행 계획")


class SessionInfo(BaseModel):
    """세션 정보 모델"""
    session_id: str = Field(..., description="세션 ID")
    total_messages: int = Field(..., ge=0, description="총 메시지 수")
    current_topic: Optional[str] = Field(default=None, description="현재 주제")
    has_search_results: bool = Field(..., description="검색 결과 존재 여부")
    created_at: Optional[str] = Field(default=None, description="생성 시간")
    updated_at: Optional[str] = Field(default=None, description="업데이트 시간")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(default=None, description="에러 코드")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="에러 발생 시간")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SuccessResponse(BaseModel):
    """성공 응답 모델"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Dict[str, Any]] = Field(default=None, description="응답 데이터")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="응답 시간")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
