# CLAUDE.md — 작업 규칙 요약 (다음 세션용)

Oracle DBA 학습 자료 파이프라인. **HTML 학습 문서(소스 오브 트루스)** 에서
발표용 **PPTX** 를 만들고, 학습 허브의 동기화·검증을 자동화한다.
PPT는 HTML에서 파생하되 **새 사실을 지어내지 않는다.**

## 파일 구조

| 경로 | 역할 |
|------|------|
| `sync_and_verify.py` | 동기화(한글→ASCII) · 재주입(docsrc-*) · 검증. **검증 실패 시 멈춤**(`--force`로 무시). |
| `inject_quiz.py`     | 하루치 문제(JSON)를 허브 JS 배열(MCQ/ESSAY/TERMS/PLANQ)·DAYS·날짜칩에 주입. **멱등+갱신** — 같은 id의 내용이 바뀌면 그 자리에서 교체(days 파일이 소스 오브 트루스). TERMS엔 `day` 자동 부여(날짜칩 필터용, `d`는 상세설명). |
| `new_day.py`         | **하루치 스캐폴드** — `days/<N>/` 에 복습 노트(review.md)·문제 뼈대(quiz.json) 생성(멱등). 자습 시작 준비. |
| `check_quiz.py`      | **출제자 검수** — quiz.json 구조 검증(정답 인덱스 등, 실패 시 주입 차단) + 검수 시트(✔정답 표시) + 원문 근거 대조 + **정답 길이 편향 검사**(정답이 최장 보기로 30%+ 길거나 세트 절반 이상 '정답=최장'이면 ⚠ — MCQ 저작 시 오답도 정답만큼 구체적으로). `--warmup`=어제 문제 3개. make_day가 주입 전 자동 실행. |
| `inject_compare.py`  | **복습 시트 내장** — `days/N/compare.md`(일일 복습 시트, md)를 HTML로 변환해 허브 '복습' 탭에 주입(멱등). `[텍스트](assets/...#앵커)` 링크는 소비자 위치에 맞게 경로 재작성. 자료실 일지(reviews/)는 build_library가 생성. |
| `make_day.py`        | **일차 파이프라인** — 동기화·검증 → 문제 주입 → 일차 덱 + 문서 덱 + QA + 대시보드 + 자료실 |
| `docs/STUDY_ROUTINE.md` | **자습 1시간 복습 루틴** + 매일 남길 양식 + 양식→파이프라인 지도. 복사용 원본: `days/TEMPLATE.md`. |
| `docs/SYSTEM_OVERVIEW.md` | **AI 핸드오프 문서** — 시스템 목적·구조·워크플로·규칙 전체를 한 문서로(다른 AI에게 설명용). |
| `build_dashboard.py` | 관리 대시보드 생성 → `assets/dashboard.html` (검토·정확성·난이도·린트 한 눈에) |
| `build_library.py`   | **자료실 생성** → 루트 `index.html` + `out/` 덱·대본을 `files/`로 복사(멱등). GitHub Pages(루트)로 공유·다운로드. |
| `review.py`          | 검토/정확성 상태 관리 CLI → `review_status.json` (사람 소유, git 추적) |
| `.claude/skills/study` | `/study` — 모르는 걸 물으면 설명 + 문서/PPT 담기 선택 + 오류 시 교정 제안 |
| `.claude/skills/review-doc` | `/review-doc` — 문서 사실 오류를 LLM 정독으로 검증·최소 교정 |
| `.claude/skills/plan-drill` | `/plan-drill` — 실행계획 해석 문제 출제·채점(완성된 플랜 제시→말로 해석, Q1사실·Q2인과·Q3판단, 오독 진단·공식·비유·질문 포착함). 단계·약점은 `days/drill_log.md`. |
| `extract_slides.py`  | HTML 문서 → 슬라이드 스펙 JSON (추출) |
| `svg_snippets.py`    | 인라인 SVG 다이어그램 생성기(정의된 클래스만 → 검은박스 0) |
| `lint_authoring.py`  | 저작 품질 린터 — 개념(h3.blk)별 다이어그램·실측·서사 점수화 |
| `AUTHORING.md`       | **정답지 작법 규약**(P1~P7 체크리스트·헬퍼 API·문제/슬라이드 규약) |
| `layout.js`          | 레이아웃 엔진 — 좌표/페이지네이션 (렌더러·프리뷰 공유) |
| `build_ppt.js`       | 스펙 JSON → PPTX (pptxgenjs, 참고 디자인) |
| `preview.js`         | 스펙 → HTML(동일 좌표) → 슬라이드 PNG (Chromium QA) |
| `scripts/rezip.py`   | pptxgenjs 출력 재압축 |
| `notes_export.py`    | 발표 대본 추출 — 덱 스펙 → 슬라이드별 [제목+요지+발표노트] md/txt (무료 PPT에서 노트 안 보일 때) |
| `make.py`            | 파이프라인 엔트리 (위를 묶음) |
| `assets/`            | HTML 자산 (문서 4종 + `study_hub_full.html`) — **git 추적**(세션 간 지속) |
| `days/`              | 일차별 저작물(quiz·slides) — **git 추적**(세션 간 지속) |
| `ref/`               | 참고 디자인 PPTX (`reference.pptx`) + 언팩 — git 제외(대용량) |
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
MCQ/ESSAY 선택 필드 `ref`(URL) = 문제별 외부 레퍼런스 오버라이드. 없으면 허브 `DAY_REF`
(일차→문서 파트 앵커 + 검증된 매뉴얼 챕터)가 그날 주제 링크를 자동 제공. 새 URL은 실존 검증 후 등록.

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
  {type:"content", title(=주장 문장), notes(=발표자 노트), blocks:[
     {kind:"bullets", items:[]} | {kind:"table", headers:[], rows:[[]]} |
     {kind:"callout", tone:"why|tip", head, body} |
     {kind:"code", lines:[]} | {kind:"figure", caption, summary} |
     {kind:"svg", svg:"<svg 자체완결>", caption} |
     {kind:"analogy", text} | {kind:"steps", items:[{n,head,body}]} ]}
]}
```
**일차 덱 작법은 `docs/DECK_DESIGN.md`** (Assertion-Evidence·Mayer·시각설계): 저작 전 **원문의 빈도·중요도로 그날의 축을 먼저 잡고**(그 축이 발표 중심이 되게), 제목은 **주장 문장**,
본문은 **다이어그램(svg 블록, 자체완결 SVG→sharp 래스터)**, 상세 설명은 **notes(발표자 노트)**로.
3층 구조(큰 그림·핵심·빈틈&질문). `make_day`가 `lint_authoring.py`로 얇은 개념을 지적한다.
build 단계에서 title 뒤 **로드맵**, 맨 끝 **감사** 슬라이드가 자동 추가되고,
`[bullets + callout|figure]` 2개면 좌/우 2단 레이아웃, 넘치면 자동 페이지네이션.

## 참고 디자인 (ref/reference.pptx 에서 추출)

- 팔레트: ink `1E293B` · **Oracle Red `C74634`** · muted `64748B/94A3B8` · dark `0F172A` · card `F1F5F9` · line `E2E8F0`
- 폰트: 본문 **맑은 고딕**, 코드 **Consolas** (덱은 웜 페이퍼 · 모던 에디토리얼)
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

- 추출기·린터는 `<section class="part">` + `<h3 class="blk">` 구조(guide/sql/buffer)가 기본.
  `rman_recovery.html`(plain `<section>`+`<h2>`)은 **h2 폴백**으로 커버한다 —
  `extract_slides.py`·`lint_authoring.py`·`lint_vagueness.py` 모두 h3.blk이 없으면 h2를 개념 경계로 본다.
  단 h2 폴백은 개념 단위가 STEP 단위라 굵다. 세밀한 개념 분해가 필요하면 원문을 h3.blk 구조로 승격 권장.
- `sql_tuning.html`은 SVG에서 `.nal`(=`fill:var(--alert-t)`)을 **정의 없이 사용** → 검은박스 후보. 원문 수정 필요(검증기가 매번 지적).
