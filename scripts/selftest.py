"""LLM 없이 빌더만 검증하는 오프라인 자가 테스트.

python-pptx가 `Deck` 샘플을 실제 .pptx로 렌더링하는지 확인한다.
API 키가 필요 없으므로 CI/개발 환경 점검에 쓴다.

    python scripts/selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lecture_ppt.builder import build_pptx  # noqa: E402
from lecture_ppt.models import Deck, Slide, SlideLayout  # noqa: E402

SAMPLE = Deck(
    title="운영체제 개요",
    subtitle="프로세스와 스레드",
    slides=[
        Slide(layout=SlideLayout.title, title="운영체제 개요"),
        Slide(
            layout=SlideLayout.section,
            title="1. 프로세스란?",
        ),
        Slide(
            layout=SlideLayout.bullets,
            title="프로세스의 정의",
            bullets=[
                "실행 중인 프로그램의 인스턴스",
                "고유한 주소 공간과 자원을 가진다",
                "PCB(Process Control Block)로 상태를 관리",
            ],
            speaker_notes="프로그램은 디스크의 정적 파일이고, 프로세스는 메모리에 적재되어 실행되는 동적 개체라는 점을 강조.",
        ),
        Slide(
            layout=SlideLayout.two_column,
            title="프로세스 vs 스레드",
            bullets=["독립된 주소 공간", "생성 비용이 큼", "IPC로 통신"],
            right_bullets=["주소 공간 공유", "생성 비용이 작음", "메모리 직접 공유"],
            speaker_notes="스레드는 같은 프로세스 안에서 자원을 공유하므로 context switch 비용이 낮다.",
        ),
    ],
)


def main() -> int:
    data = build_pptx(SAMPLE)
    out = Path(__file__).resolve().parent.parent / "examples"
    out.mkdir(exist_ok=True)
    path = out / "sample_output.pptx"
    path.write_bytes(data)

    # 간단 검증: 파일이 비어있지 않고 zip(pptx) 시그니처로 시작하는지.
    assert len(data) > 2000, "생성된 파일이 너무 작습니다."
    assert data[:2] == b"PK", "유효한 .pptx(zip)가 아닙니다."
    print(f"OK: {len(data):,} bytes -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
