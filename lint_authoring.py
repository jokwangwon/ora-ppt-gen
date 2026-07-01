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
    missing = [label for key, _, label in CHECKS if not flags[key]]
    return {"title": title, "score": score, "flags": flags, "missing": missing}


def lint(doc_path: Path, min_score: int) -> tuple[list[dict], int]:
    soup = BeautifulSoup(doc_path.read_text(encoding="utf-8"), "lxml")
    results = []
    for h3 in soup.find_all("h3", class_="blk"):
        results.append(score_concept(_text(h3), _concept_html(h3)))
    thin = [r for r in results if r["score"] < min_score]
    return results, len(thin)


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

    avg = sum(r["score"] for r in results) / len(results)
    print(f"[lint] {args.doc.name} — 개념 {len(results)}개, 평균 {avg:.1f}/{MAX_SCORE}, "
          f"얇음(<{args.min}) {n_thin}개\n")
    for r in results:
        mark = "⚠" if r["score"] < args.min else "·"
        line = f"  {mark} [{r['score']}/{MAX_SCORE}] {r['title'][:44]}"
        if r["score"] < args.min:
            line += f"  ← 보강: {', '.join(r['missing'])}"
        print(line)

    if n_thin and args.strict:
        print(f"\n✗ 얇은 개념 {n_thin}개 — 정답지 작법으로 보강 필요(--strict).")
        return 1
    print(f"\n{'✓ 모든 개념이 기준 충족.' if n_thin == 0 else '△ 위 개념을 대화로 보강 권장(다이어그램/실측/서사).'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
