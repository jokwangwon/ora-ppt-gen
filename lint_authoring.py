#!/usr/bin/env python3
"""저작 품질 린터 — 정답지 작법 대비 '얇은' 개념을 적발한다.

정답지(허브)의 개념(h3.blk)은 대체로 [다이어그램 + why/tip + 실측 숫자 +
비유 + 문제→원인→해결 서사]를 갖춘다. 이 린터는 문서의 각 개념이 그 기준에
얼마나 부합하는지 점수화하고, 미달 개념과 '무엇이 빠졌는지'를 보고한다.

강제(exit 1)가 아니라 **조언**이 기본. `--strict` 로 얇은 개념이 있으면 실패.
make_day 에 연결하면 저작 직후 약점을 자동으로 짚어준다.

사용법:
    python lint_authoring.py assets/sql_tuning.html
    python lint_authoring.py assets/sql_tuning.html --min 3 --strict
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

# 점검 항목 (가중치). 다이어그램이 가장 큰 격차라 2점.
CHECKS = [
    ("diagram", 2, "다이어그램(figure/svg)"),
    ("callout", 1, "why/tip 박스"),
    ("number", 1, "실측 숫자"),
    ("analogy", 1, "비유(lead/‘비유’)"),
    ("steps", 1, "문제→원인→해결 서사"),
    ("depth", 1, "본문 400자+"),
]
MAX_SCORE = sum(w for _, w, _ in CHECKS)


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _concept_html(h3: Tag) -> str:
    """h3.blk 다음부터 다음 h3.blk(또는 섹션 끝)까지의 HTML."""
    parts = []
    for sib in h3.next_siblings:
        if isinstance(sib, Tag):
            if sib.name == "h3" and "blk" in (sib.get("class") or []):
                break
            parts.append(str(sib))
    return "".join(parts)


def complexity(title: str, html: str) -> str:
    """개념 난이도: 쉬움 / 보통 / 어려움.

    목표는 '즉시 이해'다. 난이도에 맞춰 설명 깊이를 매칭한다 —
    쉬운 개념은 한두 줄+표로 충분(얇아도 정상), 어려운 개념일수록 구조가 필요.
    난이도는 '움직이는 부품 수'로 추정한다: 하위 항목·표 행·단계·주의/예외·코드.
    """
    txt = re.sub(r"<[^>]+>", " ", html)
    prose = len(re.sub(r"\s+", "", txt))
    parts = len(re.findall(r"<li\b", html)) + len(re.findall(r"<tr\b", html)) + len(re.findall(r"<h4\b", html))
    caveats = len(re.findall(r"주의|예외|함정|충돌|하지만|단,|반면| vs |왜 ", txt))
    codeplan = len(re.findall(r"<pre|kind.:.(?:code|plan)", html))
    steps = 1 if re.search(r"①.*②|단계|순서|→", txt, re.S) else 0
    hard = (prose > 900) or (parts >= 9) or (caveats >= 3) or (codeplan >= 2) or (steps and prose > 500)
    easy = (prose < 320) and (parts <= 3) and (caveats == 0) and (codeplan == 0)
    return "어려움" if hard else ("쉬움" if easy else "보통")


def concept_type(title: str, html: str) -> str:
    """개념 유형: reference(참조표·정리) / example(예제·실습) / mechanism(원리).

    정답지도 참조·예제 개념은 얇게 둔다 → 이런 유형엔 깊이를 강요하지 않는다.
    메커니즘(원리 설명) 개념만 정답지급 깊이를 목표로 한다.
    """
    if re.search(r"사전|총정리|정리|종류|목록|치트|요약|한눈에", title):
        return "reference"
    if re.search(r"예제|예로|실습|해보기|읽어보기|따라", title):
        return "example"
    # 코드/표가 지배적이고 산문이 적으면 예제/참조로 본다
    codes = len(re.findall(r"<pre|<code|kind.:.code", html))
    tables = len(re.findall(r"<table", html))
    prose = len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html)))
    if codes >= 2 and prose < 300:
        return "example"
    if tables >= 1 and prose < 250:
        return "reference"
    return "mechanism"


def score_concept(title: str, html: str) -> dict:
    txt = re.sub(r"<[^>]+>", " ", html)
    flags = {
        "diagram": bool(re.search(r"<figure|<svg", html)),
        "callout": bool(re.search(r'class="(why|tip)"', html)),
        # 실측: 2자리+ 숫자, %, N배, 콤마 숫자 등
        "number": bool(re.search(r"\d{2,}|\d+\s*배|\d+%|[\d,]{3,}", txt)),
        "analogy": bool(re.search(r"비유|class=\"lead\"", html)),
        "steps": bool(re.search(r"①.*②|문제.*원인.*해결|class=\"steps\"", txt, re.S)),
        "depth": len(re.sub(r"\s+", "", txt)) >= 400,
    }
    score = sum(w for key, w, _ in CHECKS if flags[key])
    lvl = complexity(title, html)
    typ = concept_type(title, html)

    # 난이도 대비 설명 판정: '어려운데 구조가 약한'(벽글) 개념만 보강 대상.
    # 쉬운 개념은 얇아도 정상. 구조 aid = 도해·단계서사·why/tip·표(둘 이상).
    tables = len(re.findall(r"<table", html))
    has_structure = flags["diagram"] or flags["steps"] or flags["callout"] or tables >= 2
    needs_work = (typ == "mechanism" and lvl == "어려움" and not has_structure)

    # 무엇이 이해를 도울지 (어려운 개념에 한해)
    helps = []
    if not flags["diagram"]:
        helps.append("도해(구조/흐름)")
    if not flags["callout"]:
        helps.append("why(왜 그런가)")
    if not flags["steps"] and re.search(r"순서|단계|→", re.sub(r"<[^>]+>", " ", html)):
        helps.append("단계 정리")

    return {"title": title, "score": score, "flags": flags, "type": typ,
            "level": lvl, "needs_work": needs_work, "helps": helps}


def lint(doc_path: Path, min_score: int) -> tuple[list[dict], int]:
    soup = BeautifulSoup(doc_path.read_text(encoding="utf-8"), "lxml")
    results = []
    for h3 in soup.find_all("h3", class_="blk"):
        results.append(score_concept(_text(h3), _concept_html(h3)))
    # 보강 대상 = '어려운데 구조가 약한' 개념만. 쉬운 개념은 얇아도 정상.
    need = [r for r in results if r["needs_work"]]
    return results, len(need)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="저작 품질 린터")
    ap.add_argument("doc", type=Path, help="검사할 HTML 문서")
    ap.add_argument("--min", type=int, default=3, help="얇음 기준 점수(미만이면 경고). 기본 3")
    ap.add_argument("--strict", action="store_true", help="얇은 개념이 있으면 exit 1")
    args = ap.parse_args(argv)

    if not args.doc.exists():
        print(f"[lint] 파일 없음: {args.doc}", file=sys.stderr); return 1

    results, n_thin = lint(args.doc, args.min)
    if not results:
        print(f"[lint] {args.doc.name}: h3.blk 개념이 없음 (구조 밖 문서일 수 있음)")
        return 0

    from collections import Counter
    lv = Counter(r["level"] for r in results)
    print(f"[lint] {args.doc.name} — 개념 {len(results)}개 "
          f"(쉬움 {lv['쉬움']}·보통 {lv['보통']}·어려움 {lv['어려움']}), "
          f"설명 보강 권장 {n_thin}개\n")
    print("  목표: 즉시 이해. 쉬운 건 얇아도 정상, '어려운데 구조가 약한' 것만 ⚠.\n")
    for r in results:
        mark = "⚠" if r["needs_work"] else "·"
        line = f"  {mark} [{r['level']}] {r['title'][:44]}"
        if r["needs_work"]:
            line += f"  ← 이해 도움: {', '.join(r['helps']) or '구조 정리'}"
        print(line)

    if n_thin and args.strict:
        print(f"\n✗ 어려운데 설명이 약한 개념 {n_thin}개 — 구조(도해·단계·why) 보강 필요(--strict).")
        return 1
    print(f"\n{'✓ 난이도 대비 설명이 적절합니다.' if n_thin == 0 else '△ ⚠ 개념만 보강 권장 — 어려운데 벽글인 것. 쉬운 개념은 그대로 두세요.'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
