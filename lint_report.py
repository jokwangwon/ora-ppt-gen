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
    rows = []           # 요약표
    backlog = []        # (score, doc, title, type, missing)
    issues = []         # 구조/검은박스
    for p in docs:
        html = p.read_text(encoding="utf-8")
        results, _ = la.lint(p, 4)
        if not results:
            issues.append(f"- `{p.name}` — h3.blk 구조 밖(추출·평가 불가)")
            rows.append((p.name, 0, 0, None, 0))
            continue
        mech = [r for r in results if r["type"] == "mechanism"]
        avg = sum(r["score"] for r in mech) / len(mech) if mech else 0
        thin = [r for r in mech if r["score"] < 4]
        rows.append((p.name, len(results), len(mech), avg, len(thin)))
        for r in thin:
            backlog.append((r["score"], p.name, r["title"], r["type"], r["missing"]))
        bb = blackbox(html)
        if bb:
            issues.append(f"- `{p.name}` — 검은박스 후보(미정의 SVG 클래스): {bb}")

    backlog.sort(key=lambda x: (x[0], x[1]))  # 점수 낮은 순

    out = ["# 허브 품질 평가 리포트", ""]
    out.append("> 점수는 **풍부화 요소(다이어그램·비유·실측·서사·깊이)** 존재 여부의 대리 지표입니다.")
    out.append("> 정확성·명료성 판정이 아니며, 참조표·예제 개념은 얇아도 정상입니다.\n")

    out.append("## 요약 (원리 개념 기준)\n")
    out.append(f"| 문서 | 개념 | 원리 | 원리 평균 /{MAX} | 보강대상(원리<4) |")
    out.append("|------|-----:|-----:|-----:|-----:|")
    tot_mech = tot_thin = 0
    for name, n, m, avg, thin in rows:
        avg_s = "—" if not m else f"{avg:.1f}"
        out.append(f"| {name} | {n} | {m} | {avg_s} | {thin} |")
        tot_mech += m
        tot_thin += thin
    pct = (tot_thin / tot_mech * 100) if tot_mech else 0
    out.append(f"| **합계** | | **{tot_mech}** | | **{tot_thin} ({pct:.0f}%)** |\n")

    out.append("## 보강 백로그 (원리 개념, 점수 낮은 순)\n")
    out.append("0/7·1/7 부터 대화로 보강 권장 — 원문 사실은 그대로, 다이어그램·비유·서사만 추가.\n")
    out.append(f"| 점수 | 문서 | 개념 | 보강할 것 |")
    out.append("|-----:|------|------|------|")
    for score, name, title, typ, missing in backlog:
        out.append(f"| {score}/{MAX} | {name} | {title[:38]} | {', '.join(missing)} |")

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
