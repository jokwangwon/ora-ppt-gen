#!/usr/bin/env python3
"""발표 대본 추출 — 슬라이드 스펙(JSON)에서 화면 요지 + 발표자 노트를 한 문서로.

무료/뷰어 버전 PowerPoint에서는 발표자 노트가 잘 안 보인다. 노트는 pptx에
박혀 있지만(Google 슬라이드·LibreOffice·PPT 웹에서 보임), 앱에 의존하지 않게
슬라이드별 [제목 + 화면 블록 요지 + 발표 노트]를 markdown/txt로 뽑는다.

사용법:
    python notes_export.py days/72/72.slides.json                 # → out/day72.notes.md
    python notes_export.py days/72/72.slides.json -o out/x.md
    python notes_export.py days/72/72.slides.json --txt           # 순수 텍스트
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def block_gist(b: dict) -> str:
    """화면에 실제로 보이는 블록의 한 줄 요지(노트와 대조용)."""
    k = b.get("kind")
    if k == "bullets":
        return "· " + " / ".join(b.get("items", []))
    if k == "table":
        hdr = " | ".join(b.get("headers", []))
        return f"[표] {hdr}" + (f"  ({len(b.get('rows', []))}행)" if b.get("rows") else "")
    if k == "callout":
        return f"[{b.get('head','콜아웃')}] {b.get('body','')}"
    if k == "code":
        return "[코드] " + " ⏎ ".join(l for l in b.get("lines", []) if l.strip())[:200]
    if k == "svg":
        return f"[다이어그램] {b.get('caption','') or '(그림)'}"
    if k == "analogy":
        return f"[비유] {b.get('text','')}"
    if k == "steps":
        return "[단계] " + " → ".join(f"{it.get('n','')}{it.get('head','')}" for it in b.get("items", []))
    if k == "figure":
        return f"[그림] {b.get('caption','')}"
    if k == "plan":
        return f"[실행계획] {b.get('title','')}"
    return f"[{k}]"


def export(spec: dict, txt: bool = False) -> str:
    title = spec.get("title", spec.get("deck_id", "deck"))
    out = [] if txt else [f"# {title} — 발표 대본\n", f"> {spec.get('subtitle','')}\n"]
    if txt:
        out.append(f"{title} — 발표 대본\n{'='*40}\n")
    n = 0
    for sl in spec.get("slides", []):
        t = sl.get("type")
        if t == "section":
            head = f"■ [{sl.get('num','')}] {sl.get('title','')}"
            out.append(f"\n{head}" if txt else f"\n---\n\n## {head}")
        elif t == "content":
            n += 1
            label = f"[{n}] {sl.get('title','')}"
            out.append(f"\n### {label}" if not txt else f"\n{label}\n{'-'*len(label)}")
            # 화면 요지
            gist = [block_gist(b) for b in sl.get("blocks", [])]
            for g in gist:
                out.append(f"- {g}")
            # 발표 노트
            if sl.get("notes"):
                out.append(("\n**발표 노트 →** " if not txt else "\n▶ 발표: ") + sl["notes"])
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="발표 대본 추출")
    ap.add_argument("spec", type=Path, help="슬라이드 스펙 JSON")
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--txt", action="store_true", help="순수 텍스트(.txt)")
    args = ap.parse_args(argv)
    if not args.spec.exists():
        print(f"[notes] 파일 없음: {args.spec}"); return 1
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    doc = export(spec, txt=args.txt)
    stem = spec.get("deck_id") or args.spec.stem.replace(".slides", "")
    out = args.out or Path("out") / (stem + (".notes.txt" if args.txt else ".notes.md"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"[notes] {args.spec.name} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
