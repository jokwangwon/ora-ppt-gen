#!/usr/bin/env python3
"""자료실 생성 — 문서·허브·발표 덱을 한 페이지(index.html)로 묶어 공유·다운로드.

GitHub Pages(리포 루트)로 배포하면 누구나 URL로 접근한다:
  - 문서(assets/*.html)는 그 자리에서 보기
  - 발표 덱·대본은 files/ 로 복사해 바로 다운로드

관리 = 파일 추가/갱신 후 이 스크립트 재실행(멱등). 상태는 review_status.json(사람 소유)에서 읽는다.

사용법:
    python build_library.py                 # out/ 덱 → files/ 복사 + index.html 생성
    python build_library.py --no-copy       # 복사 없이 index.html 만 갱신
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "out"
FILES = ROOT / "files"
STATUS_FILE = ROOT / "review_status.json"

# 문서 → (주제 배지, 사람이 읽는 제목)
DOCS = {
    "guide_62_68.html": ("내부구조", "DBA 62–68 완전정복 가이드 (내부구조편)"),
    "sql_tuning.html": ("SQL·실행계획", "SQL 튜닝편 — 실행계획 읽기·인덱스·조인"),
    "buffer_cache_dbwr_checkpoint.html": ("버퍼·DBWR", "버퍼 캐시 · DBWR · 체크포인트"),
    "rman_recovery.html": ("백업·복구", "RMAN 복구 치트시트 (운영편)"),
}
# 덱 파일명 → 사람이 읽는 라벨
DECK_LABELS = {
    "day68.pptx": "68일차 — row migration · ITL · full scan",
    "day72.pptx": "72일차 — 실행계획 숫자 읽기 · 조인 · 인덱스",
    "sql_tuning.pptx": "SQL 튜닝편 (문서 전체 덱)",
    "guide_62_68.pptx": "내부구조편 (문서 전체 덱)",
    "buffer_cache_dbwr_checkpoint.pptx": "버퍼 캐시·DBWR (문서 전체 덱)",
    "rman_recovery.pptx": "RMAN 복구 (문서 전체 덱)",
}
STATUS_BADGE = {
    "reviewed": ("검토완료", "#16803d", "#dcfce7"),
    "reviewing": ("검토중", "#b45309", "#fef3c7"),
    "unreviewed": ("미검토", "#64748b", "#f1f5f9"),
    "published": ("게시", "#1d4ed8", "#dbeafe"),
}


def fsize(p: Path) -> str:
    b = p.stat().st_size
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b/1024:.0f} KB"
    return f"{b/1024/1024:.1f} MB"


def fdate(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")


def load_status() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {"docs": {}, "days": {}}


def copy_artifacts() -> list[Path]:
    """out/ 의 덱·대본을 files/ 로 복사(멱등). 복사된 파일 목록 반환."""
    FILES.mkdir(exist_ok=True)
    copied = []
    for pat in ("*.pptx", "*.notes.md"):
        for src in sorted(OUT.glob(pat)):
            dst = FILES / src.name
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def badge(text: str, fg: str, bg: str) -> str:
    return f'<span class="badge" style="color:{fg};background:{bg}">{escape(text)}</span>'


def render(status: dict) -> str:
    docs_status = status.get("docs", {})
    days_status = status.get("days", {})

    # --- 문서 카드 ---
    doc_cards = []
    for fn, (topic, title) in DOCS.items():
        if not (ASSETS / fn).exists():
            continue
        st = docs_status.get(fn, {})
        s = st.get("status", "unreviewed")
        lab, fg, bg = STATUS_BADGE.get(s, STATUS_BADGE["unreviewed"])
        acc = st.get("accuracy", {})
        acc_txt = ""
        if acc.get("checked"):
            iss = acc.get("issues", 0)
            acc_txt = f'<span class="mini">정확성 검증 · {"이슈 " + str(iss) + "건 교정" if iss else "이슈 없음"}</span>'
        doc_cards.append(f"""
      <div class="card">
        <div class="ctop"><span class="topic">{escape(topic)}</span>{badge(lab, fg, bg)}</div>
        <div class="ctitle">{escape(title)}</div>
        {acc_txt}
        <div class="actions">
          <a class="btn" href="assets/{fn}" target="_blank">문서 보기 →</a>
          <a class="btn ghost" href="assets/{fn}" download>HTML 내려받기</a>
        </div>
      </div>""")

    # --- 발표 덱 카드 (files/ 스캔) ---
    deck_rows = []
    if FILES.exists():
        for p in sorted(FILES.glob("*.pptx")):
            label = DECK_LABELS.get(p.name, p.stem)
            notes = FILES / (p.stem + ".notes.md")
            notes_link = (f'<a class="btn ghost" href="files/{notes.name}" download>대본(.md)</a>'
                          if notes.exists() else "")
            deck_rows.append(f"""
      <div class="card">
        <div class="ctop"><span class="topic dk">발표 덱</span><span class="mini">{fsize(p)} · {fdate(p)}</span></div>
        <div class="ctitle">{escape(label)}</div>
        <div class="actions">
          <a class="btn" href="files/{p.name}" download>PPTX 내려받기 ↓</a>
          {notes_link}
        </div>
      </div>""")
    if not deck_rows:
        deck_rows.append('<div class="empty">아직 게시된 덱이 없습니다. <code>python build_library.py</code> 로 out/ 덱을 올리세요.</div>')

    updated = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Oracle DBA 학습 자료실</title>
<style>
:root{{--bg:#F6F7F9;--panel:#fff;--ink:#161B22;--muted:#5A6472;--line:#E4E8EE;--accent:#C74634;--accent2:#1C7E8C}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:'Pretendard',system-ui,-apple-system,sans-serif;line-height:1.6}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 20px}}
header{{background:linear-gradient(135deg,#20303F,#2C3742);color:#fff;padding:44px 0 38px}}
header .kick{{font-family:ui-monospace,monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#9fb0bf}}
header h1{{margin:8px 0 6px;font-size:30px}}
header p{{margin:0;color:#cdd6df;font-size:15px}}
main{{padding:30px 0 60px}}
h2.sec{{font-size:16px;margin:34px 0 4px;display:flex;align-items:center;gap:8px}}
h2.sec .n{{font-family:ui-monospace,monospace;font-size:12px;color:var(--accent);border:1px solid #e7c3bd;border-radius:7px;padding:3px 8px}}
.sub{{color:var(--muted);font-size:13.5px;margin:2px 0 14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 16px;display:flex;flex-direction:column;gap:8px}}
.ctop{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.topic{{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;color:var(--accent2);background:#e1f1f3;border:1px solid #b6dde2;border-radius:7px;padding:3px 8px}}
.topic.dk{{color:var(--accent);background:#fbe7de;border-color:#e7c3bd}}
.badge{{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;border-radius:7px;padding:3px 8px}}
.ctitle{{font-size:14.5px;font-weight:700;line-height:1.4}}
.mini{{font-family:ui-monospace,monospace;font-size:11.5px;color:var(--muted)}}
.actions{{display:flex;gap:7px;flex-wrap:wrap;margin-top:2px}}
.btn{{font-size:12.5px;font-weight:700;text-decoration:none;color:#fff;background:var(--accent);border:1px solid var(--accent);border-radius:9px;padding:8px 12px}}
.btn.ghost{{color:var(--ink);background:var(--panel);border-color:var(--line)}}
.btn:hover{{opacity:.9}}
.empty{{color:var(--muted);border:1px dashed var(--line);border-radius:12px;padding:22px;text-align:center;font-size:13.5px}}
.big{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.big .card{{flex-direction:row;align-items:center;justify-content:space-between}}
footer{{color:var(--muted);font-size:12.5px;padding:24px 0 50px;text-align:center}}
@media(max-width:640px){{.big{{grid-template-columns:1fr}}}}
</style></head>
<body>
<header><div class="wrap">
  <div class="kick">Oracle DBA Bootcamp · 학습 자료실</div>
  <h1>Oracle DBA 학습 자료실</h1>
  <p>수업에서 만든 학습 문서 · 발표 덱 · 문제 허브를 한곳에서 보고 내려받습니다.</p>
</div></header>
<main class="wrap">

  <h2 class="sec"><span class="n">01</span>학습 허브 & 관리</h2>
  <div class="sub">문제 풀이 · 용어 검색 · 오답노트가 있는 허브와, 진행 상태 대시보드.</div>
  <div class="big">
    <div class="card">
      <div><div class="ctitle">📚 학습 허브</div><div class="mini">객관식·서술형·실행계획·용어 검색·오답노트</div></div>
      <a class="btn" href="assets/study_hub_full.html" target="_blank">열기 →</a>
    </div>
    <div class="card">
      <div><div class="ctitle">📊 관리 대시보드</div><div class="mini">검토·정확성·난이도·린트 상태</div></div>
      <a class="btn ghost" href="assets/dashboard.html" target="_blank">열기 →</a>
    </div>
  </div>

  <h2 class="sec"><span class="n">02</span>학습 문서</h2>
  <div class="sub">소스 오브 트루스 — 그 자리에서 보거나 HTML로 내려받으세요.</div>
  <div class="grid">{''.join(doc_cards)}
  </div>

  <h2 class="sec"><span class="n">03</span>발표 자료 (덱 · 대본)</h2>
  <div class="sub">발표용 PPTX와 발표 대본(무료 PowerPoint에서 노트가 안 보일 때).</div>
  <div class="grid">{''.join(deck_rows)}
  </div>

</main>
<footer><div class="wrap">자동 생성 · 최종 갱신 {updated} · <code>build_library.py</code> — 파일 추가 후 재실행하면 목록이 갱신됩니다.</div></footer>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="자료실(index.html) 생성")
    ap.add_argument("--out", type=Path, default=ROOT / "index.html")
    ap.add_argument("--no-copy", action="store_true", help="out/ → files/ 복사 생략")
    args = ap.parse_args(argv)

    if not args.no_copy:
        copied = copy_artifacts()
        print(f"[library] files/ 로 복사: {len(copied)}개")
    status = load_status()
    args.out.write_text(render(status), encoding="utf-8")
    print(f"[library] → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
