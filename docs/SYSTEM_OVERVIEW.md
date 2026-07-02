# 시스템 개요 (AI 핸드오프 문서)

> 이 문서 하나로 다른 AI/사람이 이 저장소의 목적·구조·워크플로·규칙을 이해하고 바로 운영할 수 있게 정리한다.
> 저장소: `jokwangwon/ora-ppt-gen` · 기본 브랜치 `main` · 공개 자료실은 GitHub Pages(루트).

---

## 1. 한 줄 요약

**Oracle DBA 부트캠프 학습 파이프라인.** 수업마다 손으로 쓴 **HTML 학습 문서(=소스 오브 트루스)** 에서
발표용 **PPTX 덱**, 문제 풀이 **허브**, 관리 **대시보드**, 공개 **자료실**을 반자동으로 만든다.
**핵심 불변식: PPT·문제·요약은 문서에서 파생하되 "새 사실을 지어내지 않는다"(원문만 구조화).**

## 2. 철학·원칙 (가장 중요)

1. **저작은 대화, 배선은 스크립트.** 내용(문서 섹션·문제·덱 스펙)은 사람이 Claude와 **대화로 저작**한다.
   스크립트는 검증·주입·렌더·배포 같은 **결정적 배선**만 한다.
2. **원문만.** 노트/문서에 없는 사실은 넣지 않는다. 표준 지식이라도 노트 밖이면 **"확인 권장"** 으로 표시.
3. **소스 오브 트루스 = `assets/*.html` 문서.** 덱·문제·요약은 여기서 파생.
4. **검증 실패 시 산출물 내지 말고 원인 보고.** (`--force`로만 강제)
5. **축 잡기.** 덱은 원문의 빈도·중요도로 **그날의 축(중심 주제)** 을 먼저 잡고 그 축이 발표의 중심이 되게 설계.

## 3. 전체 데이터 흐름

```
[수업] ──▶ 자습 1시간(복습 노트 days/N/review.md)
             │  (대화 저작: 원문만 구조화)
             ▼
   assets/<topic>.html  ── 그날 섹션 추가 (소스 오브 트루스)
   days/N/quiz.json     ── 문제 (MCQ/ESSAY/TERMS/PLANQ)
   days/N/N.slides.json ── 일차 덱 스펙 (선택)
             │
             ▼  python make_day.py N --doc <topic>.html  (결정적 배선)
   ┌─────────────────────────────────────────────────────────┐
   │ 1) sync_and_verify : 문서→허브 docsrc 재주입 + 검증        │
   │ 2) inject_quiz     : 문제·DAYS·날짜칩 허브 주입(멱등)       │
   │ 3) 일차 덱         : slides.json → out/dayN.pptx + 노트    │
   │ 4) 문서 전체 덱    : <doc> → 추출 → out/<doc>.pptx        │
   │ 5) build_dashboard : assets/dashboard.html               │
   │ 6) build_library   : out/덱→files/ 복사 + index.html      │
   └─────────────────────────────────────────────────────────┘
             ▼
   공개(GitHub Pages 루트): index.html(자료실) · assets/*.html · files/*.pptx
```

## 4. 구성 요소 (파일별 역할)

### 배선 스크립트 (파이프라인)
| 파일 | 역할 |
|------|------|
| `new_day.py` | 하루 스캐폴드 — `days/<N>/`에 `review.md`(복습노트)·`quiz.json` 뼈대 생성(멱등) |
| `make_day.py` | **일차 파이프라인** — 아래를 순서대로: 동기화·검증→문제주입→일차덱+문서덱+노트→대시보드→자료실 |
| `make.py` | 문서 단위 파이프라인 엔트리(문서 하나/전체 → PPT) |
| `sync_and_verify.py` | 한글→ASCII 동기화 · 문서를 허브 `docsrc-*` 블록에 재주입 · 검증(태그/JS/SVG클래스). **실패 시 중단** |
| `inject_quiz.py` | `quiz.json`을 허브 JS 배열(MCQ/ESSAY/TERMS/PLANQ)·`DAYS`·날짜칩(색변수·배지·필터칩)에 멱등 주입 |
| `extract_slides.py` | HTML 문서 → 슬라이드 스펙 JSON (충실 추출, 재작성 X) |
| `build_ppt.js` | 스펙 JSON → PPTX (pptxgenjs). title 뒤 로드맵·끝 감사 슬라이드 자동, 넘치면 페이지네이션 |
| `layout.js` | 레이아웃 엔진(좌표·페이지네이션) — 렌더러·프리뷰 공유 |
| `preview.js` | 스펙 → 동일좌표 HTML → Chromium 스크린샷 QA (`out/qa/*.png`, `out/preview.html`) |
| `notes_export.py` | 덱 스펙 → 슬라이드별 [제목+요지+발표노트] md/txt (무료 PPT에서 노트 안 보일 때) |
| `svg_snippets.py` | 인라인 SVG 다이어그램 생성기(정의된 클래스만 → 검은박스 0) |
| `scripts/rezip.py` | pptxgenjs 출력 재압축 |

