import json
import os
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIError, AsyncOpenAI, BaseModel, RateLimitError
from pydantic import Field

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
    model: str = Field(default="gpt-4o-mini", description="사용할 OpenAI 모델명입니다.")


def get_interview_openai_client() -> AsyncOpenAI:
    """환경변수에서 OPENAI_API_KEY를 읽어 AsyncOpenAI 클라이언트를 만듭니다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY in not configured")
    return AsyncOpenAI(api_key=api_key)


async def interview_event_generator(
    request: InterviewStreamRequest,
) -> AsyncIterator[str]:
    """면접 코치 피드백을 SSE data 이벤트로 스트리밍합니다.
    작성 흐름:
    1. get_interview_openai_client() 를 호출해 client 를 얻는다.
    2. ROLE_PROMPTS 에서 request.role 에 맞는 system_prompt 를 꺼낸다.(없으면 "technical" 사용)
    3. client.chat.completions.create(..., stream=True) 로 스트림을 연다. messages 는 [system_prompt, user 메시지(질문+답변)] 두 개다.
    4. async for chunk in stream: 으로 순회하며 delta.content 가 있을 때만 f"data: {delta.content}\n\n" 를 yield 한다.
    5. 순회 완료 후 "data: [DONE]\n\n" 을 yield 한다.
    """
    client = get_interview_openai_client()

    system_prompt = get_system_prompt(request.role, "technical")

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
                {"role": "user", "content": user_content},
            ],
        )

        async for chunk in stream:
            token = chunk.choices[0].delta.content

            if token:
                yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"

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
