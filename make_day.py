#!/usr/bin/env python3
"""일차(N일차) 파이프라인 — 대화로 저작한 하루치를 허브·PPT에 배선한다.

전제(대화형 저작): 아래는 Claude와 대화로 미리 만들어 둔다.
  - assets/<topic>.html          : 그날 섹션(h3.blk·표·why/tip·pre.term·SVG)을 문서에 직접 추가
  - days/<N>/quiz.json           : {MCQ,ESSAY,TERMS,PLANQ} 문제
  - days/<N>/<N>.slides.json     : 일차 덱 슬라이드 스펙 (선택)

이 스크립트는 결정적으로 배선한다:
  1) sync_and_verify : 문서 편집분을 허브 docsrc에 재주입 + 검증(태그/JS/검은박스)
  2) inject_quiz     : 문제·DAYS·날짜칩 주입, 주입 후 허브 JS 재검증
  3) 일차 덱 렌더    : days/<N>/<N>.slides.json → out/day<N>.pptx  (있으면)
  4) 문서 전체 덱    : <doc> → out/<stem>.pptx
  5) --preview 시 QA 스크린샷

사용법:
    python make_day.py 71 --doc sql_tuning.html
    python make_day.py 71 --doc sql_tuning.html --preview
    python make_day.py 71 --doc sql_tuning.html --force   # HTML 검증 실패해도 진행
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import sync_and_verify as sv

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=ROOT).returncode


def hub_js_ok(hub_path: Path) -> bool:
    rep = sv.Report()
    sv.verify_document(hub_path.read_text(encoding="utf-8"), hub_path.name, rep, js=True)
    if rep.errors:
        print("  주입 후 허브 검증 실패:")
        rep.dump()
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="일차 파이프라인")
    ap.add_argument("day", type=int, help="일차 (예: 71)")
    ap.add_argument("--doc", required=True, help="그날 내용이 속한 토픽 문서 파일명 (예: sql_tuning.html)")
    ap.add_argument("--dir", type=Path, default=ROOT / "assets", help="HTML 자산 폴더")
    ap.add_argument("--days-dir", type=Path, default=ROOT / "days", help="일차 산출물 폴더")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--force", action="store_true", help="HTML 검증 실패해도 진행")
    args = ap.parse_args(argv)

    base = args.dir
    day_dir = args.days_dir / str(args.day)
    doc = base / args.doc
    hub = base / sv.HUB

    if not doc.exists():
        print(f"✗ 문서 없음: {doc}"); return 1

    # 1) 동기화·검증 (문서 편집분 재주입)
    print(f"\n■ 1) 동기화·검증")
    cmd = [sys.executable, "sync_and_verify.py", "--dir", str(base)]
    if args.force:
        cmd.append("--force")  # 실패해도 문서 재주입본을 허브에 기록
    rc = run(cmd)
    if rc != 0 and not args.force:
        print("✗ 검증 실패 — 중단(--force 로 진행 가능).")
        return 1

    # 1b) 저작 품질 린트 (조언) — 난이도 대비 설명 + 얼버무림
    print(f"\n■ 1b) 저작 품질 린트 (난이도 매칭)")
    run([sys.executable, "lint_authoring.py", str(doc)])
    print(f"\n■ 1c) 얼버무림 검사")
    run([sys.executable, "lint_vagueness.py", str(doc)])

    # 2) 문제 검수 → 주입
    quiz = day_dir / "quiz.json"
    if quiz.exists():
        print(f"\n■ 2a) 문제 검수 (출제자 검수 시트)")
        rc = run([sys.executable, "check_quiz.py", str(quiz), "--doc", str(doc), "--day", str(args.day)])
        if rc != 0 and not args.force:
            print("✗ 문제 구조 오류 — 주입 중단(--force 로 진행 가능).")
            return 1
        print(f"\n■ 2) 문제 주입")
        if run([sys.executable, "inject_quiz.py", str(quiz), "--day", str(args.day), "--hub", str(hub)]) != 0:
            print("✗ 문제 주입 실패"); return 1
        if not hub_js_ok(hub):
            print("✗ 주입 후 허브 JS 깨짐 — 중단."); return 1
    else:
        print(f"\n■ 2) 문제 주입 — 건너뜀 (없음: {quiz})")

    # 3) 일차 덱
    day_spec = day_dir / f"{args.day}.slides.json"
    if day_spec.exists():
        print(f"\n■ 3) 일차 덱 렌더")
        day_pptx = OUT / f"day{args.day}.pptx"
        if run(["node", "build_ppt.js", str(day_spec), "-o", str(day_pptx)]) == 0:
            run([sys.executable, "scripts/rezip.py", str(day_pptx)])
            run([sys.executable, "notes_export.py", str(day_spec)])  # 발표 대본(노트) 별도 파일
            if args.preview:
                run(["node", "preview.js", str(day_spec)])
    else:
        print(f"\n■ 3) 일차 덱 — 건너뜀 (없음: {day_spec})")

    # 4) 문서 전체 덱
    print(f"\n■ 4) 문서 전체 덱")
    stem = doc.stem
    spec = OUT / f"{stem}.slides.json"
    pptx = OUT / f"{stem}.pptx"
    if run([sys.executable, "extract_slides.py", str(doc), "-o", str(spec)]) == 0:
        if run(["node", "build_ppt.js", str(spec), "-o", str(pptx)]) == 0:
            run([sys.executable, "scripts/rezip.py", str(pptx)])
            if args.preview:
                run(["node", "preview.js", str(spec)])

    # 5) 관리 대시보드 갱신
    print(f"\n■ 5) 대시보드 갱신")
    run([sys.executable, "build_dashboard.py"])

    # 6) 자료실 갱신 (덱 → files/ 복사 + index.html)
    print(f"\n■ 6) 자료실 갱신")
    run([sys.executable, "build_library.py"])

    print("\n✓ 완료 — out/ · assets/dashboard.html · index.html 확인.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
