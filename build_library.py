#!/usr/bin/env python3
"""자료실 생성 — 문서·허브·발표 덱을 한 페이지(index.html)로 묶어 공유·다운로드.

디자인은 블로그(Chirpy Jekyll 테마) 룩을 참고: 좌측 사이드바(아바타·사이트명·네비)
+ 라이트/다크 토글 + 둥근 카드 + 파란 액센트. index.html 은 자체완결(정적)이라
GitHub Pages(리포 루트)로 그대로 배포된다.

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
import re
import shutil
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from inject_compare import md2html

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "out"
FILES = ROOT / "files"
REVIEWS = ROOT / "reviews"
STATUS_FILE = ROOT / "review_status.json"

# 일일 복습 페이지(자료실 하단 일지) 템플릿
REVIEW_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{day}일차 복습 시트</title>
<style>
body{{margin:0;background:#f6f8fa;color:#34343c;font-family:'Lato','Noto Sans KR',-apple-system,sans-serif;line-height:1.7}}
.wrap{{max-width:820px;margin:0 auto;padding:36px 22px 80px}}
.top{{font-size:12px;color:#7c828a;margin-bottom:6px}}
h2{{color:#1b1b1f;font-size:22px;margin:4px 0 14px}}
h3{{color:#1b1b1f;font-size:16px;margin:26px 0 8px;padding-top:14px;border-top:1px solid #e7ebef}}
h4{{font-size:14px;color:#7c828a;margin:16px 0 4px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(23,32,50,.05)}}
th{{text-align:left;font-size:12px;color:#7c828a;padding:9px 12px;border-bottom:2px solid #e7ebef;background:#fbfcfd}}
td{{padding:8px 12px;border-bottom:1px solid #eef1f4;vertical-align:top}}
code{{font-family:ui-monospace,monospace;font-size:.85em;background:#eef1f4;padding:1px 6px;border-radius:5px}}
.note{{background:#e9f2fb;border:1px solid #cfe0fb;border-radius:11px;padding:11px 14px;font-size:13px;color:#1f4f9e;margin:10px 0}}
hr{{border:none;border-top:1px dashed #e7ebef;margin:18px 0}}
ul,ol{{padding-left:22px}}
.back{{position:fixed;right:16px;bottom:16px;background:#1d7dcc;color:#fff;font:700 13px/1 system-ui;text-decoration:none;padding:11px 15px;border-radius:24px;box-shadow:0 4px 14px rgba(0,0,0,.22)}}
</style></head><body><div class="wrap">
<div class="top">Oracle DBA 학습 자료실 · 일일 복습</div>
{body}
</div><a class="back" href="../index.html">&larr; 자료실</a></body></html>
"""


def build_review_pages() -> list[tuple[int, str]]:
    """days/*/compare.md → reviews/dayN.html. (일차, 축 한 줄) 목록 반환."""
    REVIEWS.mkdir(exist_ok=True)
    out = []
    for p in sorted((ROOT / "days").glob("*/compare.md")):
        if not p.parent.name.isdigit():
            continue
        day = int(p.parent.name)
        md = p.read_text(encoding="utf-8")
        m = re.search(r"\[오늘의 축\][^\n]*\n+>\s*\*\*(.+?)\*\*", md)
        axis = m.group(1) if m else ""
        body = md2html(md).replace("href='assets/", "href='../assets/")  # reviews/에서의 상대경로
        (REVIEWS / f"day{day}.html").write_text(
            REVIEW_PAGE.format(day=day, body=body), encoding="utf-8")
        out.append((day, axis))
    return out

