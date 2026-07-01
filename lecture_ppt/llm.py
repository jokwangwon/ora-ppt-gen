"""Claude로 강의 내용을 슬라이드 덱으로 구조화한다.

Anthropic 구조화 출력(`messages.parse` + `output_format`)을 사용해
스키마(`Deck`)에 맞는 검증된 객체를 바로 돌려받는다.
"""

from __future__ import annotations

import anthropic

from .models import Deck

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
당신은 대학/기업 강의 내용을 발표용 슬라이드 덱으로 정리하는 전문가입니다.
주어진 수업 내용(텍스트 또는 마크다운)을 분석해 논리적 흐름을 갖춘 슬라이드 덱을 만드세요.

원칙:
- 첫 슬라이드는 반드시 layout="title" 표지로, 전체 주제를 담은 제목을 씁니다.
- 내용을 주제 단위로 묶고, 큰 전환점에는 layout="section" 슬라이드를 넣습니다.
- 본문 슬라이드(layout="bullets")의 불릿은 3~6개, 각 항목은 완결된 한 문장으로 간결하게.
  원문을 그대로 복사하지 말고 핵심만 재구성합니다.
- 비교/대조/장단점처럼 두 축이 뚜렷하면 layout="two_column"으로 좌우로 나눕니다.
- speaker_notes에는 슬라이드에 다 담지 못한 부연 설명이나 예시를 2~4문장으로 적어,
  발표자가 실제로 말할 대본이 되게 합니다.
- 슬라이드 제목은 명사구로 짧게. 불릿에 소제목을 중복해 넣지 않습니다.
- 입력 언어를 그대로 따릅니다(한국어 입력 → 한국어 슬라이드).

분량은 내용에 맞게 조절하되, 한 슬라이드에 너무 많은 정보를 몰아넣지 마세요.
"""


def build_prompt(lecture_text: str, max_slides: int | None) -> str:
    limit = (
        f"\n\n표지를 포함해 슬라이드는 최대 {max_slides}장 이내로 만드세요."
        if max_slides
        else ""
    )
    return (
        "다음 수업 내용을 슬라이드 덱으로 정리해 주세요."
        f"{limit}\n\n--- 수업 내용 시작 ---\n{lecture_text}\n--- 수업 내용 끝 ---"
    )


def generate_deck(
    lecture_text: str,
    max_slides: int | None = 15,
    client: anthropic.Anthropic | None = None,
) -> Deck:
    """강의 텍스트를 받아 검증된 `Deck`을 반환한다.

    ANTHROPIC_API_KEY 환경변수(또는 `ant auth login` 프로필)로 인증한다.
    """
    if not lecture_text.strip():
        raise ValueError("수업 내용이 비어 있습니다.")

    client = client or anthropic.Anthropic()

    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(lecture_text, max_slides)}],
        output_format=Deck,
    )

    deck = response.parsed_output
    if deck is None or not deck.slides:
        raise RuntimeError("슬라이드를 생성하지 못했습니다. 입력을 확인해 주세요.")
    return deck
