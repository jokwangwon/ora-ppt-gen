#!/usr/bin/env python3
"""HTML 학습 문서 → 슬라이드 스펙(JSON) 추출.

파이프라인의 1단계. HTML(소스 오브 트루스)에서 섹션/개념/표/박스/코드/다이어그램을
구조화된 JSON으로 뽑는다. **원문에서 새 사실을 지어내지 않는다** — 요약 재작성 없이
문서에 있는 텍스트를 그대로 옮기고, 발표에 맞게 "구조"만 만든다.

추출이 부정확한 슬라이드는 이 JSON만 손보면 되고, 디자인은 렌더러(build_ppt.js)에서 고친다.

사용법:
    python extract_slides.py assets/sql_tuning.html            # stdout으로 JSON
    python extract_slides.py assets/sql_tuning.html -o out/sql_tuning.slides.json

슬라이드 스펙 스키마 (build_ppt.js와 공유):
    {
      "deck_id":  "sql_tuning",
      "title":    "<h1 텍스트>",
      "subtitle": "<있으면>",
      "source":   "sql_tuning.html",
      "slides": [
        {"type":"title",   "title":..., "subtitle":...},
        {"type":"section", "num":"02", "title":..., "subtitle":...},
        {"type":"content", "title":"2.1 ...", "blocks":[ <block>, ... ]}
      ]
    }
    block =
        {"kind":"bullets", "items":[str, ...]}
      | {"kind":"table",   "headers":[str,...], "rows":[[str,...], ...]}
      | {"kind":"callout", "tone":"why"|"tip", "head":str, "body":str}
      | {"kind":"code",    "lines":[str, ...]}
      | {"kind":"figure",  "caption":str, "summary":str}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

# 문서 순서대로 추출할 관심 블록. h3.blk은 개념(=슬라이드) 경계.
_LEAF = "leaf"  # 하위로 더 내려가지 않고 이 요소 자체를 하나의 블록으로 취급


def _text(node) -> str:
    """자식 태그를 벗겨 공백 정리된 순수 텍스트."""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _classify(el: Tag) -> str | None:
    """관심 있는 블록이면 종류 문자열, 아니면 None."""
    cls = el.get("class") or []
    if el.name == "h3" and "blk" in cls:
        return "h3"
    if el.name == "table":
        return "table"
    if el.name == "figure":
        return "figure"
    if el.name == "pre" and "term" in cls:
        return "code"
    if el.name == "div" and ("why" in cls or "tip" in cls):
        return "callout"
    if el.name == "p":
        return "p"
    return None


def _walk(section: Tag):
    """섹션 내부를 문서 순서로 훑어 (종류, 요소)를 방출한다.

    인식된 블록을 만나면 방출하고 그 하위로는 내려가지 않는다(중복 방지).
    래핑용 컨테이너(div 등)만 재귀한다.
    """
    def visit(node):
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            kind = _classify(child)
            if kind is not None:
                yield kind, child
            elif child.name in ("div", "section", "figure") and child is not node:
                # phead(섹션 헤더)는 별도 처리하므로 건너뛴다.
                if "phead" in (child.get("class") or []):
                    continue
                yield from visit(child)
    yield from visit(section)


def _table_block(el: Tag) -> dict:
    rows = []
    for tr in el.find_all("tr"):
        cells = [_text(c) for c in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return {"kind": "table", "headers": [], "rows": []}
    # 첫 행에 th가 있으면 헤더로 분리.
    first_tr = el.find("tr")
    has_head = first_tr is not None and first_tr.find("th") is not None
    headers = rows[0] if has_head else []
    body = rows[1:] if has_head else rows
    return {"kind": "table", "headers": headers, "rows": body}


def _callout_block(el: Tag) -> dict:
    tone = "why" if "why" in (el.get("class") or []) else "tip"
    head_el = el.find(class_="h") or el.find("b")
    head = _text(head_el) if head_el else ""
    body = _text(el)
    if head and body.startswith(head):
        body = body[len(head):].lstrip(" —-:·").strip()
    return {"kind": "callout", "tone": tone, "head": head, "body": body}


def _code_block(el: Tag) -> dict:
    # <br>을 줄바꿈으로, 나머지 태그(프롬프트 span 등)는 텍스트로.
    for br in el.find_all("br"):
        br.replace_with("\n")
    raw = el.get_text("", strip=False)
    lines = [ln.rstrip() for ln in raw.splitlines()]
    # 앞뒤 빈 줄 제거
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return {"kind": "code", "lines": lines}


def _figure_block(el: Tag) -> dict:
    cap_el = el.find("figcaption")
    caption = _text(cap_el) if cap_el else ""
    # 다이어그램의 텍스트 노드(라벨)를 모아 요약. 새 사실이 아니라 그림 속 글자.
    labels = []
    svg = el.find("svg")
    if svg:
        for t in svg.find_all("text"):
            s = _text(t)
            if s and s not in labels:
                labels.append(s)
    summary = " · ".join(labels[:12])
    return {"kind": "figure", "caption": caption, "summary": summary}


def _flush_bullets(buf: list[str]) -> dict | None:
    items = [b for b in (s.strip() for s in buf) if b]
    return {"kind": "bullets", "items": items} if items else None


def _section_slides(section: Tag) -> list[dict]:
    """한 섹션(part) → [섹션 슬라이드, 개념 슬라이드들]."""
    phead = section.find(class_="phead")
    num = _text(section.find(class_="pnum")) if section.find(class_="pnum") else ""
    ptitle = _text(section.find(class_="ptitle")) if section.find(class_="ptitle") else ""
    psub = _text(section.find(class_="psub")) if section.find(class_="psub") else ""

    slides: list[dict] = [
        {"type": "section", "num": num, "title": ptitle, "subtitle": psub}
    ]

    # 현재 개념 슬라이드 상태
    cur_title = ptitle or "개요"
    cur_blocks: list[dict] = []
    bullet_buf: list[str] = []

    def close_concept():
        nonlocal cur_blocks, bullet_buf
        b = _flush_bullets(bullet_buf)
        if b:
            cur_blocks.insert(0, b) if False else cur_blocks.append(b)
        bullet_buf = []
        if cur_blocks:
            slides.append({"type": "content", "title": cur_title, "blocks": cur_blocks})
        cur_blocks = []

    started = False
    for kind, el in _walk(section):
        if kind == "h3":
            # 새 개념 시작 — 이전 개념 마감
            if started:
                close_concept()
            cur_title = _text(el)
            cur_blocks = []
            bullet_buf = []
            started = True
        elif kind == "p":
            bullet_buf.append(_text(el))
        else:
            # 표/박스/코드/그림 — 버퍼된 불릿을 먼저 붙이고 블록 추가
            b = _flush_bullets(bullet_buf)
            if b:
                cur_blocks.append(b)
            bullet_buf = []
            if kind == "table":
                cur_blocks.append(_table_block(el))
            elif kind == "callout":
                cur_blocks.append(_callout_block(el))
            elif kind == "code":
                cur_blocks.append(_code_block(el))
            elif kind == "figure":
                cur_blocks.append(_figure_block(el))
            started = True

    close_concept()
    return slides


def extract(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    h1 = soup.find("h1")
    title = _text(h1) if h1 else html_path.stem
    # 부제: h1 바로 뒤 형제 중 sub/lead 성격, 없으면 빈 문자열
    subtitle = ""
    if h1:
        sib = h1.find_next_sibling()
        if sib and isinstance(sib, Tag) and sib.name in ("p", "div"):
            cls = " ".join(sib.get("class") or [])
            if re.search(r"sub|lead|desc", cls):
                subtitle = _text(sib)

    slides: list[dict] = [{"type": "title", "title": title, "subtitle": subtitle}]
    for section in soup.find_all("section", class_="part"):
        slides.extend(_section_slides(section))

    return {
        "deck_id": html_path.stem,
        "title": title,
        "subtitle": subtitle,
        "source": html_path.name,
        "slides": slides,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HTML 학습 문서 → 슬라이드 스펙 JSON")
    ap.add_argument("html", type=Path, help="입력 HTML 문서 경로")
    ap.add_argument("-o", "--out", type=Path, help="출력 JSON 경로 (미지정 시 stdout)")
    args = ap.parse_args(argv)

    if not args.html.exists():
        print(f"[extract] 파일 없음: {args.html}", file=sys.stderr)
        return 1

    spec = extract(args.html)
    text = json.dumps(spec, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        n = len(spec["slides"])
        print(f"[extract] {args.html.name} → {args.out}  (슬라이드 {n}장)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
