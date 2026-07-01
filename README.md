# 강의 → PPT 생성기 (Lecture → PPT)

수업 내용(텍스트/마크다운)을 붙여넣으면 **Claude가 내용을 정리·구조화**하고,
그 결과를 웹에서 미리 본 뒤 **PowerPoint(.pptx) 파일로 바로 내려받는** 시스템입니다.

## 동작 방식

```
강의 텍스트/MD ─▶ Claude (opus-4-8, 구조화 출력) ─▶ 슬라이드 JSON ─▶ 웹 미리보기
                                                       └─▶ python-pptx ─▶ .pptx 다운로드
```

1. **`/api/generate`** — 강의 텍스트를 Claude에 보내 `Deck`(제목/부제/슬라이드) JSON으로 구조화합니다.
   Anthropic 구조화 출력(`messages.parse` + `output_format`)으로 스키마에 맞는 검증된 결과를 받습니다.
2. **웹 미리보기** — 슬라이드별 제목·불릿·발표자 노트를 브라우저에서 확인합니다.
3. **`/api/pptx`** — (필요하면 수정한) 덱 JSON을 받아 `python-pptx`로 `.pptx`를 생성해 반환합니다.

슬라이드는 4가지 레이아웃을 지원합니다: `title`(표지), `section`(섹션 구분), `bullets`(불릿 본문),
`two_column`(2단 비교). 발표자 노트는 .pptx의 노트 영역에 그대로 들어갑니다.

## 구성

| 경로 | 역할 |
|------|------|
| `lecture_ppt/models.py`  | 슬라이드 덱 데이터 모델 (Pydantic) |
| `lecture_ppt/llm.py`     | Claude 호출 · 구조화 출력 |
| `lecture_ppt/builder.py` | `Deck` → `.pptx` (python-pptx) |
| `lecture_ppt/app.py`     | FastAPI 엔드포인트 + 정적 파일 |
| `lecture_ppt/static/index.html` | 단일 페이지 웹 UI |
| `scripts/selftest.py`    | LLM 없이 빌더만 검증하는 오프라인 테스트 |

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 인증: API 키를 환경변수로 지정 (또는 `ant auth login` 프로필 사용)
export ANTHROPIC_API_KEY=sk-ant-...

uvicorn lecture_ppt.app:app --reload
# 브라우저에서 http://127.0.0.1:8000 접속
```

## 오프라인 자가 테스트

API 키 없이 빌더가 정상 동작하는지 확인:

```bash
python scripts/selftest.py
# OK: 38,135 bytes -> examples/sample_output.pptx
```

## 사용 모델

`claude-opus-4-8` — 긴 강의 내용을 요약·구조화하는 데 강점이 있습니다.
`lecture_ppt/llm.py`의 `MODEL` 상수에서 변경할 수 있습니다.

## 향후 확장 아이디어

- PDF/DOCX 파일 업로드 입력 (현재는 텍스트/마크다운 붙여넣기)
- 테마/색상 커스터마이징, 회사 템플릿(.potx) 적용
- 슬라이드별 재생성, 이미지·다이어그램 자동 삽입
- 웹 미리보기에서 슬라이드 직접 편집 후 다운로드
