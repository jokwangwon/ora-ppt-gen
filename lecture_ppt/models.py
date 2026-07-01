"""슬라이드 덱 데이터 모델.

Claude 구조화 출력(structured outputs)과 python-pptx 빌더가 공유하는 스키마.
스키마는 재귀 없이 단순하게 유지해 구조화 출력 제약을 만족시킨다.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SlideLayout(str, Enum):
    """슬라이드 종류. 빌더가 렌더링 방식을 결정하는 데 사용한다."""

    title = "title"          # 표지 (제목 + 부제)
    section = "section"      # 섹션 구분 슬라이드
    bullets = "bullets"      # 제목 + 불릿 본문
    two_column = "two_column"  # 제목 + 좌/우 2단 불릿


class Slide(BaseModel):
    layout: SlideLayout = Field(description="슬라이드 종류")
    title: str = Field(description="슬라이드 제목 (한 줄)")
    bullets: list[str] = Field(
        default_factory=list,
        description="본문 불릿. 각 항목은 간결한 한 문장. bullets 레이아웃에서 3~6개 권장",
    )
    right_bullets: list[str] = Field(
        default_factory=list,
        description="two_column 레이아웃일 때 오른쪽 열 불릿. 다른 레이아웃에서는 비워둔다",
    )
    speaker_notes: str = Field(
        default="",
        description="발표자 노트. 슬라이드에서 실제로 말할 부연 설명 2~4문장",
    )


class Deck(BaseModel):
    title: str = Field(description="발표 전체 제목")
    subtitle: str = Field(default="", description="부제 또는 한 줄 요약")
    slides: list[Slide] = Field(description="슬라이드 목록 (표지 포함)")
