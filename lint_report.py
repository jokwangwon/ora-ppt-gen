#!/usr/bin/env python3
"""허브 품질 평가 리포트 — 전 문서 감사를 한 장(markdown)으로.

lint_authoring 의 개념 점수를 여러 문서에 걸쳐 모아, 요약표 + 보강 백로그
(원리 개념 점수 낮은 순)를 낸다. sync_and_verify 의 검은박스 검사도 곁들인다.

이 점수는 '풍부화 요소가 있느냐'의 대리 지표이지 정확성·명료성 판정이 아니다.
= 품질 낙제표가 아니라 **풍부화 기회 감사**.

사용법:
    python lint_report.py                       # assets/*.html → out/quality_report.md
    python lint_report.py --dir assets --out out/quality_report.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import lint_authoring as la
import sync_and_verify as sv

MAX = la.MAX_SCORE
T = {"mechanism": "원리", "reference": "참조", "example": "예제"}


def blackbox(doc_html: str) -> list[str]:
    defined = sv._defined_classes(doc_html)
    used: set[str] = set()
    for svg in re.findall(r"<svg.*?</svg>", doc_html, re.S):
        for c in re.findall(r'class="([^"]+)"', svg):
            used.update(c.split())
    return sorted(used - defined)


def build_report(docs: list[Path]) -> str:
    from collections import Counter
    rows = []           # 요약표
    backlog = []        # (doc, title, level, helps) — 어려운데 구조 약한 것만
    issues = []         # 구조/검은박스
    for p in docs:
        html = p.read_text(encoding="utf-8")
        results, need = la.lint(p, 4)
        if not results:
            issues.append(f"- `{p.name}` — h3.blk 구조 밖(추출·평가 불가)")
            rows.append((p.name, 0, Counter(), 0))
            continue
        lv = Counter(r["level"] for r in results)
        rows.append((p.name, len(results), lv, need))
        for r in results:
            if r["needs_work"]:
                backlog.append((p.name, r["title"], r["level"], r["helps"]))
        bb = blackbox(html)
        if bb:
            issues.append(f"- `{p.name}` — 검은박스 후보(미정의 SVG 클래스): {bb}")

    out = ["# 허브 품질 평가 리포트", ""]
    out.append("> 목표는 **즉시 이해**입니다. 난이도에 맞춰 설명 깊이를 매칭합니다 —")
    out.append("> 쉬운 개념은 얇아도 정상이고, **'어려운데 구조가 약한(벽글)' 개념만** 보강 대상입니다.")
    out.append("> (기계적 지표라 대략치입니다. 실제 '곧바로 이해되나'는 사람/LLM이 읽어 판단해야 정확합니다.)\n")

    out.append("## 요약 (난이도 분포)\n")
    out.append("| 문서 | 개념 | 쉬움 | 보통 | 어려움 | 설명 보강 권장 |")
    out.append("|------|-----:|-----:|-----:|-----:|-----:|")
    tot = tot_need = 0
    for name, n, lv, need in rows:
        out.append(f"| {name} | {n} | {lv['쉬움']} | {lv['보통']} | {lv['어려움']} | {need} |")
        tot += n
        tot_need += need
    out.append(f"| **합계** | **{tot}** | | | | **{tot_need}** |\n")

    if backlog:
        out.append("## 보강 권장 (어려운데 구조가 약한 개념)\n")
        out.append("원문 사실은 그대로, 이해를 돕는 구조(도해/단계/why)만 더한다.\n")
        out.append("| 문서 | 개념 | 난이도 | 이해 도움 |")
        out.append("|------|------|------|------|")
        for name, title, lvl, helps in backlog:
            out.append(f"| {name} | {title[:40]} | {lvl} | {', '.join(helps) or '구조 정리'} |")
    else:
        out.append("## 보강 권장\n\n없음 — 난이도 대비 설명이 대체로 적절합니다. "
                   "(정밀 판단은 개념별 'LLM 가독성 리뷰' 권장 — 아래 참고)\n")

    out.append("\n## 더 정확한 평가 — LLM 가독성 리뷰\n")
    out.append("기계적 지표는 '구조 유무'만 본다. **'처음 보는 사람이 곧바로 이해되나'** 는 "
               "개념을 실제로 읽어야 안다. 대화로 개념을 하나씩 읽어 *어디서 걸리는지 → 최소 수정*을 "
               "짚는 방식이 목표에 가장 부합한다.")

    if issues:
        out.append("\n## 구조·검증 이슈\n")
        out.extend(issues)

    out.append("\n---\n_생성: `python lint_report.py`_")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="허브 품질 평가 리포트")
    ap.add_argument("--dir", type=Path, default=Path("assets"), help="문서 폴더")
    ap.add_argument("--out", type=Path, default=Path("out/quality_report.md"))
    args = ap.parse_args(argv)

    docs = sorted(p for p in args.dir.glob("*.html") if "study_hub" not in p.name)
    if not docs:
        print(f"[report] 문서 없음: {args.dir}/*.html"); return 1
    md = build_report(docs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"[report] {len(docs)}개 문서 → {args.out}")
    print("\n" + md.split("## 보강 백로그")[0])  # 요약까지 콘솔에
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