### 품질·관리
| 파일 | 역할 |
|------|------|
| `lint_authoring.py` | 저작 품질 린트 — 개념(h3.blk)별 난이도 대비 설명·다이어그램 점수화 |
| `lint_vagueness.py` | 얼버무림(막연한 일반화) 검사 |
| `lint_report.py` | 린트 리포트 집계 |
| `review.py` | 검토/정확성 상태 CLI → `review_status.json`(사람 소유, git 추적) |
| `build_dashboard.py` | 관리 대시보드 → `assets/dashboard.html`(검토·정확성·난이도·린트 한눈에) |
| `build_library.py` | **자료실** → 루트 `index.html`(Chirpy 룩) + `out/` 덱을 `files/`로 복사(멱등) |

### 산출·자산 (git 추적 — 세션 간 지속)
| 경로 | 내용 |
|------|------|
| `assets/*.html` | 학습 문서 4종 + `study_hub_full.html`(문제 허브) + `dashboard.html`(생성물) |
| `days/<N>/` | 일차별 `review.md`·`quiz.json`·`N.slides.json` |
| `days/TEMPLATE.md` | 복습 노트 양식 원본 |
| `files/*.pptx` | 자료실 공개용 덱(커밋됨) |
| `index.html` | 자료실 랜딩(생성물, 커밋됨) |
| `review_status.json` | 문서/일차 검토·정확성 상태 |

### 문서·스킬
| 경로 | 내용 |
|------|------|
| `CLAUDE.md` | 작업 규칙 요약(다음 세션용) — **먼저 읽을 것** |
| `AUTHORING.md` | 정답지 작법 규약(P1~P7·헬퍼 API·문제/슬라이드 규약) |
| `docs/DECK_DESIGN.md` | 덱 설계 원칙(축 잡기·Assertion-Evidence·Mayer·시각설계·문체) |
| `docs/STUDY_ROUTINE.md` | 자습 1시간 루틴 + 양식 + 양식→파이프라인 지도 |
| `docs/SYSTEM_OVERVIEW.md` | (이 문서) |
| `.claude/skills/study` | `/study` — 모르는 걸 물으면 설명 + 문서/PPT 담기 + 오류 교정 제안 |
| `.claude/skills/review-doc` | `/review-doc` — 문서 사실 오류를 LLM 정독으로 검증·최소 교정 |

### git 제외
`out/`(산출물)·`*.pptx`(단, `files/*.pptx`는 예외로 커밋)·`ref/`(참고 디자인)·`node_modules/`.

## 5. 데이터 계약

### `days/<N>/quiz.json` (허브 배열과 동일 필드)
```json
{ "MCQ":  [{"id":"m73a","d":73,"q":"...","o":["...","..."],"a":1,"e":"해설"}],
  "ESSAY":[{"id":"e73a","d":73,"q":"...","a":"모범답안","k":["채점 키워드"]}],
  "TERMS":[{"t":"용어","e":"짧은 뜻","d":"자세히"}],
  "PLANQ":[{"id":"pl73a","q":"...","plan":"| Id | ... |","a":"..."}] }
```
- `a`(MCQ)=정답 인덱스(0-base). `id`(또는 TERMS의 `t`)로 멱등 — 재실행해도 중복 안 됨.

### 슬라이드 스펙 JSON (extract ↔ build 계약)
```
{ deck_id, title, subtitle, source, slides:[
  {type:"title"} | {type:"section", num, title, subtitle} |
  {type:"content", title(=주장 문장), notes(=발표자 노트), blocks:[
     {kind:"bullets", items:[]} | {kind:"table", headers:[], rows:[[]]} |
     {kind:"callout", tone:"why|tip", head, body} |
     {kind:"code", lines:[]} | {kind:"figure", caption, summary} |
     {kind:"svg", svg:"<svg 자체완결>", caption} |
     {kind:"analogy", text} | {kind:"steps", items:[{n,head,body}]} | {kind:"plan", ...} ]}
]}
```
- content `title` = **주장 문장**(주제어 X). 상세 설명은 `notes`(발표자 노트)로. 시각자료는 자체완결 SVG.

### `review_status.json`
`docs[name]={status: reviewed|reviewing|unreviewed, accuracy:{checked,issues,method}}`,
`days[N]={status, note}`. **사람이 소유**(review.py로만 변경), build_dashboard/library가 읽어 표시.

## 6. 매일 워크플로

