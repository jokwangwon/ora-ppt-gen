#!/usr/bin/env python3
"""대화로 저작한 하루치 문제(JSON)를 학습 허브의 JS 배열에 주입한다.

허브(study_hub_full.html)의 데이터 배열을 편집한다:
  MCQ   += {id,d,q,o:[],a,e}
  ESSAY += {id,d,q,a,k:[]}
  TERMS += {t,e,d,day}        (d = 상세설명 텍스트, day = 일차 — 날짜칩 필터용. 주입 시 자동 부여)
  PLANQ += {id,q,plan,a}
그리고 DAYS 에 해당 일차를 추가하고, 없으면 날짜 칩(--dNN 색 변수 + .dtNN)을 만든다.

**멱등 + 갱신**: 이미 있는 id(또는 TERMS의 t)는 — 내용이 같으면 건너뛰고, 내용이
바뀌었으면 그 자리에서 교체한다(update-in-place). days/N/quiz.json 이 소스 오브 트루스:
문제를 고치면 재주입으로 허브가 따라온다. 주입 후 JS 문법은 호출측(make_day/
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
    "TERMS": (["t", "e", "d", "day"], "t"),
    "PLANQ": (["id", "q", "plan", "a", "k"], "id"),
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


def find_literal(body: str, id_field: str, key: str) -> tuple[int, int] | None:
    """array body 안에서 id_field:key 를 가진 객체 리터럴의 (시작,끝) 위치.

    문자열 리터럴('…' / "…", 이스케이프 포함)을 인식하며 중괄호 짝을 맞춘다 —
    plan/해설 텍스트에 { } , 가 들어 있어도 안전하다.
    """
    km = re.search(id_field + r":\s*" + re.escape(json.dumps(key, ensure_ascii=False)), body) \
        or re.search(id_field + r":\s*'" + re.escape(key) + r"'", body)
    if not km:
        return None
    # 뒤로 스캔해 이 항목의 여는 '{' 를 찾는다 (직전의 최상위 '{')
    start = body.rfind("{", 0, km.start())
    if start == -1:
        return None
    depth, i, in_str, quote = 0, start, False, ""
    while i < len(body):
        c = body[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                in_str = False
        elif c in "'\"":
            in_str, quote = True, c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (start, i + 1)
        i += 1
    return None


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
        lit = js_literal(it, keys)
        if key in have:
            # 이미 있음 — 내용이 다르면 그 자리에서 교체 (days 파일이 소스 오브 트루스)
            span = find_literal(body, id_field, key)
            if span and body[span[0]:span[1]] != lit:
                body = body[:span[0]] + lit + body[span[1]:]
                rep.append(f"~ {name} 갱신: {key}")
            else:
                rep.append(f"· {name} 건너뜀(동일): {key}")
            continue
        new_lits.append(lit)
        rep.append(f"+ {name} 추가: {key}")
    if new_lits:
        sep = ",\n  "
        body = body.rstrip().rstrip(",") + sep + sep.join(new_lits) + "\n"
    return hub[:m.start()] + head + body + tail + hub[m.end():]


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
    # ⚠ 반드시 메인 <style> 범위(hub[:style_end]) 안에서만 찾고/넣는다 —
    #   허브에는 docsrc(내장 문서)의 CSS도 통째로 들어 있어, 전체 검색은
    #   내장 문서 쪽(무효 영역)에 주입되는 사고가 난다(73일차 --d73 버그).
    style_end = hub.find("</style>")
    region = hub[:style_end] if style_end != -1 else hub

    have_var = bool(re.search(r"--d" + str(day) + r"\s*:", region))
    have_badge = bool(re.search(r"\.dt" + str(day) + r"\s*\{", region))          # 카드 배지 .dtNN
    have_filter = bool(re.search(r"\.chip\.d" + str(day) + r"\.on\s*\{", region))  # 필터 버튼 .chip.dNN.on
    if have_var and have_badge and have_filter:
        rep.append(f"· 날짜 칩 이미 존재: {day}")
        return hub
    used = set(re.findall(r"--d\d+\s*:\s*(#[0-9A-Fa-f]{6})", region))
    color = next((c for c in CHIP_COLORS if c not in used), CHIP_COLORS[day % len(CHIP_COLORS)])

    # --dNN 색 변수: 없을 때만, (메인 style 내) 마지막 --dNN 정의 뒤에 추가
    if not have_var:
        var_matches = list(re.finditer(r"--d\d+\s*:\s*#[0-9A-Fa-f]{6};", region))
        if var_matches:
            last = var_matches[-1]
            hub = hub[:last.end()] + f"--d{day}:{color};" + hub[last.end():]
            rep.append(f"+ 색 변수 --d{day}:{color}")
    # .dtNN 배지: 없을 때만, (메인 style 내) 마지막 .dtNN 정의 뒤에 추가
    if not have_badge:
        region = hub[:hub.find("</style>")]
        chip_matches = list(re.finditer(r"\.dt\d+\s*\{[^}]*\}", region))
        if chip_matches:
            last = chip_matches[-1]
            hub = hub[:last.end()] + f".dt{day}{{background:var(--d{day});color:#fff}}" + hub[last.end():]
            rep.append(f"+ 배지 .dt{day}")
    # .chip.dNN.on 필터 버튼: 없을 때만, (메인 style 내) 마지막 .chip.dX.on 뒤에 추가
    # (없으면 선택 시 .chip.on{color:#fff}만 걸려 흰 배경+흰 글자로 안 보임)
    if not have_filter:
        region = hub[:hub.find("</style>")]
        filt_matches = list(re.finditer(r"\.chip\.d\w+\.on\s*\{[^}]*\}", region))
        if filt_matches:
            last = filt_matches[-1]
            hub = hub[:last.end()] + f".chip.d{day}.on{{background:var(--d{day});border-color:var(--d{day})}}" + hub[last.end():]
            rep.append(f"+ 필터칩 .chip.d{day}.on")
    return hub


def inject(hub: str, quiz: dict, day: int, rep: list[str]) -> str:
    for name in ("MCQ", "ESSAY", "TERMS", "PLANQ"):
        items = quiz.get(name) or []
        if name == "TERMS":
            # 날짜칩 필터용 일차 태그 (d 는 상세설명 텍스트라 별도 필드)
            items = [{**it, "day": it.get("day", day)} for it in items]
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
