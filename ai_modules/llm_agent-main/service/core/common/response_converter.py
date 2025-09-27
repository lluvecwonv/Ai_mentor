from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class OpenAIResponseConverter:
    """OpenAI 호환 응답 형식 변환기"""

    @staticmethod
    def convert_to_openai_format(
        result: Any,
        duration: float,
        processing_type: str,
        model: str = "gpt-4",
        system_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:

        # 기본 응답 구조
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "system_fingerprint": system_fingerprint or f"fp_{processing_type}",
            "usage": {
                "prompt_tokens": 0,  # 실제 토큰 계산 로직 추가 필요
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

        # 결과 처리
        if isinstance(result, dict):
            # 이미 OpenAI 형식인 경우
            if "choices" in result:
                response.update(result)
            # LangGraph 결과 형식
            elif "messages" in result:
                response["choices"] = [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result["messages"][-1].content if result["messages"] else ""
                        },
                        "finish_reason": "stop"
                    }
                ]
            # 일반 딕셔너리 결과
            else:
                content = result.get("content", str(result))
                response["choices"] = [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }
                ]
        # 문자열 결과
        else:
            response["choices"] = [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(result)
                    },
                    "finish_reason": "stop"
                }
            ]

        # 메타데이터 추가
        response["metadata"] = {
            "processing_type": processing_type,
            "processing_time": duration,
            "timestamp": datetime.now().isoformat()
        }

        return response

    @staticmethod
    def convert_streaming_chunk(
        content: str,
        index: int = 0,
        finish_reason: Optional[str] = None,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """
        스트리밍 청크를 OpenAI 형식으로 변환

        Args:
            content: 청크 내용
            index: 청크 인덱스
            finish_reason: 완료 이유
            model: 사용된 모델

        Returns:
            OpenAI 호환 스트리밍 청크
        """
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "index": index,
                    "delta": {
                        "content": content
                    },
                    "finish_reason": finish_reason
                }
            ]
        }
        return chunk

    @staticmethod
    def merge_responses(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        여러 응답을 하나로 병합

        Args:
            responses: 병합할 응답 목록

        Returns:
            병합된 응답
        """
        if not responses:
            return OpenAIResponseConverter.convert_to_openai_format(
                "No responses to merge", 0, "merge"
            )

        # 첫 번째 응답을 베이스로 사용
        merged = responses[0].copy()

        # choices 병합
        all_choices = []
        for response in responses:
            if "choices" in response:
                all_choices.extend(response["choices"])

        merged["choices"] = all_choices

        # usage 통계 병합
        if "usage" in merged:
            total_prompt = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in responses)
            total_completion = sum(r.get("usage", {}).get("completion_tokens", 0) for r in responses)
            merged["usage"] = {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_prompt + total_completion
            }

        return merged