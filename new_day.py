#!/usr/bin/env python3
"""하루치 자습 폴더 스캐폴드 — 자습 시작 전 1초 준비.

days/<N>/ 를 만들고 복습 노트(review.md)와 문제 뼈대(quiz.json)를 깔아둔다.
템플릿은 days/TEMPLATE.md. 이미 있으면 덮어쓰지 않는다(멱등).

사용법:
    python new_day.py 73
    python new_day.py 73 --topic rman_recovery.html   # 문서 힌트만 출력용
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DAYS = ROOT / "days"
TEMPLATE = DAYS / "TEMPLATE.md"
QUIZ_SKELETON = {"MCQ": [], "ESSAY": [], "TERMS": [], "PLANQ": []}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="하루치 자습 폴더 스캐폴드")
    ap.add_argument("day", type=int, help="일차 (예: 73)")
    ap.add_argument("--topic", help="그날 내용이 들어갈 문서 파일명 (안내용)")
    args = ap.parse_args(argv)

    day_dir = DAYS / str(args.day)
    day_dir.mkdir(parents=True, exist_ok=True)

    # 복습 노트
    review = day_dir / "review.md"
    if review.exists():
        print(f"· 이미 있음: {review}")
    else:
        body = (TEMPLATE.read_text(encoding="utf-8").replace("N일차", f"{args.day}일차")
                if TEMPLATE.exists() else f"# {args.day}일차 복습 노트\n")
        review.write_text(body, encoding="utf-8")
        print(f"+ 생성: {review}")

    # 문제 뼈대
    quiz = day_dir / "quiz.json"
    if quiz.exists():
        print(f"· 이미 있음: {quiz}")
    else:
        quiz.write_text(json.dumps(QUIZ_SKELETON, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"+ 생성: {quiz}")

    doc = args.topic or "<topic>.html"
    print(f"""
다음 순서 (자습 1시간):
  1) days/{args.day}/review.md 를 양식대로 채우기        (docs/STUDY_ROUTINE.md 참고)
  2) 대화(Claude)로 저작: assets/{doc} 섹션 · quiz.json · {args.day}.slides.json
  3) python make_day.py {args.day} --doc {doc}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
