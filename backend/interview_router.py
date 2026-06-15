import json
import os
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIError, AsyncOpenAI, BaseModel, RateLimitError
from pydantic import Field

from backend.sessions import (
    create_session,
    get_history,
    get_session_role,
    set_session_role,
)
from core.roles import get_system_prompt

load_dotenv()
router = APIRouter(prefix="/chat", tags=["chat"])


class InterviewStreamRequest(BaseModel):
    """면접 코치 '/chat/stream' 엔드포인트가 받는 요청 모델입니다."""

    question: str = Field(
        ...,
        min_length=1,
        description="면접관이 제시한 질문입니다.",
        examples=["자기소개를 해 주세요."],
    )
    answer: str = Field(
        ...,
        min_length=1,
        description="지원자가 입력한 답변입니다.",
        examples=["안녕하세요. 저는..."],
    )
    role: str = Field(
        default="technical",
        description="면접관 유형입니다. technical, personality, executive, structured 중 하나를 사용합니다.",
        examples=["technical"],
    )
    session_id: str | None = Field(
        default=None, description="UUID 기반 면접 세션 ID입니다."
    )
    model: str = Field(
        default="gpt-5.4-nano", description="사용할 OpenAI 모델명입니다."
    )


# 응답 모델
class SessionCreateResponse(BaseModel):
    session_id: str
    role: str


# 세션 생성 요청 모델
class SessionCreateRequest(BaseModel):
    role: str = Field(default="technical", description="초기 면접관 유형")


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict[str, str]]
    role: str
    message_count: int


ALLOWED_ROLES = {"technical", "personality", "executive", "structured"}


class RoleUpdateRequest(BaseModel):
    role: str = Field(
        ...,
        description="변경할 면접관 유형 (technical · personality · executive · structured)",
    )


class RoleUpdateResponse(BaseModel):
    session_id: str
    role: str
    message: str


def get_interview_openai_client() -> AsyncOpenAI:
    """환경변수에서 OPENAI_API_KEY를 읽어 AsyncOpenAI 클라이언트를 만듭니다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY in not configured")
    return AsyncOpenAI(api_key=api_key)


async def interview_event_generator(
    request: InterviewStreamRequest,
) -> AsyncIterator[str]:
    """면접 코치 피드백을 SSE data 이벤트로 스트리밍합니다."""
    client = get_interview_openai_client()

    system_prompt = get_system_prompt(request.role, "technical")

    history = []
    if not request.session_id:
        session = await create_interview_session(
            SessionCreateRequest(role=request.role)
        )
        request.session_id = session.session_id
        yield (
            "data: "
            f"{json.dumps({'type': 'session', 'session_id': request.session_id}, ensure_ascii=False)}"
            "\n\n"
        )

    # 세션 이력 연결
    try:
        history = get_history(request.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")

    user_content = (
        f"[면접 질문]\n{request.question}\n\n"
        f"[지원자 답변]\n{request.answer}\n\n"
        "위 답변을 면접관 역할에 맞게 평가하고 개선 피드백을 제공해 주세요."
    )
    try:
        stream = await client.chat.completions.create(
            model=request.model,
            temperature=0.7,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": user_content},
            ],
        )

        async for chunk in stream:
            token = chunk.choices[0].delta.content

            if token:
                yield (
                    "data: "
                    f"{json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}"
                    "\n\n"
                )

        yield "data: [DONE]\n\n"
    except RateLimitError:
        raise HTTPException(status_code=429, detail="RateLimitError")
    except APIError:
        raise HTTPException(status_code=502, detail="APIError")


@router.post("/stream")
async def interview_stream(request: InterviewStreamRequest) -> StreamingResponse:
    """면접관 유형에 맞는 피드백을 SSE 형식으로 스트리밍합니다."""
    return StreamingResponse(
        interview_event_generator(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/session/create", response_model=SessionCreateResponse)
async def create_interview_session(body: SessionCreateRequest) -> SessionCreateResponse:
    session_id = create_session(body.role)
    return SessionCreateResponse(session_id=session_id, role=body.role)


@router.get("/session/{session_id}/history", response_model=HistoryResponse)
async def get_interview_history(session_id: str) -> HistoryResponse:
    """
    세션 ID 로 면접 이력을 조회합니다.
    """
    try:
        messages = get_history(session_id)
        role = get_session_role(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found")

    return HistoryResponse(
        session_id=session_id,
        messages=messages,
        role=role,
        message_count=len(messages),
    )


@router.patch("/session/{session_id}/role", response_model=RoleUpdateResponse)
async def update_interview_role(session_id: str, body: RoleUpdateRequest):
    """면접관 유형 변경"""
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="role not found")
    else:
        try:
            set_session_role(session_id, body.role)
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        return RoleUpdateResponse(
            session_id=session_id,
            role=body.role,
            message=f"면접관 유형이 {body.role}로 변경되었습니다.",
        )
