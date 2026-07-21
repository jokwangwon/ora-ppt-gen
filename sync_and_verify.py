#!/usr/bin/env python3
"""동기화 · 재주입 · 검증을 한 번에.

매일 손으로 하던 반복 작업을 자동화한다:
  1) 동기화   — 한글 원본 HTML → ASCII 사본 복사 (뷰어 호환)
  2) 재주입   — 4개 ASCII 문서를 study_hub_full의 docsrc-* 블록에 다시 삽입
                (문서 안의 </script 는 <\\/script 로 이스케이프)
  3) 검증     — 태그 균형 / 메인 <script> JS 문법(node --check) /
                미정의 SVG 클래스(.nXXX·.edge) 탐지 (검은 박스 버그 예방)

**검증이 실패하면 산출물(허브)을 쓰지 않고 멈춰서 원인을 보고한다.**

사용법:
    python sync_and_verify.py                 # --dir . 기본
    python sync_and_verify.py --dir assets
    python sync_and_verify.py --dir assets --check-only   # 재주입 없이 검증만
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 한글 원본 ↔ ASCII 사본 (뷰어 호환용 사본)
KO_TO_ASCII = {
    "SQL_튜닝.html": "sql_tuning.html",
    "DBA_62-68일차_완전정복.html": "guide_62_68.html",
    "RMAN_복구_치트시트.html": "rman_recovery.html",
    "buffer_cache_dbwr_checkpoint.html": "buffer_cache_dbwr_checkpoint.html",
    "RAC_클러스터.html": "rac.html",
}
# study_hub_full 의 docsrc-<key> ← ASCII 문서
DOCSRC_TO_ASCII = {
    "guide": "guide_62_68.html",
    "sql": "sql_tuning.html",
    "rman": "rman_recovery.html",
    "buffer": "buffer_cache_dbwr_checkpoint.html",
    "rac": "rac.html",
}
HUB = "study_hub_full.html"
BALANCED_TAGS = ["section", "table", "figure", "svg", "pre", "div", "ul", "ol"]

# ── 결과 수집 ─────────────────────────────────────────────────────
class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.notes: list[str] = []

    def error(self, m: str) -> None: self.errors.append(m)
    def warn(self, m: str) -> None: self.warns.append(m)
    def note(self, m: str) -> None: self.notes.append(m)

    def dump(self) -> None:
        for m in self.notes: print(f"  · {m}")
        for m in self.warns: print(f"  ⚠ {m}")
        for m in self.errors: print(f"  ✗ {m}")


# ── 1) 동기화 ─────────────────────────────────────────────────────
def sync(base: Path, rep: Report) -> None:
    print("[1/3] 동기화 (한글 원본 → ASCII 사본)")
    done = 0
    for ko, ascii_name in KO_TO_ASCII.items():
        src = base / ko
        if ko == ascii_name:
            continue  # 이미 ASCII 이름
        if src.exists():
            shutil.copyfile(src, base / ascii_name)
            rep.note(f"복사: {ko} → {ascii_name}")
            done += 1
    if done == 0:
        rep.note("한글 원본이 없어 복사 생략 (ASCII 사본을 직접 사용)")


# ── 2) 재주입 (문자열 생성만, 쓰기는 검증 후) ─────────────────────
def build_injected_hub(base: Path, rep: Report) -> str | None:
    print("[2/3] 재주입 (docsrc-* 블록 갱신)")
    hub_path = base / HUB
    if not hub_path.exists():
        rep.error(f"허브 없음: {hub_path}")
        return None
    hub = hub_path.read_text(encoding="utf-8")

    for key, ascii_name in DOCSRC_TO_ASCII.items():
        doc_path = base / ascii_name
        if not doc_path.exists():
            rep.warn(f"문서 없음, docsrc-{key} 유지: {ascii_name}")
            continue
        doc = doc_path.read_text(encoding="utf-8")
        escaped = doc.replace("</script", r"<\/script")  # 필수 이스케이프
        pattern = re.compile(
            r'(<script type="text/plain" id="docsrc-' + key + r'">)(.*?)(</script>)', re.S
        )
        if not pattern.search(hub):
            rep.error(f"docsrc-{key} 블록을 허브에서 찾지 못함")
            continue
        hub = pattern.sub(lambda m: m.group(1) + escaped + m.group(3), hub, count=1)
        rep.note(f"주입: {ascii_name} → docsrc-{key} ({len(doc):,}B)")
    return hub


# ── 3) 검증 ───────────────────────────────────────────────────────
def check_tag_balance(html: str, label: str, rep: Report) -> None:
    for tag in BALANCED_TAGS:
        opens = len(re.findall(r"<" + tag + r"(?=[\s>/])", html))
        closes = len(re.findall(r"</" + tag + r"\s*>", html))
        if opens != closes:
            rep.error(f"[{label}] <{tag}> 여는 {opens} ≠ 닫는 {closes}")


def _defined_classes(html: str) -> set[str]:
    """<style> 안에서 정의된 CSS 클래스명 집합. 그룹 선택자(.a,.b{)도 처리."""
    defined: set[str] = set()
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S):
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)  # 주석 제거
        for selector in re.findall(r"([^{}]+)\{", style):     # 선언 앞 선택자 목록
            defined.update(re.findall(r"\.([A-Za-z][\w-]*)", selector))
    return defined


def check_svg_classes(html: str, label: str, rep: Report) -> None:
    """SVG 안에서 쓰인 class 토큰이 CSS에 정의됐는지 확인 (검은 박스 예방)."""
    defined = _defined_classes(html)
    used: set[str] = set()
    for svg in re.findall(r"<svg.*?</svg>", html, re.S):
        for cls in re.findall(r'class="([^"]+)"', svg):
            used.update(cls.split())
    undefined = sorted(t for t in used if t not in defined)
    if undefined:
        rep.error(f"[{label}] 미정의 SVG 클래스(검은 박스 위험): {undefined}")
    if "edge" in used and "edge" not in defined:
        rep.error(f"[{label}] .edge 미정의 (연결선 누락 위험)")


def check_js_syntax(html: str, label: str, rep: Report) -> None:
    """메인 <script>(실행 스크립트)만 node --check 로 문법 검증.

    <script type="text/plain">(docsrc 등)은 코드가 아니므로 통째로 제거한 뒤 검사한다.
    """
    html = re.sub(r'<script type="text/plain"[^>]*>.*?</script>', "", html, flags=re.S)
    for m in re.finditer(r"<script(?![^>]*type=)([^>]*)>(.*?)</script>", html, re.S):
        body = m.group(2)
        if not body.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(body)
            tmp = f.name
        try:
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                first = (r.stderr.strip().splitlines() or ["(no detail)"])[0]
                rep.error(f"[{label}] 메인 <script> JS 문법 오류: {first}")
        except FileNotFoundError:
            rep.warn(f"[{label}] node 미설치 — JS 문법 검증 생략")
            return
        finally:
            Path(tmp).unlink(missing_ok=True)


def verify_document(html: str, label: str, rep: Report, js: bool = False) -> None:
    check_tag_balance(html, label, rep)
    check_svg_classes(html, label, rep)
    if js:
        check_js_syntax(html, label, rep)


def verify(base: Path, hub_html: str | None, rep: Report) -> bool:
    print("[3/3] 검증 (태그 균형 · JS 문법 · SVG 클래스)")
    # 각 문서 개별 검증
    for ascii_name in DOCSRC_TO_ASCII.values():
        p = base / ascii_name
        if p.exists():
            verify_document(p.read_text(encoding="utf-8"), ascii_name, rep)
    # 허브(주입본) 검증 — 메인 스크립트 JS 문법 포함
    if hub_html is not None:
        verify_document(hub_html, HUB, rep, js=True)
    return not rep.errors


# ── 엔트리 ───────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="동기화 · 재주입 · 검증")
    ap.add_argument("--dir", type=Path, default=Path("."), help="HTML 자산 폴더")
    ap.add_argument("--check-only", action="store_true", help="재주입 없이 검증만")
    ap.add_argument("--force", action="store_true", help="검증 실패해도 허브 재주입본을 기록")
    args = ap.parse_args(argv)
    base = args.dir
    rep = Report()

    if not args.check_only:
        sync(base, rep)
    hub_html = None if args.check_only else build_injected_hub(base, rep)

    ok = verify(base, hub_html, rep)
    print("\n결과:")
    rep.dump()

    if not ok and not args.force:
        print(f"\n✗ 검증 실패 ({len(rep.errors)}건) — 허브를 쓰지 않고 중단합니다.")
        return 1

    if hub_html is not None:
        (base / HUB).write_text(hub_html, encoding="utf-8")
        note = "검증 통과" if ok else f"검증 실패 {len(rep.errors)}건이지만 --force"
        print(f"\n{'✓' if ok else '⚠'} {note} — {base / HUB} 갱신 완료.")
    elif ok:
        print("\n✓ 검증 통과.")
    return 0 if ok else (0 if args.force else 1)


if __name__ == "__main__":
    raise SystemExit(main())