# 문서 → (주제 배지, 사람이 읽는 제목)
DOCS = {
    "guide_62_68.html": ("내부구조", "DBA 완전정복 가이드 (내부구조편)"),
    "sql_tuning.html": ("SQL·실행계획", "SQL 튜닝편 — 실행계획 읽기·인덱스·조인"),
    "buffer_cache_dbwr_checkpoint.html": ("버퍼·DBWR", "버퍼 캐시 · DBWR · 체크포인트"),
    "rman_recovery.html": ("백업·복구", "RMAN 복구 치트시트 (운영편)"),
}
# 덱 파일명 → 사람이 읽는 라벨
DECK_LABELS = {
    "day68.pptx": "68일차 — row migration · ITL · full scan",
    "day72.pptx": "72일차 — 실행계획 숫자 읽기 · 조인 · 인덱스",
    "day73.pptx": "73일차 — NL 조인 · 조인 순서와 진입 인덱스",
    "day74.pptx": "74일차 — 조인 3형제 · Sort Merge와 Hash",
    "day75.pptx": "75일차 — 쿼리 변환 · filter↔unnest · 조인 제거",
    "day76.pptx": "76일차 — 쿼리 변환 2탄 · OR-expansion · push_subq · bloom",
    "day77.pptx": "77일차 — 조건절 이동 · 집계→분석함수 · 옵티마이저 개막",
    "day78.pptx": "78일차 — E-Rows의 산수 · 히스토그램 · 통계 수명주기",
    "day79.pptx": "79일차 — 커서 공유 · bind peeking · 파티션과 pruning",
    "day80.pptx": "80일차 — 부분범위처리 · arraysize · 파티션 관리(결석 보강)",
    "day81.pptx": "81일차 — 파티션 인덱스(local/global) · Data Pump · 병렬 개막",
    "day82.pptx": "82일차 — 병렬 심화: IN-OUT · PQ Distrib · gby_pushdown · 파티션 wise 조인",
    "sql_tuning.pptx": "SQL 튜닝편 (문서 전체 덱)",
    "guide_62_68.pptx": "내부구조편 (문서 전체 덱)",
    "buffer_cache_dbwr_checkpoint.pptx": "버퍼 캐시·DBWR (문서 전체 덱)",
    "rman_recovery.pptx": "RMAN 복구 (문서 전체 덱)",
}
STATUS_BADGE = {
    "reviewed": ("검토완료", "#1a7f37", "#dafbe1"),
    "reviewing": ("검토중", "#9a6700", "#fff8c5"),
    "unreviewed": ("미검토", "#636c76", "#eef1f4"),
    "published": ("게시", "#0969da", "#ddf4ff"),
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
    """out/ 의 덱(PPTX)만 files/ 로 복사(멱등). 발표 대본(.md)은 개인용이라 제외.
    혹시 예전에 복사된 대본이 있으면 정리한다. 복사된 파일 목록 반환."""
    FILES.mkdir(exist_ok=True)
    for stray in FILES.glob("*.notes.md"):  # 개인용 대본은 자료실에서 제거
        stray.unlink()
    copied = []
    for src in sorted(OUT.glob("*.pptx")):
        dst = FILES / src.name
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def pill(text: str, fg: str, bg: str) -> str:
    return f'<span class="pill" style="color:{fg};background:{bg}">{escape(text)}</span>'


def render(status: dict, recaps: list[tuple[int, str]] | None = None) -> str:
    docs_status = status.get("docs", {})

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
            acc_txt = f'<p class="meta">정확성 검증 · {"이슈 " + str(iss) + "건 교정" if iss else "이슈 없음"}</p>'
        doc_cards.append(f"""
        <article class="card">
          <div class="tags"><span class="pill topic">{escape(topic)}</span>{pill(lab, fg, bg)}</div>
          <h3 class="ctitle">{escape(title)}</h3>
          {acc_txt}
          <div class="acts">
            <a class="btn" href="assets/{fn}">문서 보기</a>
            <a class="btn ghost" href="assets/{fn}" download>HTML</a>
          </div>
        </article>""")

    # --- 발표 덱: 검토된 최신(day72)만 정식 노출, 나머지 미검토는 접어서 소형 ---
    FEATURED = {"day72.pptx"}  # 검토 완료·최신 덱만 눈에 띄게
    featured_cards, misc_rows = [], []
    if FILES.exists():
        for p in sorted(FILES.glob("*.pptx")):
            label = DECK_LABELS.get(p.name, p.stem)
            if p.name in FEATURED:
                featured_cards.append(f"""
        <article class="card">
          <div class="tags"><span class="pill topic dk">발표 덱</span>{pill("72일차 · 최신", "#9a6700", "#fff8c5")}<span class="meta">{fsize(p)} · {fdate(p)}</span></div>
          <h3 class="ctitle">{escape(label)}</h3>
          <div class="acts">
            <a class="btn" href="files/{p.name}" download>PPTX 내려받기</a>
          </div>
        </article>""")
            else:
                misc_rows.append(f"""
          <li class="mrow"><span class="mtitle">{escape(label)}</span>"""
                                 f"""<span class="pill mini warn">미검토</span>"""
                                 f"""<span class="meta">{fsize(p)} · {fdate(p)}</span>"""
                                 f"""<a class="mdl" href="files/{p.name}" download>PPTX ↓</a></li>""")
    featured_html = "".join(featured_cards) or '<div class="empty">아직 검토 완료된 덱이 없습니다.</div>'
    misc_html = ""
    if misc_rows:
        misc_html = (f'<details class="misc"><summary>그 외 발표 덱 '
                     f'<span class="pill mini warn">미검토 · 참고용</span> · {len(misc_rows)}개</summary>'
                     f'<ul class="misc-list">{"".join(misc_rows)}</ul></details>')

    # --- 일일 복습 (reviews/dayN.html) ---
    daily_cards = []
    for day, axis in sorted(recaps or [], reverse=True):
        daily_cards.append(f"""
        <article class="card">
          <div class="tags"><span class="pill topic">📅 {day}일차</span></div>
          <h3 class="ctitle">{escape(axis) if axis else f'{day}일차 복습 시트'}</h3>
          <div class="acts">
            <a class="btn" href="reviews/day{day}.html">복습 시트 열기</a>
          </div>
        </article>""")
    daily_html = "".join(daily_cards) or '<div class="empty">아직 복습 시트가 없습니다 — 수업 노트가 오면 days/N/compare.md 로 생성됩니다.</div>'

    updated = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html lang="ko" data-mode="light"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Oracle DBA 학습 자료실</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script>
// 다크/라이트 모드 — 깜빡임 방지 위해 head 에서 즉시 적용
(function(){{try{{var m=localStorage.getItem('lib-mode');if(m)document.documentElement.setAttribute('data-mode',m);}}catch(e){{}}}})();
</script>
<style>
:root{{
  --bg:#f6f8fa; --sidebar:#ffffff; --card:#ffffff; --border:#e7ebef;
  --text:#34343c; --muted:#7c828a; --heading:#1b1b1f; --accent:#1d7dcc; --accent-soft:#e9f2fb;
  --pill-bg:#eef1f4; --pill-fg:#5b636b; --shadow:0 4px 16px rgba(23,32,50,.06);
  --shadow-hover:0 10px 26px rgba(23,32,50,.10);
}}
html[data-mode=dark]{{
  --bg:#1b1b1e; --sidebar:#161618; --card:#212125; --border:#2c2d33;
  --text:#bcc0c6; --muted:#828892; --heading:#e8eaed; --accent:#7cb2e0; --accent-soft:#1f2a35;
  --pill-bg:#2a2b31; --pill-fg:#9aa2ac; --shadow:0 4px 16px rgba(0,0,0,.35);
  --shadow-hover:0 10px 26px rgba(0,0,0,.5);
}}
*{{box-sizing:border-box}}
html,body{{margin:0}}
body{{background:var(--bg);color:var(--text);
  font-family:'Lato','Noto Sans KR',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  line-height:1.65;-webkit-font-smoothing:antialiased;transition:background .2s,color .2s}}
a{{color:var(--accent);text-decoration:none}}

/* 좌측 사이드바 (Chirpy) */
#sidebar{{position:fixed;top:0;left:0;bottom:0;width:280px;background:var(--sidebar);
  border-right:1px solid var(--border);display:flex;flex-direction:column;padding:34px 24px 20px;z-index:10}}
