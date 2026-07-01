#!/usr/bin/env python3
"""문서 스타일 인라인 SVG 다이어그램 생성기 (정답지 작법 P3·P4·P6).

정답지의 가장 큰 강점은 "개념마다 다이어그램"이다. 이 모듈은 그 다이어그램을
**그 문서 <style>에 정의된 클래스만** 써서 찍어낸다 → 룩 일관 + 검은박스 원천 차단.

전제: 대상 문서가 아래 클래스를 정의한다(guide/sql/buffer 계열 공통).
  노드: ntune(주강조)·ncor(정답/포인트)·nmut(약)   연결: edge   라벨: svg-sub·svg-mono
텍스트 색은 style="fill:var(--ink)" 로 준다.
**주의**: ntune 은 sql 전용. 공통 안전 클래스는 ncor·nmut·nal·edge (sql·guide·buffer 공통).
대상 문서가 정의한 클래스를 cls= 로 넘겨라 — sync_and_verify 가 미정의를 잡는다.

대화 저작 중 파이썬으로 불러 쓰거나(권장), CLI 데모로 확인:
    python svg_snippets.py demo > /tmp/demo.svg
"""

from __future__ import annotations

from html import escape


def _rect(x: float, y: float, w: float, h: float, cls: str, label: str) -> str:
    return (
        f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6" stroke-width="1.1"/>'
        f'<text x="{x + 12}" y="{y + h/2 + 4}" style="fill:var(--ink)">{escape(label)}</text>'
    )


def _defs(uid: str) -> str:
    """화살표 마커. edge 색을 따르도록 currentColor 대신 var(--muted)."""
    return (
        f'<defs><marker id="ah{uid}" markerWidth="8" markerHeight="8" refX="6" refY="3" '
        f'orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="var(--muted)"/></marker></defs>'
    )


def figure(inner: str, caption: str, vb_w: int = 680, vb_h: int = 200, aria: str = "") -> str:
    """<figure><svg>…</svg><figcaption></figure> 래핑."""
    a = f' role="img" aria-label="{escape(aria or caption)}"' if (aria or caption) else ""
    return (
        f'<figure>\n  <svg viewBox="0 0 {vb_w} {vb_h}"{a} font-family="var(--mono)" font-size="12">\n'
        f'    {inner}\n  </svg>\n  <figcaption>{escape(caption)}</figcaption>\n</figure>'
    )


def boxes_row(items: list[str], *, cls: str = "ncor", y: float = 40,
              x0: float = 24, w: float = 150, h: float = 34, gap: float = 18) -> str:
    """라벨 박스 한 줄. (개념의 요소 나열 P4)"""
    out = []
    x = x0
    for it in items:
        out.append(_rect(x, y, w, h, cls, it))
        x += w + gap
    return "".join(out)


def flow(steps: list[str], *, cls: str = "ncor", y: float = 46,
         x0: float = 24, w: float = 150, h: float = 40, gap: float = 40, uid: str = "f") -> str:
    """박스 → 박스 → 박스 (화살표 연결). 문제→원인→해결, Id 흐름 등 (P3)."""
    parts = [_defs(uid)]
    x = x0
    centers = []
    for i, s in enumerate(steps):
        parts.append(_rect(x, y, w, h, cls, s))
        centers.append((x, x + w))
        x += w + gap
    for i in range(len(steps) - 1):
        x1, y1 = centers[i][1] + 4, y + h / 2
        x2 = centers[i + 1][0] - 4
        parts.append(f'<line class="edge" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" marker-end="url(#ah{uid})"/>')
    return "".join(parts)


def good_bad_grid(good: list[str], bad: list[str], *, good_label: str, bad_label: str,
                  y0: float = 36, gap_y: float = 94) -> str:
    """좋음(ntune) vs 나쁨(nmut) 두 묶음 대비. CF·정규화 등 (P6)."""
    parts = [f'<text class="svg-sub" x="24" y="{y0 - 12}">{escape(good_label)}</text>']
    parts.append(boxes_row(good, cls="ncor", y=y0, w=130, gap=16))
    y1 = y0 + gap_y
    parts.append(f'<text class="svg-sub" x="24" y="{y1 - 12}">{escape(bad_label)}</text>')
    parts.append(boxes_row(bad, cls="nmut", y=y1, w=130, gap=16))
    return "".join(parts)


def plan_pair(top: str, bottom: str, *, note: str = "", uid: str = "p") -> str:
    """실행계획 두 줄의 상호작용(Id N ↕ Id M) (P3)."""
    parts = [_defs(uid)]
    parts.append(_rect(60, 30, 360, 36, "ncor", top))
    parts.append(_rect(60, 110, 360, 36, "nal", bottom))
    parts.append(f'<line class="edge" x1="440" y1="48" x2="440" y2="128" marker-end="url(#ah{uid})"/>')
    parts.append(f'<line class="edge" x1="460" y1="128" x2="460" y2="48" marker-end="url(#ah{uid})"/>')
    if note:
        parts.append(f'<text class="svg-sub" x="480" y="92">{escape(note)}</text>')
    return "".join(parts)


# ── 데모 ─────────────────────────────────────────────────────────
def demo() -> str:
    inner = good_bad_grid(
        ["blk A: 10 10 10", "blk B: 20 20 20", "blk C: 30 30 30"],
        ["blk A: 10 20 30", "blk B: 10 20 30", "blk C: 10 20 30"],
        good_label="CF 좋음 — 같은 값이 같은 블록에 (블록 수 ≈ CF)",
        bad_label="CF 나쁨 — 흩어짐 (행 수 ≈ CF)",
    )
    return figure(inner, "같은 인덱스 키라도 물리적으로 모여 있으면 적은 블록만 읽는다.", vb_h=210)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        print(demo())
    else:
        print(__doc__)
