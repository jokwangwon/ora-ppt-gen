# ora-ppt-gen — 수업자료 HTML → 발표 PPTX 자동 생성

Oracle DBA 부트캠프 학습 문서(HTML)를 **소스 오브 트루스**로 삼아,
발표용 **PPTX** 를 자동 생성하고 학습 허브의 동기화·검증을 자동화하는 파이프라인.

디자인은 첨부한 참고 템플릿(**Slate + Oracle Red**, 맑은 고딕)을 따른다.

## 빠른 시작

```bash
# 1) 의존성
pip install -r requirements.txt
npm install

# 2) HTML 자산을 assets/ 에 둔다 (문서 4종 + study_hub_full.html)

# 3) 실행
python make.py assets/sql_tuning.html            # 한 문서 → out/sql_tuning.pptx
python make.py --all                             # 4개 문서 전부
python make.py assets/sql_tuning.html --preview  # + QA 스크린샷 out/qa/*.png
```

생성물은 `out/` 에 쌓인다: `*.slides.json`(스펙), `*.pptx`(덱), `qa/*.png`(QA 이미지).

## 파이프라인

```
HTML 문서 ─▶ sync_and_verify.py ─▶ extract_slides.py ─▶ build_ppt.js ─▶ rezip ─▶ .pptx
 (소스)       동기화·재주입·검증      슬라이드 스펙 JSON     pptxgenjs 렌더           └▶ preview.js ─▶ QA 이미지
```

- **sync_and_verify.py** — 한글→ASCII 사본 복사, 4개 문서를 `study_hub_full.html`의
  `docsrc-*` 블록에 재주입(`</script` 이스케이프), 검증(태그 균형 · 메인 스크립트 JS
  문법 · 미정의 SVG 클래스=검은박스 탐지). **검증 실패 시 허브를 쓰지 않고 멈춘다.**
- **extract_slides.py** — 섹션/개념/표/박스/코드/다이어그램을 스펙 JSON으로 추출.
  원문을 재작성하지 않는다(새 사실 지어내기 금지). 추출이 부정확하면 JSON만 손보면 된다.
- **build_ppt.js** — 스펙 → PPTX. 타이틀·로드맵·섹션·콘텐츠·코드·비교·감사 슬라이드,
  넘치면 자동 페이지네이션. 좌표는 `layout.js`가 계획(프리뷰 QA와 동일 기하).
- **preview.js** — 동일 좌표로 HTML을 만들어 Chromium으로 슬라이드별 PNG를 찍는다.

## 주요 명령

| 명령 | 설명 |
|------|------|
| `python make_day.py <N> --doc <topic.html>` | **일차 파이프라인**(문제 주입 + 일차 덱 + 문서 덱). 저작은 대화로 `days/<N>/`·문서에 미리 준비 |
| `python inject_quiz.py days/<N>/quiz.json --day <N>` | 하루치 문제를 허브에 주입(멱등) |
| `python make.py <doc.html>` | 한 문서 파이프라인 |
| `python make.py --all` | assets/의 4개 문서 전부 |
| `python make.py <doc> --preview` | QA 스크린샷까지 |
| `python make.py <doc> --force` | HTML 검증 실패해도 PPT 생성 |
| `python sync_and_verify.py --dir assets` | 동기화·재주입·검증만 |
| `python extract_slides.py <doc> -o out/x.json` | 추출만 |
| `node build_ppt.js out/x.json -o out/x.pptx` | 렌더만 |

## 환경 메모

- 이 저장소는 파이프라인 **스크립트**를 담는다. HTML 자산(`assets/`)·참고 PPTX(`ref/`)·
  산출물(`out/`)은 `.gitignore` 대상(사용자 콘텐츠).
- 참고: 일부 샌드박스에서 LibreOffice 변환이 동작하지 않아, QA는 `preview.js`(Chromium)로
  한다. 최종 미세 검수는 PowerPoint/로컬 LibreOffice 권장.

자세한 규칙·함정·데이터 계약은 [CLAUDE.md](CLAUDE.md) 참고.
