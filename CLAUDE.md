# CLAUDE.md — 작업 규칙 요약 (다음 세션용)

Oracle DBA 학습 자료 파이프라인. **HTML 학습 문서(소스 오브 트루스)** 에서
발표용 **PPTX** 를 만들고, 학습 허브의 동기화·검증을 자동화한다.
PPT는 HTML에서 파생하되 **새 사실을 지어내지 않는다.**

## 파일 구조

| 경로 | 역할 |
|------|------|
| `sync_and_verify.py` | 동기화(한글→ASCII) · 재주입(docsrc-*) · 검증. **검증 실패 시 멈춤**(`--force`로 무시). |
| `inject_quiz.py`     | 하루치 문제(JSON)를 허브 JS 배열(MCQ/ESSAY/TERMS/PLANQ)·DAYS·날짜칩에 주입(멱등) |
| `make_day.py`        | **일차 파이프라인** — 동기화·검증 → 문제 주입 → 일차 덱 + 문서 덱 + QA |
| `extract_slides.py`  | HTML 문서 → 슬라이드 스펙 JSON (추출) |
| `layout.js`          | 레이아웃 엔진 — 좌표/페이지네이션 (렌더러·프리뷰 공유) |
| `build_ppt.js`       | 스펙 JSON → PPTX (pptxgenjs, 참고 디자인) |
| `preview.js`         | 스펙 → HTML(동일 좌표) → 슬라이드 PNG (Chromium QA) |
| `scripts/rezip.py`   | pptxgenjs 출력 재압축 |
| `make.py`            | 파이프라인 엔트리 (위를 묶음) |
| `assets/`            | HTML 자산 (문서 4종 + `study_hub_full.html`) — git 제외 |
| `ref/`               | 참고 디자인 PPTX (`reference.pptx`) + 언팩 — git 제외 |
| `out/`               | 산출물(JSON/PPTX/QA 이미지) — git 제외 |

## 매일 하는 일 (일일 워크플로)

**저작은 대화(Claude), 배선은 스크립트.** 하루치 노트(`N일차_강사.txt`)가 오면:

1. **[Claude가 대화로 저작]**
   - `assets/<topic>.html` 에 그날 섹션을 문서 스타일로 직접 추가
     (`<section class="part">`·`<h3 class="blk">`·표·`.why`/`.tip`·`<pre class="term">`·인라인 `<svg>`).
     **SVG는 쓰는 `class="nXXX"` 를 그 문서 `<style>`에 반드시 정의**(검은박스 방지).
   - `days/<N>/quiz.json` — 문제(아래 규약)
   - `days/<N>/<N>.slides.json` — 일차 덱 스펙(기존 스펙 포맷; 없으면 일차 덱 생략)
2. **[스크립트가 배선]**
   ```bash
   python make_day.py 71 --doc sql_tuning.html            # 검증→문제주입→일차덱+문서덱
   python make_day.py 71 --doc sql_tuning.html --preview  # + QA 스크린샷
   python make_day.py 71 --doc sql_tuning.html --force    # HTML 검증 실패해도 진행
   ```

### `days/<N>/quiz.json` 규약 (허브 배열과 동일 필드)
```json
{ "MCQ":  [{"id":"m71a","d":71,"q":"...","o":["...","..."],"a":1,"e":"해설"}],
  "ESSAY":[{"id":"e71a","d":71,"q":"...","a":"모범답안","k":["채점 키워드"]}],
  "TERMS":[{"t":"용어","e":"짧은 뜻","d":"자세히"}],
  "PLANQ":[{"id":"pl71a","q":"...","plan":"| Id | ... |","a":"..."}] }
```
`a`(MCQ)=정답 인덱스. `id`(또는 TERMS의 `t`)로 멱등 — 재실행해도 중복 안 됨.

### 문서만/전체만 돌릴 때
```bash
python make.py assets/sql_tuning.html            # 문서 하나 → PPT
python make.py --all                             # 4개 문서 전부
python sync_and_verify.py --dir assets           # 동기화·재주입·검증만
python inject_quiz.py days/71/quiz.json --day 71 --dry-run   # 문제 주입 미리보기
```

