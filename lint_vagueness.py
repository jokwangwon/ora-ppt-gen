#!/usr/bin/env python3
"""얼버무림 탐지기 — '대충 뭉뚱그리거나 넘어가려는' 문장을 잡는다.

생성 글에서 자주 나오는 결함: 구체적 사실 대신 두루뭉술한 표현으로 넘어가기.
이 프로젝트 원칙("원문 사실만, 지어내지 말 것")의 뒷면 — 노트에 근거가 없으면
얼버무리지 말고 **정확히 쓰거나 '확인 필요'로 표시**해야 한다.

기계적 후보 탐지다(‘등’처럼 정상 용법도 있어 오탐 가능) → 강한 신호 문장만 ⚠.
정밀 판정은 LLM이 문장을 읽어 "이건 구체적인가, 얼버무렸나 → 무엇이 빠졌나(수치·이름·
메커니즘)"를 짚는 게 가장 정확하다.

사용법:
    python lint_vagueness.py assets/sql_tuning.html
    python lint_vagueness.py days/71/71.slides.json    # 스펙 텍스트도 검사
    python lint_vagueness.py 71일차.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 강한 얼버무림 신호 (문장 단위로 ⚠)
STRONG = {
    "넘어가기/생략": ["대충", "얼추", "대략적으로", "자세한 (?:내용|설명|건|것)은", "이하 생략",
                 "설명은 생략", "생략한다", "추후", "나중에 다룬다", "여기서는 다루지 않"],
    "두루뭉술": ["여러 ?가지", "다양한", "각종", "여러 요인", "여러 이유", "적절히", "적당히",
              "알아서", "상황에 따라", "경우에 따라", "필요에 따라", "어느 ?정도", "그런 식으로",
              "이런 식으로", "등을 통해", "등등"],
    "막연한 일반화": ["일반적으로", "대체로", "대부분", "보통은", "흔히", "종종"],
    "약한 단정": ["것 같다", "듯하다", "듯 하다", "인 것으로 보인다", "라고 볼 수 있다", "아마도?"],
    "과장 단정": ["무조건", "절대로", "절대 (?:안|아니|없|못)", "모든 경우에"],
}
# 전달 없이 약속만 하는 신호 (soft)
PROMISE = ["에 대해 (?:설명|알아본다|살펴본다)", "아래에서 다룬다", "뒤에서 설명"]

STRONG_RE = {cat: re.compile("|".join(pats)) for cat, pats in STRONG.items()}
PROMISE_RE = re.compile("|".join(PROMISE))


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+|(?<=다)\s+(?=[가-힣])|·|—", text)
    return [s.strip() for s in parts if len(s.strip()) >= 6]


def scan_text(text: str) -> list[tuple[str, str, str]]:
    """(카테고리, 트리거, 문장) 목록."""
    hits = []
    for s in sentences(text):
        for cat, rx in STRONG_RE.items():
            m = rx.search(s)
            if m:
                hits.append((cat, m.group(0), s))
        pm = PROMISE_RE.search(s)
        if pm:
            hits.append(("약속만/전달없음", pm.group(0), s))
    return hits


def extract_units(path: Path) -> list[tuple[str, str]]:
    """(단위 라벨, 텍스트) — HTML은 개념별, JSON 스펙은 슬라이드별, txt는 통째."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "lxml")
        units = []
        for h3 in soup.find_all("h3", class_="blk"):
            body = []
            for sib in h3.next_siblings:
                if getattr(sib, "name", None) == "h3" and "blk" in (sib.get("class") or []):
                    break
                body.append(getattr(sib, "get_text", lambda **k: str(sib))(separator=" "))
            units.append((re.sub(r"\s+", " ", h3.get_text(" ", strip=True))[:50], " ".join(body)))
        return units
    if path.suffix == ".json":
        spec = json.loads(raw)
        out = []
        for sl in spec.get("slides", []):
            txt = " ".join(
                " ".join(b.get("items", []) or [])
                + " " + (b.get("body", "") or "") + " " + (b.get("text", "") or "")
                + " " + " ".join((it.get("body", "") or "") for it in b.get("items", []) if isinstance(it, dict))
                for b in sl.get("blocks", [])
            )
            out.append((sl.get("title", sl.get("type", "?"))[:50], txt))
        return out
    return [(path.name, raw)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="얼버무림 탐지기")
    ap.add_argument("path", type=Path, help="HTML / 슬라이드 JSON / txt")
    ap.add_argument("--strict", action="store_true", help="후보가 있으면 exit 1")
    args = ap.parse_args(argv)
    if not args.path.exists():
        print(f"[vague] 파일 없음: {args.path}", file=sys.stderr); return 1

    units = extract_units(args.path)
    total = 0
    print(f"[vague] {args.path.name} — 얼버무림 후보 검사 "
          f"(강한 신호 문장만 표시, ‘등’ 등 정상 용법은 넘어감)\n")
    for label, text in units:
        hits = scan_text(text)
        if not hits:
            continue
        total += len(hits)
        print(f"■ {label}")
        for cat, trig, sent in hits[:8]:
            s = sent if len(sent) <= 90 else sent[:88] + "…"
            print(f"   ⚠ [{cat}] “{trig}”  — {s}")
        print()

    if total == 0:
        print("✓ 강한 얼버무림 신호 없음. (정밀 판정은 LLM 가독성/구체성 리뷰 권장)")
    else:
        print(f"총 {total}건. 각 문장을 구체(수치·이름·메커니즘)로 바꾸거나, "
              f"근거가 없으면 ‘확인 필요’로 명시하세요. 지어내지 말 것.")
    return 1 if (total and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
