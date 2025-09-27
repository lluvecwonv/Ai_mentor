"""
응답 포맷팅 유틸리티
"""
import json
import re
from datetime import datetime


def format_sse(data: str, event_type: str = "message") -> str:
    """SSE 이벤트 포맷팅"""
    if event_type != "message":
        return f"event: {event_type}\ndata: {data}\n\n"
    else:
        return "".join(f"data: {line}\n" for line in data.splitlines()) + "\n\n"


def format_action_event(action: str, status: str, details: str = "") -> str:
    """액션 이벤트 포맷팅"""
    event_data = json.dumps({
        "action": action,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)
    return format_sse(event_data, f"action_{status}")


def strip_markdown(md: str) -> str:
    """마크다운 제거"""
    if not isinstance(md, str):
        return md

    # Convert links [text](url) -> text (url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", md)
    # Remove images ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Bold/italic markers
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    # Inline code/backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Code fences
    text = text.replace("```", "")
    # Headings and list markers
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Collapse excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Trim lines
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()