## 슬라이드 스펙 JSON (extract ↔ build 계약)

```
{ deck_id, title, subtitle, source, slides:[
  {type:"title"} | {type:"section", num, title, subtitle} |
  {type:"content", title, blocks:[
     {kind:"bullets", items:[]} | {kind:"table", headers:[], rows:[[]]} |
     {kind:"callout", tone:"why|tip", head, body} |
     {kind:"code", lines:[]} | {kind:"figure", caption, summary} ]}
]}
```
build 단계에서 title 뒤 **로드맵**, 맨 끝 **감사** 슬라이드가 자동 추가되고,
`[bullets + callout|figure]` 2개면 좌/우 2단 레이아웃, 넘치면 자동 페이지네이션.

## 참고 디자인 (ref/reference.pptx 에서 추출)

- 팔레트: ink `1E293B` · **Oracle Red `C74634`** · muted `64748B/94A3B8` · dark `0F172A` · card `F1F5F9` · line `E2E8F0`
- 폰트: 본문 **맑은 고딕**, 코드 **Consolas**
- 구성: 다크 타이틀(레드 마스트헤드) · 로드맵 · 큰 숫자 섹션 · 흰 콘텐츠(red 사각+제목, 우상단 `ORACLE`, 하단 푸터+페이지) · 코드 다크카드+신호등 · 2단 비교 · 감사
- 좌여백 0.92, 콘텐츠 폭 11.49, 콘텐츠 y 1.9~6.6, 푸터 y 6.95

## 함정 (반드시 지킬 것)

1. **재주입 이스케이프**: docsrc 주입 시 `</script` → `<\/script` (안 하면 허브가 깨짐). `sync_and_verify.py`가 처리.
2. **SVG 검은박스**: SVG에서 `class="nXXX"` 쓰는데 그 문서 `<style>`에 `.nXXX{` 정의가 없으면 검은 박스. 검증기가 잡는다. **CSS 그룹 선택자(`.a,.b{`)도 정의로 인정** — 정의 추출은 `<style>` 안 선택자 파싱으로 한다(단순 `.x{` 매칭 아님).
3. **JS 검증 범위**: 메인 `<script>`만 `node --check`. `<script type="text/plain">`(docsrc)은 제거 후 검사.
4. **한글 ↔ ASCII**: 원본은 한글 파일명, 배포/주입용은 ASCII 사본. 매핑은 `sync_and_verify.py`의 `KO_TO_ASCII`/`DOCSRC_TO_ASCII`.
5. **HTML 문서/허브 동작을 깨지 말 것.** 검증 실패하면 산출물 내지 말고 원인 보고.
6. **PPT에서 새 사실 지어내지 말 것** — 원문 텍스트만 구조화.

## 환경 특이사항

- **LibreOffice(soffice) 변환이 이 환경에서 멈춤(행)** → SKILL.md의 PDF→이미지 QA 불가.
  대신 `preview.js`가 **동일 좌표**로 HTML 렌더 후 **Chromium**(`/opt/pw-browsers/chromium-1194/...`, playwright-core)으로 스크린샷 → 시각 QA. 실제 .pptx 미세 검수는 PowerPoint/로컬 LibreOffice에서.
- 의존성: `pip install beautifulsoup4 lxml Pillow`, `npm i`(pptxgenjs·playwright-core·react-icons·sharp).

## 알려진 한계

- 추출기는 `<section class="part">` + `<h3 class="blk">` 구조(guide/sql/buffer) 대상.
  `rman_recovery.html`은 plain `<section>`+`<h2>` 구조라 추출량이 적다 → 추후 h2 폴백 추가 여지.
- `sql_tuning.html`은 SVG에서 `.nal`(=`fill:var(--alert-t)`)을 **정의 없이 사용** → 검은박스 후보. 원문 수정 필요(검증기가 매번 지적).
