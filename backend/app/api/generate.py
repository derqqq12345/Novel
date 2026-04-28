"""
소설 챕터 생성 API
Ollama의 OpenAI 호환 API를 통해 로컬 Qwen 모델로 한국어 소설을 생성합니다.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import json

from backend.app.config import settings

router = APIRouter()


class GenerateRequest(BaseModel):
    genre: str = "fantasy"
    tone: str = "serious"
    temperature: float = Field(default=0.7, ge=0.3, le=1.2)
    previous_content: Optional[str] = None  # 이전 챕터 내용 (컨텍스트)
    user_prompt: Optional[str] = None        # 사용자 추가 지시사항
    chapter_number: int = 1


GENRE_KO = {
    "fantasy": "판타지",
    "romance": "로맨스",
    "mystery": "미스터리",
    "science_fiction": "SF 공상과학",
    "thriller": "스릴러",
}

TONE_KO = {
    "serious": "진지하고 문학적인",
    "humorous": "유머러스하고 가벼운",
    "dark": "어둡고 긴장감 있는",
    "lighthearted": "밝고 따뜻한",
}


def build_messages(req: GenerateRequest) -> str:
    """Ollama /api/generate 용 단일 프롬프트 문자열 생성"""
    genre = GENRE_KO.get(req.genre, req.genre)
    tone = TONE_KO.get(req.tone, req.tone)

    context_section = ""
    if req.previous_content:
        prev = req.previous_content[-1500:] if len(req.previous_content) > 1500 else req.previous_content
        context_section = f"\n\n## 이전 내용 (연속성 유지)\n{prev}\n"

    user_instruction = f"\n\n## 추가 지시사항\n{req.user_prompt}" if req.user_prompt else ""

    return f"""당신은 한국어 장편소설 전문 작가입니다. 아래 조건에 맞게 소설 챕터를 작성하세요.

## 조건
- 장르: {genre}
- 문체/톤: {tone}
- 챕터 번호: {req.chapter_number}
- 최소 분량: 2,000자 이상
- 자연스러운 한국어, 적절한 대화와 묘사 포함
- 챕터 제목 없이 본문만 작성{context_section}{user_instruction}

지금 바로 소설 본문을 작성하세요:"""


@router.post("/generate")
async def generate_chapter(req: GenerateRequest):
    """
    Ollama의 Qwen 모델로 소설 챕터를 스트리밍 생성합니다.
    /api/generate 엔드포인트 사용 (구버전 Ollama 호환)
    """
    prompt = build_messages(req)

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": req.temperature,
            "num_predict": 4096,
            "top_p": 0.9,
        },
    }

    async def stream_ollama():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        yield f"data: {json.dumps({'error': f'Ollama 오류 ({response.status_code}): {error_body.decode()}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            # /api/generate 응답 구조: {"response": "...", "done": false}
                            text = data.get("response", "")
                            if text:
                                yield f"data: {json.dumps({'text': text})}\n\n"
                            if data.get("done"):
                                yield "data: [DONE]\n\n"
                                return
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Ollama에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_ollama(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/generate/models")
async def list_models():
    """Ollama에서 사용 가능한 모델 목록을 반환합니다."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Ollama에 연결할 수 없습니다. ollama serve 가 실행 중인지 확인하세요.",
        )


@router.get("/generate/health")
async def check_ollama():
    """Ollama 연결 상태를 확인합니다."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            model_available = settings.OLLAMA_MODEL in model_names
        return {
            "status": "ok",
            "model": settings.OLLAMA_MODEL,
            "model_available": model_available,
            "available_models": model_names,
        }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama 연결 실패")
