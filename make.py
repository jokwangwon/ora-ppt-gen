#!/usr/bin/env python3
"""파이프라인 엔트리 — 동기화·검증 → 추출 → 렌더 → (QA).

HTML 학습 문서(소스 오브 트루스)에서 발표용 PPTX를 만든다.

사용 예:
    python make.py assets/sql_tuning.html            # 한 문서
    python make.py --all --dir assets                # 4개 문서 전부
    python make.py assets/sql_tuning.html --preview  # QA 스크린샷까지
    python make.py assets/sql_tuning.html --force    # HTML 검증 실패해도 PPT는 생성

동작:
  1) sync_and_verify.py 로 폴더 동기화·재주입·검증. 검증 실패 시 중단(--force로 무시).
     (SVG 검은박스/JS 문법 등 HTML 자체 문제는 PPT 품질과 무관하므로 --force 제공)
  2) extract_slides.py 로 문서 → 슬라이드 스펙 JSON.
  3) build_ppt.js 로 스펙 → PPTX, 이어서 scripts/rezip.py 로 재압축.
  4) --preview 시 preview.js 로 슬라이드별 QA 이미지 생성.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

# --all 대상 (docsrc 매핑과 동일)
ALL_DOCS = ["sql_tuning.html", "guide_62_68.html", "rman_recovery.html", "buffer_cache_dbwr_checkpoint.html"]


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=ROOT).returncode


def verify_folder(base: Path, force: bool) -> bool:
    print("\n■ 1) 동기화 · 검증")
    rc = run([sys.executable, "sync_and_verify.py", "--dir", str(base)])
    if rc != 0:
        if force:
            print("⚠ 검증 실패했지만 --force 로 PPT 생성을 계속합니다 "
                  "(SVG 검은박스/JS 문제는 HTML에서 별도 수정 권장).")
            return True
        print("✗ 검증 실패 — 중단합니다. HTML을 고치거나 --force 로 PPT만 생성하세요.")
        return False
    return True


def build_one(doc: Path, preview: bool) -> bool:
    stem = doc.stem
    spec = OUT / f"{stem}.slides.json"
    pptx = OUT / f"{stem}.pptx"

    print(f"\n■ 2) 추출: {doc.name}")
    if run([sys.executable, "extract_slides.py", str(doc), "-o", str(spec)]) != 0:
        return False

    print(f"\n■ 3) 렌더: {spec.name} → {pptx.name}")
    if run(["node", "build_ppt.js", str(spec), "-o", str(pptx)]) != 0:
        return False
    run([sys.executable, "scripts/rezip.py", str(pptx)])

    if preview:
        print(f"\n■ 4) QA 프리뷰: {spec.name}")
        run(["node", "preview.js", str(spec)])
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HTML 학습 문서 → PPTX 파이프라인")
    ap.add_argument("doc", nargs="?", type=Path, help="입력 HTML 문서 (단일)")
    ap.add_argument("--all", action="store_true", help="--dir 안의 4개 문서 전부")
    ap.add_argument("--dir", type=Path, default=ROOT / "assets", help="HTML 자산 폴더")
    ap.add_argument("--preview", action="store_true", help="QA 스크린샷 생성")
    ap.add_argument("--force", action="store_true", help="HTML 검증 실패해도 PPT 생성")
    ap.add_argument("--skip-verify", action="store_true", help="검증 단계 생략")
    args = ap.parse_args(argv)

    if not args.all and not args.doc:
        ap.error("문서 경로를 주거나 --all 을 지정하세요.")

    base = args.dir
    if not args.skip_verify:
        if not verify_folder(base, args.force):
            return 1

    docs = [base / d for d in ALL_DOCS] if args.all else [args.doc]
    ok = True
    for doc in docs:
        if not doc.exists():
            print(f"⚠ 문서 없음, 건너뜀: {doc}")
            ok = False
            continue
        if not build_one(doc, args.preview):
            ok = False

    print("\n" + ("✓ 완료 — out/ 폴더 확인." if ok else "△ 일부 실패 — 로그 확인."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
