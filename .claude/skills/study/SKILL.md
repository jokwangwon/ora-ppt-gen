---
name: study
description: 공부하다 모르는 부분을 물으면 설명하고, 그 내용을 문서/PPT에 담을지 선택지를 준다. 기존 문서 내용이 틀렸으면 교정도 제안. Oracle DBA 학습 허브(assets/) 기반.
---

# /study — 공부 Q&A → 문서/PPT 담기

사용자가 학습 중 모르는 부분을 물으면 **설명**하고, 그 내용을 **문서(assets/)나 PPT에
담을지 선택**하게 한다. 원본 문서는 수업 중 직접 작성돼 **사실 오류가 있을 수 있으므로**,
이미 문서에 있는 내용을 다룰 땐 **정확성을 교차 확인**하고 틀렸으면 교정을 제안한다.

## 대원칙 (프로젝트 규약 상속)
- **원문 사실만, 지어내지 말 것.** 근거 없는 수치·이름은 만들지 않는다. 불확실하면 '확인 필요'.
- **즉시 이해가 목표.** 난이도에 맞춰 설명(쉬운 건 짧게, 어려운 건 도해·단계). `AUTHORING.md` 도구상자 참고.
- **HTML/허브 동작을 깨지 말 것.** 담은 뒤 반드시 `sync_and_verify` 검증.

## 흐름

### 1) 설명
- 질문 주제를 파악하고 **관련 문서를 먼저 읽는다**: `sql_tuning`(실행계획·인덱스·CF) /
  `buffer_cache_dbwr_checkpoint`(DBWR·checkpoint·redo) / `rman_recovery`(백업·복구) /
  `guide_62_68`(SGA·latch·ITL 등 내부구조).
- 설명 시 근거를 구분한다:
  - **문서 근거** — 해당 문서/노트에 있는 내용.
  - **노트 밖 일반 지식** — 문서엔 없지만 정확한 Oracle 지식. (담을 때 배지로 표시, 아래 3-c)
- **정확성 교차 확인**: 질문이 이미 문서에 있는 개념이면, 문서 서술이 사실과 맞는지 점검한다.
  틀렸거나 오해 소지가 있으면 **"문서의 이 서술이 부정확합니다 → 이렇게 교정"** 을 먼저 제시한다.

### 2) 선택지 (AskUserQuestion)
설명 끝에 묻는다. **기본(권장)은 '설명만'** — 실수로 반영하지 않게.
```
[설명만 보기 (권장)] [문서에 담기] [PPT에 담기] [문서+PPT 담기]
```
문서 정확성 문제를 발견했다면 별도로:
```
[문서 교정하기] [교정 보류]
```

### 3) 담기 / 교정 실행
- **a. 문서에 담기**: 알맞은 `assets/<topic>.html` 의 맞는 `<section class="part">` 안에
  `<h3 class="blk"><span class="ix">N.N</span>개념</h3>` 로 개념을 추가(AUTHORING.md 난이도 매칭).
  SVG가 필요하면 `svg_snippets.py` 로 생성(정의된 클래스만 → 검은박스 0).
- **b. 교정**: 틀린 서술을 **원문 사실 범위에서** 고친다. 뭘 왜 고쳤는지 한 줄 남긴다.
- **c. 노트 밖 일반 지식 배지**: 담을 때 본문에 구분 배지를 붙인다.
  ```html
  <span class="ext">노트 밖</span>
  ```
  대상 문서 `<style>` 에 `.ext` 가 없으면 함께 정의(예: `.ext{font-size:.72em;color:#64748b;border:1px solid #cbd5e1;border-radius:6px;padding:1px 6px;margin-left:6px}`).
  담기 전 사용자에게 **"이건 노트 밖 일반 지식입니다 — 담을까요?"** 한 번 더 확인.
- **d. PPT에 담기**: 문서 덱을 재생성하거나 `days/<N>/<N>.slides.json` 에 슬라이드 추가 후 빌드.

### 4) 배선 (담기/교정 후 항상)
```bash
python sync_and_verify.py --dir assets        # 재주입·검증 (실패 시 멈추고 원인 보고)
python lint_authoring.py assets/<topic>.html  # 난이도 대비 설명
python lint_vagueness.py assets/<topic>.html  # 얼버무림
python review.py accuracy <topic>.html --issues <n> --method "study 교정"   # 교정했으면
python build_dashboard.py                     # 대시보드 갱신
```
- 새로 담은 개념/문서는 검토 대상이므로 상태를 **미검토**로 두거나 `reviewing` 으로:
  `python review.py mark <topic>.html --status reviewing --note "study로 개념 추가"`.
- 산출물(PPTX)이 필요하면 세션에서 빌드해 제공. 끝에 **커밋/푸시**로 지속.

## 하지 말 것
- 노트에 없는 수치를 지어내 담기. (일반 지식이면 배지 + 확인, 확신 없으면 '확인 필요')
- 검증 실패한 채로 산출물 내기.
- 쉬운 개념을 억지로 도해·단계로 부풀리기(즉시 이해를 방해).