.avatar{{width:96px;height:96px;border-radius:50%;margin:0 auto 16px;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,#c74634,#8f2f22);color:#fff;font-weight:900;font-size:22px;letter-spacing:.04em;
  box-shadow:0 6px 18px rgba(199,70,52,.35);border:3px solid var(--card)}}
.site-title{{text-align:center;font-size:20px;font-weight:900;color:var(--heading);margin:0 0 4px;line-height:1.3}}
.site-title a{{color:inherit}}
.site-sub{{text-align:center;font-size:12.5px;color:var(--muted);margin:0 0 22px}}
#sidebar nav{{margin-top:6px}}
#sidebar nav a{{display:flex;align-items:center;gap:11px;padding:11px 14px;border-radius:10px;color:var(--text);
  font-weight:700;font-size:14px;margin-bottom:3px}}
#sidebar nav a:hover{{background:var(--accent-soft);color:var(--accent)}}
#sidebar nav a .ic{{width:20px;text-align:center;font-size:15px}}
.side-bottom{{margin-top:auto;padding-top:16px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:8px}}
.mode-btn{{background:var(--pill-bg);border:1px solid var(--border);color:var(--text);border-radius:9px;
  padding:7px 11px;cursor:pointer;font-size:14px;font-weight:700;display:flex;align-items:center;gap:6px}}
