#!/usr/bin/env python3
"""검토 상태 관리 CLI — review_status.json 을 갱신하고 대시보드를 재생성한다.

'검토'는 사람이 확인했다는 뜻, '정확성'은 사실 오류를 LLM 정독으로 검증했다는 뜻.
원본 문서는 수업 중 손으로 작성돼 사실 오류가 있을 수 있으므로 둘을 분리해 관리한다.

사용법:
    python review.py list
    python review.py mark guide_62_68.html --status reviewed --note "확인함"
    python review.py accuracy rman_recovery.html --issues 5 --method "LLM 정독"
    python review.py day 71 --status published --note "..."
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "review_status.json"
VALID = {"reviewed", "reviewing", "unreviewed"}


def _today() -> str:
    return datetime.date.today().isoformat()


def _load() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {"docs": {}, "days": {}}


def _save(data: dict) -> None:
    STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rebuild() -> None:
    try:
        import build_dashboard
        build_dashboard.main([])
    except Exception as e:  # 대시보드 실패가 상태 저장을 막지 않도록
        print(f"[review] 대시보드 재생성 건너뜀: {e}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="검토 상태 관리")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="현재 상태 요약")

    p_mark = sub.add_parser("mark", help="문서 검토 상태 지정")
    p_mark.add_argument("doc")
    p_mark.add_argument("--status", choices=sorted(VALID), default="reviewed")
    p_mark.add_argument("--note", default=None)

    p_acc = sub.add_parser("accuracy", help="문서 정확성(사실검증) 기록")
    p_acc.add_argument("doc")
    p_acc.add_argument("--issues", type=int, default=0, help="발견/수정 이슈 수")
    p_acc.add_argument("--method", default="LLM 정독")
    p_acc.add_argument("--uncheck", action="store_true", help="검증 안 됨으로 표시")

    p_day = sub.add_parser("day", help="일차 상태 지정")
    p_day.add_argument("day")
    p_day.add_argument("--status", choices=sorted(VALID | {"published"}), default="published")
    p_day.add_argument("--note", default=None)

    args = ap.parse_args(argv)
    data = _load()
    data.setdefault("docs", {})
    data.setdefault("days", {})

    if args.cmd == "list":
        for name, st in data["docs"].items():
            acc = st.get("accuracy", {})
            a = f"정확성 {'✔' if acc.get('checked') else '⚠미검증'}"
            print(f"  {name:42} {st.get('status','unreviewed'):11} {a}  {st.get('note','')}")
        for day, st in data["days"].items():
            print(f"  {day}일차  {st.get('status','')}  {st.get('note','')}")
        return 0

    if args.cmd == "mark":
        d = data["docs"].setdefault(args.doc, {})
        d["status"] = args.status
        d["reviewed_at"] = _today()
        if args.note is not None:
            d["note"] = args.note
        _save(data)
        print(f"[review] {args.doc} → {args.status} ({_today()})")
        _rebuild()
        return 0

    if args.cmd == "accuracy":
        d = data["docs"].setdefault(args.doc, {})
        d["accuracy"] = {"checked": not args.uncheck, "at": _today(),
                         "issues": args.issues, "method": args.method}
        _save(data)
        print(f"[review] {args.doc} 정확성 {'미검증' if args.uncheck else '검증'} "
              f"(이슈 {args.issues}, {args.method})")
        _rebuild()
        return 0

    if args.cmd == "day":
        d = data["days"].setdefault(str(args.day), {})
        d["status"] = args.status
        if args.note is not None:
            d["note"] = args.note
        _save(data)
        print(f"[review] {args.day}일차 → {args.status}")
        _rebuild()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