```bash
python new_day.py 73 --topic rman_recovery.html   # 준비: days/73/ 생성
#   ↓ days/73/review.md 를 양식대로 채운다            (자습 1시간, docs/STUDY_ROUTINE.md)
#   ↓ 대화(Claude)로 저작 — review.md 근거, 원문만:
#       - assets/rman_recovery.html 에 그날 섹션 추가
#       - days/73/quiz.json 채우기
#       - days/73/73.slides.json (일차 덱, 선택)
python make_day.py 73 --doc rman_recovery.html      # 배선(검증·주입·덱·노트·대시보드·자료실)
python make_day.py 73 --doc rman_recovery.html --preview   # + QA 스크린샷
python make_day.py 73 --doc rman_recovery.html --force     # 검증 실패해도 진행
```
자습 루틴(1시간): 0-10 개념제목 · 10-30 실습명령어 · 30-45 에러/흐름/왜 · 45-60 5줄요약 + **매뉴얼 대비 건너뛴 것**.

**건너뛴 것 추적**: 그날 주제의 컨셉 메뉴얼 챕터에서 수업이 안 다룬 소주제를 `[건너뛴 것]`에 남긴다.
"왜"는 추정이므로 분류(①뒤차시 ②비중낮음 ③구버전 ④내부심화 ⑤환경제약 ?모름)로 표시 — 지어내지 않음.
`?`→강사 질문, ①→뒤 차시에서 회수 확인. 덱의 **빈틈 & 궁금한 점** 슬라이드와 문서 '확인 권장' tip의 재료가 된다.

## 7. 산출물·공개

- **학습 허브** `assets/study_hub_full.html` — 객관식·서술형·실행계획·**용어 검색**·오답노트. 자체완결(오프라인 OK).
- **학습 문서 4종** `assets/*.html` — 소스 오브 트루스. 브라우저에서 바로 열림.
- **발표 덱** `files/*.pptx` — 자료실에서 다운로드. (발표 대본 `.md`는 개인용이라 자료실 제외)
- **관리 대시보드** `assets/dashboard.html` — 내부용.
- **자료실** `index.html`(루트) — Chirpy 룩(사이드바·라이트/다크 토글). 검토된 최신 덱만 노출, 미검토 덱은 접힘.
  각 페이지 우하단 "← 자료실" 버튼, 링크는 같은 탭(뒤로가기 복귀).
- **공개**: GitHub Pages(Settings→Pages→`main`/`root`) → `https://jokwangwon.github.io/ora-ppt-gen/`.
  루트에 `.nojekyll`(Jekyll 끄고 정적 서빙 — 문서 HTML의 `{{ }}`가 안 깨지게).

## 8. 반드시 지킬 규칙 (함정)

1. **재주입 이스케이프**: docsrc 주입 시 `</script` → `<\/script`. `sync_and_verify.py`가 처리.
2. **SVG 검은박스**: SVG의 `class="nXXX"`가 문서 `<style>`에 정의 안 되면 검은 박스. 자체완결 SVG는 인라인 스타일/정의된 클래스만.
3. **JS 검증 범위**: 메인 `<script>`만 `node --check`. `<script type="text/plain">`(docsrc)은 제거 후 검사.
4. **한글↔ASCII**: 원본 한글 파일명, 배포/주입용 ASCII 사본. 매핑은 `sync_and_verify.py`.
5. **HTML 문서/허브 동작 깨지 말 것.** 검증 실패하면 원인 보고.
6. **새 사실 지어내지 말 것.** 원문만 구조화.
7. **날짜칩 3종 세트**: 새 일차는 `--dNN` 색변수 + `.dtNN` 배지 + `.chip.dNN.on` 필터칩이 **모두** 있어야 함(하나라도 빠지면 흰 배경 흰 글자로 안 보임). inject_quiz가 3개를 각각 멱등 주입.

## 9. 환경 특이사항

- **LibreOffice(soffice) 변환이 이 환경에서 멈춤** → pptx→pdf/이미지 불가. 대신 `preview.js`가 동일 좌표 HTML→Chromium 스크린샷으로 시각 QA.
- 의존성: `pip install beautifulsoup4 lxml Pillow` · `npm i`(pptxgenjs·playwright-core·react-icons·sharp).
- 추출기·린터는 `section.part`+`h3.blk` 구조 기준. plain `<h2>` 문서는 h2 폴백(개념 단위가 굵어짐).

## 10. 빠른 명령어 레퍼런스

```bash
python new_day.py N --topic <doc>.html      # 하루 폴더 스캐폴드
python make_day.py N --doc <doc>.html        # 일차 파이프라인 전체
python make.py assets/<doc>.html             # 문서 하나 → PPT
python make.py --all                         # 문서 4개 전부
python sync_and_verify.py --dir assets       # 동기화·재주입·검증만
python inject_quiz.py days/N/quiz.json --day N --dry-run   # 문제 주입 미리보기
python build_dashboard.py                    # 대시보드 재생성
python build_library.py                      # 자료실 재생성(덱→files/ 복사)
python review.py mark <doc> --status reviewed # 검토 상태 변경
node preview.js days/N/N.slides.json          # 덱 시각 QA
```

---

**이 문서를 다른 AI에게 줄 때**: 위 2(철학)·8(함정)·6(워크플로)를 특히 강조. 핵심은 **"원문만, 저작은 대화·배선은 스크립트, 검증 실패 시 멈춤"**.
