#!/usr/bin/env python3
"""대화로 저작한 하루치 문제(JSON)를 학습 허브의 JS 배열에 주입한다.

허브(study_hub_full.html)의 데이터 배열을 편집한다:
  MCQ   += {id,d,q,o:[],a,e}
  ESSAY += {id,d,q,a,k:[]}
  TERMS += {t,e,d}            (d = 상세설명. 일차 필드 없음)
  PLANQ += {id,q,plan,a}
그리고 DAYS 에 해당 일차를 추가하고, 없으면 날짜 칩(--dNN 색 변수 + .dtNN)을 만든다.

**멱등**: 이미 있는 id(또는 TERMS의 t)는 건너뛴다. 주입 후 JS 문법은 호출측(make_day/
sync_and_verify)에서 node --check 로 재검증한다.

사용법:
    python inject_quiz.py days/71/quiz.json --day 71 --hub assets/study_hub_full.html
    python inject_quiz.py days/71/quiz.json --day 71 --dry-run   # 미리보기만
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 배열별 (키 순서, id 필드). TERMS 는 id 대신 t 로 중복 판단.
SCHEMA = {
    "MCQ": (["id", "d", "q", "o", "a", "e"], "id"),
    "ESSAY": (["id", "d", "q", "a", "k"], "id"),
    "TERMS": (["t", "e", "d"], "t"),
    "PLANQ": (["id", "q", "plan", "a"], "id"),
}
# 새 일차 칩 색상 후보 (기존과 겹치지 않게 순환)
CHIP_COLORS = ["#C74634", "#0563C1", "#70AD47", "#7C3AED", "#0F766E", "#B45309", "#BE185D", "#4338CA"]


def js_literal(item: dict, keys: list[str]) -> str:
    """dict → JS 객체 리터럴(키는 unquoted, 값은 JSON 이스케이프)."""
    parts = []
    for k in keys:
        if k not in item:
            continue
        parts.append(f"{k}:{json.dumps(item[k], ensure_ascii=False)}")
    return "{" + ",".join(parts) + "}"


def existing_ids(array_body: str, id_field: str) -> set[str]:
    if id_field == "id":
        return set(re.findall(r"\bid:\s*['\"]([^'\"]+)['\"]", array_body))
    # TERMS: t 로 판단
    return set(re.findall(r"\bt:\s*\"((?:[^\"\\]|\\.)*)\"", array_body))


def inject_array(hub: str, name: str, items: list[dict], rep: list[str]) -> str:
    keys, id_field = SCHEMA[name]
    m = re.search(r"(const\s+" + name + r"\s*=\s*\[)(.*?)(\]\s*;)", hub, re.S)
    if not m:
        rep.append(f"✗ {name} 배열을 허브에서 찾지 못함")
        return hub
    head, body, tail = m.group(1), m.group(2), m.group(3)
    have = existing_ids(body, id_field)
    new_lits = []
    for it in items:
        key = it.get(id_field)
        if key in have:
            rep.append(f"· {name} 건너뜀(이미 있음): {key}")
            continue
        new_lits.append(js_literal(it, keys))
        rep.append(f"+ {name} 추가: {key}")
    if not new_lits:
        return hub
    sep = ",\n  "
    trimmed = body.rstrip().rstrip(",")
    new_body = trimmed + sep + sep.join(new_lits) + "\n"
    return hub[:m.start()] + head + new_body + tail + hub[m.end():]


def add_day(hub: str, day: int, rep: list[str]) -> str:
    m = re.search(r"(const\s+DAYS\s*=\s*\[)(.*?)(\]\s*;)", hub, re.S)
    if not m:
        rep.append("✗ DAYS 배열을 찾지 못함")
        return hub
    body = m.group(2)
    if re.search(r"(^|[,\[])\s*" + str(day) + r"\s*([,\]])", body):
        rep.append(f"· DAYS 이미 포함: {day}")
        return hub
    # '심화' 앞에 삽입, 없으면 끝에
    if "'심화'" in body or '"심화"' in body:
        new_body = re.sub(r"(,\s*)(['\"]심화['\"])", rf",{day}\1\2", body, count=1)
    else:
        new_body = body.rstrip().rstrip(",") + f",{day}"
    rep.append(f"+ DAYS 추가: {day}")
    return hub[:m.start()] + m.group(1) + new_body + m.group(3) + hub[m.end():]


def add_day_chip(hub: str, day: int, rep: list[str]) -> str:
    # 변수·배지·필터칩을 각각 독립 체크 — 하나만 빠져도 그것만 채운다(중복/누락 방지).
    have_var = bool(re.search(r"--d" + str(day) + r"\s*:", hub))
    have_badge = bool(re.search(r"\.dt" + str(day) + r"\s*\{", hub))          # 카드 배지 .dtNN
    have_filter = bool(re.search(r"\.chip\.d" + str(day) + r"\.on\s*\{", hub))  # 필터 버튼 .chip.dNN.on
    if have_var and have_badge and have_filter:
        rep.append(f"· 날짜 칩 이미 존재: {day}")
        return hub
    used = set(re.findall(r"--d\d+\s*:\s*(#[0-9A-Fa-f]{6})", hub))
    color = next((c for c in CHIP_COLORS if c not in used), CHIP_COLORS[day % len(CHIP_COLORS)])

    # --dNN 색 변수: 없을 때만, 마지막 --dNN 정의 뒤에 추가
    if not have_var:
        var_matches = list(re.finditer(r"--d\d+\s*:\s*#[0-9A-Fa-f]{6};", hub))
        if var_matches:
            last = var_matches[-1]
            hub = hub[:last.end()] + f"--d{day}:{color};" + hub[last.end():]
            rep.append(f"+ 색 변수 --d{day}:{color}")
    # .dtNN 배지: 없을 때만, 마지막 .dtNN 정의 뒤에 추가 (배경=색, 글자=흰색 → 항상 대비 확보)
    if not have_badge:
        chip_matches = list(re.finditer(r"\.dt\d+\s*\{[^}]*\}", hub))
        if chip_matches:
            last = chip_matches[-1]
            hub = hub[:last.end()] + f".dt{day}{{background:var(--d{day});color:#fff}}" + hub[last.end():]
            rep.append(f"+ 배지 .dt{day}")
    # .chip.dNN.on 필터 버튼: 없을 때만, 마지막 .chip.dX.on 뒤에 추가
    # (없으면 선택 시 .chip.on{color:#fff}만 걸려 흰 배경+흰 글자로 안 보임)
    if not have_filter:
        filt_matches = list(re.finditer(r"\.chip\.d\w+\.on\s*\{[^}]*\}", hub))
        if filt_matches:
            last = filt_matches[-1]
            hub = hub[:last.end()] + f".chip.d{day}.on{{background:var(--d{day});border-color:var(--d{day})}}" + hub[last.end():]
            rep.append(f"+ 필터칩 .chip.d{day}.on")
    return hub


def inject(hub: str, quiz: dict, day: int, rep: list[str]) -> str:
    for name in ("MCQ", "ESSAY", "TERMS", "PLANQ"):
        items = quiz.get(name) or []
        if items:
            hub = inject_array(hub, name, items, rep)
    hub = add_day(hub, day, rep)
    hub = add_day_chip(hub, day, rep)
    return hub


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="하루치 문제를 허브에 주입")
    ap.add_argument("quiz", type=Path, help="문제 JSON (MCQ/ESSAY/TERMS/PLANQ)")
    ap.add_argument("--day", type=int, required=True, help="일차 (예: 71)")
    ap.add_argument("--hub", type=Path, default=Path("assets/study_hub_full.html"))
    ap.add_argument("--dry-run", action="store_true", help="쓰지 않고 미리보기만")
    args = ap.parse_args(argv)

    if not args.quiz.exists():
        print(f"[inject] 문제 파일 없음: {args.quiz}", file=sys.stderr); return 1
    if not args.hub.exists():
        print(f"[inject] 허브 없음: {args.hub}", file=sys.stderr); return 1

    quiz = json.loads(args.quiz.read_text(encoding="utf-8"))
    hub = args.hub.read_text(encoding="utf-8")
    rep: list[str] = []
    new_hub = inject(hub, quiz, args.day, rep)

    print(f"[inject] {args.quiz} → {args.hub} (day {args.day})")
    for line in rep:
        print("  " + line)

    if args.dry_run:
        print("  (dry-run — 쓰지 않음)")
        return 0
    args.hub.write_text(new_hub, encoding="utf-8")
    print("  ✓ 저장 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
