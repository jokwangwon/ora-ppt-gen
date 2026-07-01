# AUTHORING.md — 정답지 작법 규약 (대화 저작용)

허브 문서(정답지)가 좋은 이유는 **반복 가능한 작법 패턴**이 있기 때문이다.
하루치 노트를 문서·문제·일차 슬라이드로 저작할 때 아래를 따른다.
`lint_authoring.py` 가 이 기준으로 개념을 점수화하고, 얇으면 지적한다.

> 원칙: **원문(노트)의 사실만** 구조화한다. 새 수치·사실을 지어내지 않는다.

## 개념(h3.blk) 하나를 쓸 때 — 체크리스트 (목표 6~7/7)

| # | 패턴 | 방법 |
|---|------|------|
| P1 | **비유 오프너** | 개념을 일상 비유 한 줄로 연다. 문서: `<p class="lead">…</p>` / 슬라이드: `{"kind":"analogy","text":"…"}` |
| P2 | **문제→원인→해결** + 실측 | ①문제 ②원인(알고보니) ③해결(그래서). 노트의 **실측 숫자**를 넣는다(예: 45행→46번이 9번으로). 슬라이드: `{"kind":"steps","items":[{"n":"①","head":"문제 — …","body":"…"}]}` |
| P3 | **실행계획 줄 해석** | Id N ↔ Id M 상호작용을 말로 푼다("작은 NL 루프"). 다이어그램은 `svg_snippets.plan_pair(...)` |
| P4 | **다이어그램 ≥1** | 개념마다 인라인 SVG 1개 이상. **반드시 `svg_snippets.py` 로 생성**(정의된 클래스만 → 검은박스 0). |
| P5 | **why/tip 박스** | `.why`(정의 명확화·메커니즘·효과) + `.tip`(홈랩 실전 팁) |
| P6 | **실측 표** | before/after·수치 대비를 `<table>` 로(예: CF 1,389 vs 36,060 → Buffers 1,548 vs 36,516) |
| P7 | **키워드 강조** | 핵심어는 `<b class="k">…</b>` |

### 문서 HTML 골격 (문서 스타일 그대로)
```html
<section class="part" id="pN">
  <div class="phead"><div class="pnum">NN</div><div>
    <div class="ptitle">제목</div><div class="psub">한 줄 요약</div></div></div>
  <h3 class="blk"><span class="ix">N.1</span>개념 제목</h3>
  <p class="lead">비유 한 줄 …</p>                     <!-- P1 -->
  <p><b class="k">핵심어</b> …</p>
  <!-- P4: svg_snippets 로 생성한 <figure> 붙여넣기 -->
  <table>…</table>                                     <!-- P6 -->
  <div class="why"><span class="h">왜/정의</span>…</div>  <!-- P5 -->
  <div class="tip"><b>홈랩에서 바로</b> …</div>
</section>
```

### SVG는 반드시 헬퍼로 (검은박스 원천 차단)
```python
import svg_snippets as S
S.figure(S.good_bad_grid(good, bad, good_label="…", bad_label="…"), "캡션")   # P6
S.figure(S.flow(["① 문제 …","② 원인 …","③ 해결 …"]), "문제→원인→해결")        # P2
S.figure(S.plan_pair("Id 1  TABLE ACCESS …","Id 2  INDEX RANGE SCAN …", note="…"), "캡션")  # P3
```
사용 클래스는 대상 문서 `<style>`에 정의돼야 한다(guide/sql/buffer: `ntune·ncor·nmut·edge·svg-*`). `sync_and_verify.py` 가 미정의를 잡는다.

## 문제(quiz) 작법 — `days/<N>/quiz.json`

정답지 d:71 스타일: **계산·판정·수치비교 MCQ + 개념연결 ESSAY**.

| 유형 | 규약 | 예(정답지 스타일) |
|------|------|------|
| MCQ | 계산·판정·수치 비교. `a`=정답 인덱스, `e`=해설(왜 정답/오답) | "clustering factor가 '좋다'는 기준은?", "object_name 인덱스의 CF는?" |
| ESSAY | **두 개념을 연결**해 서술. `k`=채점 키워드 | "CF 좋고 나쁨이 성능에 만드는 차이를 24배 실측과 함께 설명" |
| TERMS | 짧은뜻 `e` + 자세히 `d` **2단** | `{"t":"clustering factor","e":"…한 줄…","d":"…메커니즘…"}` |
| PLANQ | 실행계획 텍스트 `plan` + 문제 `q` + 해설 `a` | — |

```json
{ "MCQ":[{"id":"m71a","d":71,"q":"…","o":["…","…"],"a":1,"e":"해설"}],
  "ESSAY":[{"id":"e71a","d":71,"q":"…","a":"모범답안","k":["키워드"]}],
  "TERMS":[{"t":"용어","e":"짧은 뜻","d":"자세히"}],
  "PLANQ":[] }
```
`id`(TERMS는 `t`)로 멱등. 새 사실을 만들지 말고 노트 근거로만 출제한다.

## 일차 슬라이드 스펙 — `days/<N>/<N>.slides.json`

문서와 같은 서사를 담는다(요약 나열 금지). 블록 종류:
`bullets · table · callout(why|tip) · code · figure · **analogy** · **steps**`.
`analogy`+`steps`+`callout` 조합이 정답지식 개념 슬라이드의 기본형.

## 품질 확인
```bash
python lint_authoring.py assets/sql_tuning.html     # 개념별 점수·보강점
# make_day 가 자동 실행: 얇은 개념(<3점)이면 대화로 P1·P2·P4를 보강
```
목표: **강한 초안 → 린터가 약점 지적 → 대화 1~2턴으로 정답지급(6~7/7)**.
