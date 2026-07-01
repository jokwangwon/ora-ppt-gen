#!/usr/bin/env python3
"""관리 대시보드 생성 — 문서·일차·PPT를 한 페이지로.

사람이 소유하는 검토 상태(review_status.json)와, 매번 재계산하는 자동 지표
(난이도 분포·린트·얼버무림·검은박스·슬라이드수)를 병합해 assets/dashboard.html 을 낸다.
상태 변경은 review.py 로 하고, 이 스크립트는 '보기'만 만든다(상태를 덮어쓰지 않음).

사용법:
    python build_dashboard.py                    # assets/·days/·out/ 스캔 → assets/dashboard.html
    python build_dashboard.py --out assets/dashboard.html
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from html import escape
from pathlib import Path

import lint_authoring as la
import lint_vagueness as lv
import sync_and_verify as sv

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "review_status.json"

# 상태 → (라벨, 색)
STATUS = {
    "reviewed": ("✅ 검토완료", "#16803d", "#dcfce7"),
    "reviewing": ("● 검토중", "#b45309", "#fef3c7"),
    "unreviewed": ("· 미검토", "#64748b", "#f1f5f9"),
}
TOPICS = {  # 문서 → 주제 배지
    "sql_tuning.html": "SQL·실행계획",
    "buffer_cache_dbwr_checkpoint.html": "버퍼·DBWR",
    "rman_recovery.html": "백업·복구",
    "guide_62_68.html": "내부구조",
}


def _load_status() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {"docs": {}, "days": {}}


def _blackbox(html: str) -> list[str]:
    defined = sv._defined_classes(html)
    used: set[str] = set()
    for svg in re.findall(r"<svg.*?</svg>", html, re.S):
        for c in re.findall(r'class="([^"]+)"', svg):
            used.update(c.split())
    return sorted(used - defined)


def _vague_count(path: Path) -> int:
    try:
        return sum(len(lv.scan_text(text)) for _, text in lv.extract_units(path))
    except Exception:
        return -1


def _doc_rows(status: dict) -> list[dict]:
    rows = []
    for p in sorted(ROOT.glob("assets/*.html")):
        if "study_hub" in p.name or p.name == "dashboard.html":
            continue
        html = p.read_text(encoding="utf-8")
        results, need = la.lint(p, 4)
        lvl = Counter(r["level"] for r in results)
        st = status.get("docs", {}).get(p.name, {})
        rows.append({
            "name": p.name,
            "topic": TOPICS.get(p.name, ""),
            "concepts": len(results),
            "easy": lvl["쉬움"], "mid": lvl["보통"], "hard": lvl["어려움"],
            "need": need,
            "vague": _vague_count(p),
            "blackbox": _blackbox(html),
            "status": st.get("status", "unreviewed"),
            "reviewed_at": st.get("reviewed_at", ""),
            "note": st.get("note", ""),
            "accuracy": st.get("accuracy", {}),
        })
    return rows


def _day_rows(status: dict) -> list[dict]:
    rows = []
    days_dir = ROOT / "days"
    if not days_dir.exists():
        return rows
    for d in sorted(days_dir.iterdir(), key=lambda x: (len(x.name), x.name)):
        if not d.is_dir():
            continue
        st = status.get("days", {}).get(d.name, {})
        rows.append({
            "day": d.name,
            "quiz": (d / "quiz.json").exists(),
            "deck": (d / f"{d.name}.slides.json").exists(),
            "status": st.get("status", "unreviewed"),
            "note": st.get("note", ""),
        })
    return rows


def _deck_rows() -> list[dict]:
    rows = []
    out = ROOT / "out"
    if not out.exists():
        return rows
    for spec in sorted(out.glob("*.slides.json")):
        try:
            n = len(json.loads(spec.read_text(encoding="utf-8")).get("slides", []))
        except Exception:
            n = 0
        pptx = out / f"{spec.stem.replace('.slides','')}.pptx"
        rows.append({"name": spec.stem.replace(".slides", ""), "slides": n, "built": pptx.exists()})
    return rows


def _chip(status_key: str) -> str:
    label, fg, bg = STATUS.get(status_key, STATUS["unreviewed"])
    return f'<span class="chip" style="color:{fg};background:{bg}">{escape(label)}</span>'


def render(status: dict) -> str:
    docs = _doc_rows(status)
    days = _day_rows(status)
    decks = _deck_rows()
    n_reviewed = sum(1 for d in docs if d["status"] == "reviewed")

    def bar(e, m, h):
        tot = max(e + m + h, 1)
        parts = []
        for w, c in ((e, "#94a3b8"), (m, "#f59e0b"), (h, "#C74634")):
            if w:
                parts.append(f'<span style="width:{w/tot*100:.0f}%;background:{c}"></span>')
        return f'<span class="bar" title="쉬움 {e}·보통 {m}·어려움 {h}">{"".join(parts)}</span>'

    out = []
    out.append("""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>학습 자료 관리 대시보드</title><style>
