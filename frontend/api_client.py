from collections.abc import Iterator
import json
import os
from typing import Any

from dotenv import load_dotenv
import httpx

load_dotenv()


def get_backend_url() -> str:
    """면접 코치 FastAPI 백엔드 주소를 환경변수 또는 기본값으로 가져옵니다."""
    return os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def post_interview_message(message: str) -> dict[str, Any]:
    """면접 코치 백엔드에 일반 응답 요청을 보냅니다."""
    backend_url = get_backend_url()
    with httpx.Client(base_url=backend_url, timeout=10.0) as client:
        response = client.post("/chat", json={"message": message})
        response.raise_for_status()
        return response.json()


def stream_interview_message(
    message: str,
    role: str,
    session_id: str | None = None,
) -> Iterator[dict[str, str]]:
    """면접 코치 백엔드의 SSE 응답을 순서대로 전달합니다."""
    payload = {
        "question": "지원자의 답변을 평가해주세요.",
        "answer": message,
        "role": role,
        "session_id": session_id,
    }
    url = f"{get_backend_url()}/chat/stream"

    with httpx.stream(
        "POST",
        url,
        json=payload,
        timeout=30.0,
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            if not line.startswith("data:"):
                continue

            token = line[5:].strip()

            if token == "[DONE]":
                break

            yield json.loads(token)


# def render_streaming_answer(placeholder: Any, message: str) -> str:
#     """스트리밍 토큰을 누적해 면접 코치 답변을 화면에 표시합니다.

#     Args:
#         placeholder: st.empty()로 만든 Streamlit placeholder 객체
#         message: 면접 질문 문자열

#     Returns:
#         누적된 전체 답변 문자열
#     """
#     full_text = ""

#     for event in stream_interview_message(message, "technical"):
#         if event.get("type") != "token":
#             continue

#         full_text += event["content"]
#         placeholder.markdown(full_text)
#     return full_text
