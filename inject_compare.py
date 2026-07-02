#!/usr/bin/env python3
"""복습 시트(days/N/compare.md)를 허브 '복습' 탭에 내장한다(멱등).

md를 간이 HTML로 변환해 <script type="text/plain" id="cmp-N"> 블록으로 주입.
허브의 renderCompare()가 일차 칩으로 골라 보여준다. 같은 id는 교체(멱등).

사용법:
    python inject_compare.py                          # days/*/compare.md 전부
    python inject_compare.py --day 73                 # 해당 일차만
    python inject_compare.py --hub assets/study_hub_full.html
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB = ROOT / "assets" / "study_hub_full.html"
DAYS = ROOT / "days"


def _inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # [텍스트](주소) — 문서 앵커·허브·매뉴얼로 연결. 주소는 리포 루트 기준(assets/...)으로 쓰고,
    # 소비자(허브/자료실 페이지)가 자기 위치에 맞게 접두어를 고친다.
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"<a href='\2' class='cmp-link'>\1</a>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md2html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, inlist = 0, ""
    def close_list():
        nonlocal inlist
        if inlist:
            out.append(f"</{inlist}>")
            inlist = ""
    while i < len(lines):
        l = lines[i]
        # 표: 헤더줄 + 구분줄
        if l.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s\-\|:]+\|?\s*$", lines[i + 1]):
            close_list()
            hdr = [_inline(c.strip()) for c in l.strip().strip("|").split("|")]
            i += 2
            out.append("<table><tr>" + "".join(f"<th>{h}</th>" for h in hdr) + "</tr>")
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [_inline(c.strip()) for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</table>")
            continue
        if re.match(r"^\s*[-*]\s", l):
            if inlist != "ul":
                close_list(); out.append("<ul>"); inlist = "ul"
            item = re.sub(r"^\s*[-*]\s", "", l)
            out.append(f"<li>{_inline(item)}</li>")
        elif re.match(r"^\s*\d+\.\s", l):
            if inlist != "ol":
                close_list(); out.append("<ol>"); inlist = "ol"
            item = re.sub(r"^\s*\d+\.\s", "", l)
            out.append(f"<li>{_inline(item)}</li>")
        else:
            close_list()
            if l.startswith("### "):
                out.append(f"<h4>{_inline(l[4:])}</h4>")
            elif l.startswith("## "):
                out.append(f"<h3>{_inline(l[3:])}</h3>")
            elif l.startswith("# "):
                out.append(f"<h2>{_inline(l[2:])}</h2>")
            elif l.startswith("> "):
                out.append(f"<div class='note'>{_inline(l[2:])}</div>")
            elif l.strip() in ("---", "***"):
                out.append("<hr>")
            elif l.strip():
                out.append(f"<p>{_inline(l)}</p>")
        i += 1
    close_list()
    return "\n".join(out)


def inject(hub: str, day: int, html: str, rep: list[str]) -> str:
    html = html.replace("</script", "<\\/script")  # 안전핀 (본문은 이미 이스케이프됨)
    html = html.replace("href='assets/", "href='")  # 허브는 assets/ 안에 있음 — 접두어 제거
    block = f'<script type="text/plain" id="cmp-{day}">{html}</script>'
    pat = re.compile(r'<script type="text/plain" id="cmp-' + str(day) + r'">[\s\S]*?</script>')
    if pat.search(hub):
        hub = pat.sub(lambda _: block, hub)
        rep.append(f"~ 교체: cmp-{day}")
    else:
        idx = hub.rfind("</body>")
        hub = hub[:idx] + block + "\n" + hub[idx:]
        rep.append(f"+ 추가: cmp-{day}")
    return hub


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="복습 시트 허브 내장")
    ap.add_argument("--hub", type=Path, default=HUB)
    ap.add_argument("--day", type=int, help="해당 일차만 (생략 시 전부)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    hub = args.hub.read_text(encoding="utf-8")
    rep: list[str] = []
    targets = sorted(DAYS.glob("*/compare.md"))
    if args.day:
        targets = [p for p in targets if p.parent.name == str(args.day)]
    if not targets:
        print("· 대상 compare.md 없음"); return 0
    for p in targets:
        day = int(p.parent.name)
        hub = inject(hub, day, md2html(p.read_text(encoding="utf-8")), rep)
    for r in rep:
        print(f"  {r}")
    if not args.dry_run:
        args.hub.write_text(hub, encoding="utf-8")
        print(f"✓ 저장: {args.hub}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