:root{--ink:#1E293B;--red:#C74634;--muted:#64748B;--line:#E2E8F0;--card:#F1F5F9}
*{box-sizing:border-box}body{margin:0;font-family:"맑은 고딕",system-ui,sans-serif;color:var(--ink);background:#fff}
header{background:var(--ink);color:#fff;padding:22px 28px}
header .m{color:#fff;opacity:.55;font-size:12px;letter-spacing:.18em;font-weight:700}
header h1{margin:4px 0 0;font-size:22px}header .sub{color:#cbd5e1;font-size:13px;margin-top:6px}
.wrap{padding:22px 28px;max-width:1200px}
h2{font-size:15px;margin:26px 0 10px;padding-left:10px;border-left:4px solid var(--red)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px;background:#fafbfc}
tr:hover td{background:#fafbfc}
.chip{font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:999px;white-space:nowrap}
.bar{display:inline-flex;width:96px;height:9px;border-radius:5px;overflow:hidden;background:var(--card);vertical-align:middle}
.bar span{display:block;height:100%}
.warn{color:var(--red);font-weight:700}.ok{color:#16803d}
.mono{font-family:Consolas,monospace;font-size:12px}
.note{color:var(--muted);font-size:12px}
a{color:var(--red);text-decoration:none;font-weight:600}a:hover{text-decoration:underline}
.small{color:var(--muted);font-size:11.5px}
.legend{margin-top:6px;font-size:11.5px;color:#cbd5e1}
</style></head><body>""")
    out.append('<header><div class="m">ORACLE DBA · STUDY OPS</div>'
               '<h1>학습 자료 관리 대시보드</h1>'
               f'<div class="sub">문서 {len(docs)} · 검토완료 {n_reviewed}/{len(docs)} · '
               f'일차 {len(days)} · 덱 {len(decks)}</div>'
               '<div class="legend">상태는 review_status.json(사람 소유) · 지표는 생성 때 재계산 · '
               'PPTX는 세션 빌드물이라 out/에 있을 때만 열림</div></header>')
    out.append('<div class="wrap">')

    def acc_cell(a: dict) -> str:
        if not a or not a.get("checked"):
            return '<span class="warn" title="사실 오류 미검증">⚠ 미검증</span>'
        iss = a.get("issues", 0)
        tip = escape(f'{a.get("method","")} · {a.get("at","")} · 발견/수정 {iss}건')
        badge = f'✔ 검증({iss})' if iss else '✔ 검증'
        return f'<span class="ok" title="{tip}">{badge}</span>'

    # 문서
    out.append("<h2>문서</h2>"
               '<p class="small">‘검토’=사람 확인 · ‘정확성’=사실 오류 LLM 검증. '
               '원본은 수업 중 직접 작성해 사실 오류가 있을 수 있으므로 정확성 검증을 따로 표시합니다.</p>'
               "<table><tr>"
               "<th>문서</th><th>주제</th><th>검토</th><th>정확성(사실검증)</th><th>난이도(쉬움·보통·어려움)</th>"
               "<th>보강권장</th><th>얼버무림</th><th>검은박스</th><th>확인일</th><th></th></tr>")
    for d in docs:
        need = f'<span class="warn">{d["need"]}</span>' if d["need"] else '<span class="ok">0</span>'
        vague = "-" if d["vague"] < 0 else (f'<span class="warn">{d["vague"]}</span>' if d["vague"] else "0")
        bb = f'<span class="warn">{len(d["blackbox"])}</span>' if d["blackbox"] else '<span class="ok">0</span>'
        out.append("<tr>"
                   f'<td class="mono">{escape(d["name"])}</td>'
                   f'<td class="small">{escape(d["topic"])}</td>'
                   f'<td>{_chip(d["status"])}</td>'
                   f'<td>{acc_cell(d["accuracy"])}</td>'
                   f'<td>{bar(d["easy"], d["mid"], d["hard"])} <span class="small">{d["concepts"]}개</span></td>'
                   f'<td>{need}</td><td>{vague}</td><td>{bb}</td>'
                   f'<td class="small">{escape(d["reviewed_at"])}</td>'
                   f'<td><a href="{escape(d["name"])}">열기</a></td></tr>')
        if d["note"]:
            out.append(f'<tr><td></td><td colspan="9" class="note">↳ {escape(d["note"])}</td></tr>')
    out.append("</table>")

    # 일차
    out.append("<h2>일차 저작물</h2>")
    if days:
        out.append("<table><tr><th>일차</th><th>문제</th><th>일차덱</th><th>상태</th><th>메모</th></tr>")
        for r in days:
            q = '<span class="ok">있음</span>' if r["quiz"] else '<span class="small">-</span>'
            dk = '<span class="ok">있음</span>' if r["deck"] else '<span class="small">-</span>'
            out.append(f'<tr><td class="mono">{escape(r["day"])}일차</td><td>{q}</td><td>{dk}</td>'
                       f'<td>{_chip(r["status"])}</td><td class="note">{escape(r["note"])}</td></tr>')
        out.append("</table>")
    else:
        out.append('<p class="small">아직 없음 — <span class="mono">days/&lt;N&gt;/</span> 저작 시 표시됩니다.</p>')

    # 덱
    out.append("<h2>PPT 덱</h2>")
    if decks:
        out.append("<table><tr><th>덱</th><th>슬라이드</th><th>빌드</th></tr>")
        for r in decks:
            b = '<span class="ok">완료</span>' if r["built"] else '<span class="small">스펙만(빌드 필요)</span>'
            out.append(f'<tr><td class="mono">{escape(r["name"])}</td><td>{r["slides"]}장</td><td>{b}</td></tr>')
        out.append("</table>")
    else:
        out.append('<p class="small">out/ 비어있음 — <span class="mono">make_day</span> 또는 '
                   '<span class="mono">make.py</span>로 생성됩니다.</p>')

    out.append('<p class="small" style="margin-top:28px">생성: '
               '<span class="mono">python build_dashboard.py</span> · '
               '상태 변경: <span class="mono">python review.py mark &lt;문서&gt; --status reviewed</span></p>')
    out.append("</div></body></html>")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="관리 대시보드 생성")
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "dashboard.html")
    args = ap.parse_args(argv)
    status = _load_status()
    html = render(status)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"[dashboard] → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
