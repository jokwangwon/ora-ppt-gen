"""FastAPI 앱: 강의 텍스트 → 슬라이드 미리보기 → .pptx 다운로드."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field

from . import llm
from .builder import build_pptx
from .models import Deck

app = FastAPI(title="Lecture → PPT Generator")

STATIC_DIR = Path(__file__).parent / "static"


class GenerateRequest(BaseModel):
    lecture_text: str = Field(min_length=1)
    max_slides: int | None = Field(default=15, ge=3, le=40)


@app.post("/api/generate", response_model=Deck)
def generate(req: GenerateRequest) -> Deck:
    """강의 텍스트를 슬라이드 덱(JSON)으로 변환. 미리보기용."""
    try:
        return llm.generate_deck(req.lecture_text, req.max_slides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001 - LLM/네트워크 오류를 사용자에게 전달
        raise HTTPException(status_code=502, detail=f"생성 실패: {e}")


@app.post("/api/pptx")
def download_pptx(deck: Deck) -> Response:
    """미리보기(가능하면 수정된) 덱 JSON을 받아 .pptx 파일로 반환."""
    if not deck.slides:
        raise HTTPException(status_code=400, detail="슬라이드가 없습니다.")
    data = build_pptx(deck)
    # 표시용 파일명(유니코드 허용)과 순수 ASCII 폴백을 함께 제공한다.
    display = (re.sub(r"[^\w가-힣 -]", "", deck.title, flags=re.UNICODE).strip() or "lecture")
    filename = f"{display}.pptx"
    ascii_stem = re.sub(r"[^A-Za-z0-9_-]", "_", display).strip("_")
    ascii_name = f"{ascii_stem or 'lecture'}.pptx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_name}\"; "
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