.mode-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.side-copy{{font-size:11px;color:var(--muted)}}

/* 본문 */
#main{{margin-left:280px;min-height:100vh;display:flex;flex-direction:column}}
.inner{{max-width:940px;width:100%;margin:0 auto;padding:40px 32px 30px}}
.lead{{margin:0 0 6px;font-size:14px;color:var(--muted)}}
h2.sec{{font-size:15px;letter-spacing:.02em;color:var(--heading);margin:34px 0 3px;display:flex;align-items:center;gap:9px}}
h2.sec .n{{font-family:'Lato',monospace;font-size:11px;font-weight:900;color:var(--accent);
  background:var(--accent-soft);border-radius:7px;padding:3px 8px}}
.sub{{color:var(--muted);font-size:13px;margin:2px 0 14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}}
.big{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}

.card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 17px;
  display:flex;flex-direction:column;gap:9px;box-shadow:var(--shadow);transition:transform .15s,box-shadow .15s}}
.card:hover{{transform:translateY(-3px);box-shadow:var(--shadow-hover)}}
.big .card{{flex-direction:row;align-items:center;justify-content:space-between}}
.tags{{display:flex;align-items:center;gap:7px;flex-wrap:wrap}}
.ctitle{{font-size:15px;font-weight:700;color:var(--heading);line-height:1.4;margin:0}}
.meta{{font-family:'Lato',monospace;font-size:11.5px;color:var(--muted);margin:0}}
.pill{{font-size:11px;font-weight:700;border-radius:20px;padding:3px 11px;white-space:nowrap}}
.pill.topic{{color:var(--accent);background:var(--accent-soft)}}
.pill.topic.dk{{color:#c74634;background:#fbe7de}}
html[data-mode=dark] .pill.topic.dk{{color:#e6917f;background:#3a201a}}
.acts{{display:flex;gap:8px;flex-wrap:wrap;margin-top:2px}}
.btn{{font-size:12.5px;font-weight:700;color:#fff;background:var(--accent);border:1px solid var(--accent);
  border-radius:20px;padding:7px 15px}}
.btn.ghost{{color:var(--text);background:transparent;border-color:var(--border)}}
.btn.ghost:hover{{border-color:var(--accent);color:var(--accent)}}
.btn:hover{{opacity:.9}}
.empty{{color:var(--muted);border:1px dashed var(--border);border-radius:12px;padding:22px;text-align:center;font-size:13px;grid-column:1/-1}}

/* 미검토 덱 — 접어서 소형·저강조 */
.pill.mini{{font-size:10px;padding:2px 8px}}
.pill.warn{{color:#9a6700;background:#fff8c5}}
html[data-mode=dark] .pill.warn{{color:#d9b23a;background:#332b0a}}
details.misc{{margin-top:12px;border:1px solid var(--border);border-radius:12px;background:var(--card)}}
details.misc>summary{{cursor:pointer;padding:12px 15px;font-size:12.5px;font-weight:700;color:var(--muted);
  list-style:none;display:flex;align-items:center;gap:8px}}
details.misc>summary::-webkit-details-marker{{display:none}}
details.misc>summary::before{{content:'▸';color:var(--muted);font-size:11px}}
details.misc[open]>summary::before{{content:'▾'}}
.misc-list{{list-style:none;margin:0;padding:2px 10px 8px}}
.mrow{{display:flex;align-items:center;gap:10px;padding:9px 6px;border-top:1px solid var(--border);
  font-size:12.5px;flex-wrap:wrap}}
.mtitle{{color:var(--text);font-weight:600;flex:1;min-width:160px}}
.mrow .meta{{color:var(--muted)}}
.mdl{{font-weight:700;font-size:12px;color:var(--accent);white-space:nowrap}}

footer{{margin-top:auto;border-top:1px solid var(--border);color:var(--muted);font-size:12px;padding:20px 32px 40px}}
footer .inner{{padding:0;max-width:940px}}

@media(max-width:820px){{
  #sidebar{{position:static;width:auto;flex-direction:column;border-right:none;border-bottom:1px solid var(--border);padding:24px 20px}}
  #sidebar nav{{display:flex;flex-wrap:wrap;gap:6px}}
  #sidebar nav a{{margin:0}}
  .avatar{{width:70px;height:70px;font-size:17px}}
  #main{{margin-left:0}}
  .big{{grid-template-columns:1fr}}
  .inner{{padding:26px 20px}}
}}
</style></head>
<body>
<aside id="sidebar">
  <div class="avatar">DBA</div>
  <h1 class="site-title"><a href="./">Oracle DBA<br>학습 자료실</a></h1>
  <p class="site-sub">수업에서 만든 문서 · 발표 덱 · 문제 허브</p>
  <nav>
    <a href="#hub"><span class="ic">📚</span>학습 허브</a>
    <a href="#docs"><span class="ic">📄</span>학습 문서</a>
    <a href="#decks"><span class="ic">🎞️</span>발표 자료</a>
    <a href="#daily"><span class="ic">🗓️</span>일일 복습</a>
    <a href="assets/dashboard.html"><span class="ic">📊</span>대시보드</a>
  </nav>
  <div class="side-bottom">
    <button class="mode-btn" onclick="toggleMode()"><span id="mode-ic">🌙</span><span id="mode-tx">다크</span></button>
    <span class="side-copy">© DBA Bootcamp</span>
  </div>
</aside>

<main id="main">
  <div class="inner">
    <p class="lead">수업에서 만든 학습 문서 · 발표 덱 · 문제 허브를 한곳에서 보고 내려받습니다.</p>

    <h2 class="sec" id="hub"><span class="n">01</span>학습 허브 &amp; 관리</h2>
    <div class="sub">문제 풀이 · 용어 검색 · 오답노트가 있는 허브와, 진행 상태 대시보드.</div>
    <div class="big">
      <article class="card">
        <div><h3 class="ctitle">📚 학습 허브</h3><p class="meta">객관식·서술형·실행계획·용어 검색·오답노트 · 받아두면 오프라인 작동</p></div>
        <div class="acts">
          <a class="btn" href="assets/study_hub_full.html">열기</a>
          <a class="btn ghost" href="assets/study_hub_full.html" download>다운로드</a>
        </div>
      </article>
      <article class="card">
        <div><h3 class="ctitle">📊 관리 대시보드</h3><p class="meta">검토·정확성·난이도·린트 상태</p></div>
        <a class="btn ghost" href="assets/dashboard.html">열기</a>
      </article>
    </div>

    <h2 class="sec" id="docs"><span class="n">02</span>학습 문서</h2>
    <div class="sub">소스 오브 트루스 — 그 자리에서 보거나 HTML로 내려받으세요.</div>
    <div class="grid">{''.join(doc_cards)}
    </div>

    <h2 class="sec" id="decks"><span class="n">03</span>발표 자료</h2>
    <div class="sub">검토 완료된 최신 덱만 노출합니다. 나머지는 아래에서 펼쳐 참고용으로 받을 수 있어요.</div>
    <div class="grid">{featured_html}
    </div>
    {misc_html}

    <h2 class="sec" id="daily"><span class="n">04</span>일일 복습</h2>
    <div class="sub">하루치 요약 일지 — 그날의 축·개념·명령어·5줄 요약을 한 장으로. 관련 문서 섹션으로 바로 이동합니다.</div>
    <div class="grid">{daily_html}
    </div>
  </div>
  <footer><div class="inner">자동 생성 · 최종 갱신 {updated} · <code>build_library.py</code> — 파일 추가 후 재실행하면 목록이 갱신됩니다.</div></footer>
</main>

<script>
function toggleMode(){{
  var h=document.documentElement, m=h.getAttribute('data-mode')==='dark'?'light':'dark';
  h.setAttribute('data-mode',m);
  try{{localStorage.setItem('lib-mode',m)}}catch(e){{}}
  syncModeBtn();
}}
function syncModeBtn(){{
  var dark=document.documentElement.getAttribute('data-mode')==='dark';
  var ic=document.getElementById('mode-ic'), tx=document.getElementById('mode-tx');
  if(ic) ic.textContent=dark?'☀️':'🌙';
  if(tx) tx.textContent=dark?'라이트':'다크';
}}
syncModeBtn();
</script>
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
    recaps = build_review_pages()
    if recaps:
        print(f"[library] 일일 복습 페이지: {len(recaps)}개 → reviews/")
    status = load_status()
    args.out.write_text(render(status, recaps), encoding="utf-8")
    print(f"[library] → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
