#!/usr/bin/env python3
"""출제자 검수 — quiz.json 정답 체크 (자습 58~60분 · 문제당 10초).

세 가지를 한 번에:
  1) 구조 검증(차단) : 정답 인덱스 범위·보기 수·id 중복·일차(d) 일치 — 틀리면 rc 1
  2) 검수 시트       : 문제마다 ✔정답 보기를 표시해 눈으로 10초 확인 (+md 파일)
  3) 근거 대조(조언) : 해설·정답의 숫자가 원문 문서에 있는지 — 없으면 ⚠ 표시

워밍업(자습 0~5분): 어제 문제 3개 뽑기
  python check_quiz.py days/72/quiz.json --warmup        # 문제만 → 맨 끝에 정답

사용법:
  python check_quiz.py days/73/quiz.json --doc assets/sql_tuning.html
  python check_quiz.py days/73/quiz.json --doc assets/sql_tuning.html -o out/day73.quizcheck.md
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

OK, BAD, WARN = "✓", "✗", "⚠"


def strip_tags(html: str) -> str:
    html = re.sub(r"<script[^>]*type=[\"']text/plain[\"'][\s\S]*?</script>", " ", html)
    return re.sub(r"<[^>]+>", " ", html)


def numbers_of(text: str) -> list[str]:
    """근거 대조용 숫자 추출 — 2자리 이상(연도·일차·백분율 꼬리 제외한 러프 추출)."""
    nums = re.findall(r"\d[\d,\.]*", text)
    out = []
    for n in nums:
        plain = n.rstrip(".").replace(",", "")
        if len(plain) >= 2 and not re.fullmatch(r"(19|20)\d\d", plain):  # 연도 제외
            out.append(plain)
    return sorted(set(out))


def structural_errors(quiz: dict, day: int | None) -> list[str]:
    errs = []
    ids = []
    for it in quiz.get("MCQ", []):
        qid = it.get("id", "?")
        ids.append(qid)
        o, a = it.get("o", []), it.get("a", None)
        if len(o) < 2:
            errs.append(f"MCQ {qid}: 보기가 {len(o)}개 (2개 이상 필요)")
        if not isinstance(a, int) or not (0 <= a < len(o)):
            errs.append(f"MCQ {qid}: 정답 인덱스 a={a!r} 가 보기 범위(0~{len(o)-1}) 밖")
        if day is not None and it.get("d") not in (day, "심화"):
            errs.append(f"MCQ {qid}: d={it.get('d')!r} 가 일차({day})와 다름")
        if not it.get("e"):
            errs.append(f"MCQ {qid}: 해설(e) 없음")
    for it in quiz.get("ESSAY", []):
        qid = it.get("id", "?")
        ids.append(qid)
        if not it.get("a"):
            errs.append(f"ESSAY {qid}: 모범답안(a) 없음")
        if not it.get("k"):
            errs.append(f"ESSAY {qid}: 채점 키워드(k) 없음")
    for it in quiz.get("PLANQ", []):
        qid = it.get("id", "?")
        ids.append(qid)
        if not it.get("plan") or not it.get("a"):
            errs.append(f"PLANQ {qid}: plan 또는 정답(a) 없음")
    for it in quiz.get("TERMS", []):
        if not it.get("t") or not it.get("e"):
            errs.append(f"TERMS {it.get('t','?')}: t/e 필수")
    dup = {x for x in ids if ids.count(x) > 1}
    if dup:
        errs.append(f"id 중복: {sorted(dup)}")
    return errs


def length_bias(quiz: dict) -> list[str]:
    """정답 길이 편향(조언) — '제일 긴 보기가 정답' 패턴이 시험 요령으로 뚫리는 문제.

    문제 단위: 정답이 유일하게 최장이고 2위보다 30%+ 길면 지적.
    세트 단위: 절반 이상에서 '정답=최장'이면 세트 전체 경향으로 지적.
    """
    warns, longest_correct, n = [], 0, 0
    for it in quiz.get("MCQ", []):
        o, a = it.get("o", []), it.get("a")
        if not isinstance(a, int) or not (0 <= a < len(o)) or len(o) < 2:
            continue
        n += 1
        lens = [len(x) for x in o]
        if lens[a] == max(lens) and lens.count(max(lens)) == 1:
            longest_correct += 1
            runner = max(v for i, v in enumerate(lens) if i != a)
            if lens[a] > runner * 1.3:
                warns.append(f"MCQ {it.get('id','?')}: 정답({lens[a]}자)이 2위({runner}자)보다 30%+ 김 — 오답을 살찌우거나 정답을 다듬기")
    if n and longest_correct * 2 >= n and n >= 3:
        warns.append(f"세트 경향: {n}문제 중 {longest_correct}개가 '정답=최장 보기' — 길이만 보고 찍힌다")
    return warns


def grounding(text: str, doc_text: str | None) -> tuple[list[str], list[str]]:
    """텍스트의 숫자들이 원문에 있는지. (있는것, 없는것)

    추출기가 콤마를 벗기므로(1,1,2 → 112) 원문도 콤마 제거본을 함께 대조 —
    순위 나열(1,1,3) 같은 표기가 허위 ⚠로 뜨지 않게 한다.
    """
    if doc_text is None:
        return [], []
    doc_nocomma = doc_text.replace(",", "")
    found, missing = [], []
    for n in numbers_of(text):
        (found if (n in doc_text or n in doc_nocomma) else missing).append(n)
    return found, missing


def sheet(quiz: dict, doc_text: str | None) -> tuple[str, int]:
    """검수 시트 md + 근거 미확인 수."""
    lines = ["# 출제자 검수 시트", "", "> 문제당 10초: ✔가 진짜 정답인가 · 해설이 원문과 맞는가 · ⚠는 원문에서 재확인", ""]
    warn_count = 0
    for it in quiz.get("MCQ", []):
        lines.append(f"## [{it['id']}] {it['q']}")
        for i, opt in enumerate(it.get("o", [])):
            mark = "✔" if i == it.get("a") else "  "
            lines.append(f"- {mark} ({i}) {opt}")
        lines.append(f"- 해설: {it.get('e','')}")
        basis = (it.get("o", [""] * (it.get("a", 0) + 1))[it.get("a", 0)] if isinstance(it.get("a"), int) and it.get("a", -1) < len(it.get("o", [])) else "") + " " + it.get("e", "")
        found, missing = grounding(basis, doc_text)
        if doc_text is not None:
            if missing:
                warn_count += 1
                lines.append(f"- 근거 숫자: {OK} {' '.join(found) or '-'} · {WARN} 원문 미확인: **{' '.join(missing)}**")
            else:
                lines.append(f"- 근거 숫자: {OK} {' '.join(found) or '(숫자 없음)'}")
        lines.append("")
    for it in quiz.get("PLANQ", []):
        lines.append(f"## [{it['id']}] (실행계획) {it['q']}")
        lines.append(f"- 정답 요지: {it.get('a','')[:180]}…")
        found, missing = grounding(it.get("a", ""), doc_text)
        if doc_text is not None and missing:
            warn_count += 1
            lines.append(f"- {WARN} 원문 미확인 숫자: **{' '.join(missing)}**")
        lines.append("")
    for it in quiz.get("ESSAY", []):
        lines.append(f"## [{it['id']}] (서술) {it['q']}")
        lines.append(f"- 키워드: {' · '.join(it.get('k', []))}")
        found, missing = grounding(it.get("a", ""), doc_text)
        if doc_text is not None and missing:
            warn_count += 1
            lines.append(f"- {WARN} 원문 미확인 숫자: **{' '.join(missing)}**")
        lines.append("")
    if quiz.get("TERMS"):
        lines.append("## 용어")
        for it in quiz["TERMS"]:
            lines.append(f"- **{it['t']}** — {it['e']}")
        lines.append("")
    return "\n".join(lines), warn_count


def warmup(quiz: dict, n: int = 3) -> str:
    mcq = quiz.get("MCQ", [])
    pick = random.sample(mcq, min(n, len(mcq)))
    out = ["■ 워밍업 — 어제 문제 (답은 맨 아래)", ""]
    for i, it in enumerate(pick, 1):
        out.append(f"{i}. {it['q']}")
        for j, opt in enumerate(it["o"]):
            out.append(f"   {'ABCD'[j]}) {opt}")
        out.append("")
    out.append("--- 정답 ---")
    for i, it in enumerate(pick, 1):
        out.append(f"{i}. {'ABCD'[it['a']]}  ({it['e'][:80]}…)")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="quiz.json 출제자 검수")
    ap.add_argument("quiz", type=Path)
    ap.add_argument("--doc", type=Path, help="근거 대조할 원문 문서 (assets/*.html)")
    ap.add_argument("--day", type=int, help="일차 (생략 시 폴더명에서 추정)")
    ap.add_argument("-o", "--out", type=Path, help="검수 시트 md 저장 위치")
    ap.add_argument("--warmup", action="store_true", help="문제 3개 뽑기(정답은 맨 끝)")
    args = ap.parse_args(argv)

    if not args.quiz.exists():
        print(f"{BAD} 파일 없음: {args.quiz}"); return 1
    quiz = json.loads(args.quiz.read_text(encoding="utf-8"))

    if args.warmup:
        print(warmup(quiz)); return 0

    day = args.day
    if day is None and args.quiz.parent.name.isdigit():
        day = int(args.quiz.parent.name)

    # 1) 구조 검증 (차단)
    errs = structural_errors(quiz, day)
    if errs:
        print(f"{BAD} 구조 오류 {len(errs)}건 — 주입 전에 고치세요:")
        for e in errs:
            print(f"   {BAD} {e}")
        return 1

    # 2·3) 검수 시트 + 근거 대조
    doc_text = None
    if args.doc:
        p = args.doc if args.doc.exists() else Path("assets") / args.doc.name
        if p.exists():
            doc_text = strip_tags(p.read_text(encoding="utf-8"))
    md, warns = sheet(quiz, doc_text)
    out = args.out or Path("out") / f"day{day}.quizcheck.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    n_m, n_e, n_t, n_p = (len(quiz.get(k, [])) for k in ("MCQ", "ESSAY", "TERMS", "PLANQ"))
    print(f"{OK} 구조 통과 — MCQ {n_m}·ESSAY {n_e}·TERMS {n_t}·PLANQ {n_p}")
    bias = length_bias(quiz)
    if bias:
        print(f"{WARN} 정답 길이 편향 {len(bias)}건:")
        for b in bias:
            print(f"   {WARN} {b}")
    else:
        print(f"{OK} 정답 길이 편향 없음")
    if doc_text is not None:
        print(f"{OK if warns == 0 else WARN} 근거 대조 — 원문 미확인 숫자 있는 문제 {warns}건" + ("" if warns == 0 else " (시트에서 ⚠ 확인)"))
    else:
        print(f"{WARN} --doc 미지정: 근거 대조 생략")
    print(f"[검수 시트] {out}  ← 문제당 10초, ✔정답·해설 눈으로 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
