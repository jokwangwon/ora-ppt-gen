# 73일차 비교 시트 (Claude 버전)

> ⚠ **자습이 끝나기 전엔 열지 마세요.** 내 review.md를 다 쓴 뒤, 항목별로 대조해 ○(일치)·△(부분)·×(놓침)를 매기는 용도.
> Claude가 수업 노트만 보고 독립적으로 작성한 버전입니다 — 정답지가 아니라 **대조 상대**입니다.

---

## [오늘의 축] — Claude 버전

> **NL 조인 — 바깥(driving) 선택과 진입 인덱스가 Buffers를 결정한다. 판정은 Starts·Buffers.**

판단 근거: 모든 실험이 "순서를 바꾸고(leading) 인덱스를 만들며 Buffers를 비교"하는 구조. 강사도 NL 집중을 명시.

## [개념 제목] — Claude 버전 (수업 등장 순)

1. **batch i/o** (nlj_batching) — inner 테이블 접근을 일괄 처리 · [문서 §7.8](assets/sql_tuning.html#join)
2. **table prefetch** (nlj_prefetch) — 곧 읽을 블록을 미리 캐시 적재 · [문서 §7.8](assets/sql_tuning.html#join)
3. **optimizer_features_enable** — 옵티마이저 버전 고정 · [문서 §7.8](assets/sql_tuning.html#join)
4. NL 플랜의 **세 가지 모양** (classic / prefetch / BATCHED) · [문서 §7.8](assets/sql_tuning.html#join)
5. **인덱스가 조인 방법을 바꾼다** — CTAS 재생성 + PK 점진 생성 실험 · [문서 §7.4](assets/sql_tuning.html#join)
6. **MERGE JOIN CARTESIAN** — 인덱스 없을 때 옵티마이저의 선택 · [문서 §7.4](assets/sql_tuning.html#join)
7. **조인 순서(leading)** — Seattle 실험 (227 → 72) · [문서 §7.5](assets/sql_tuning.html#join)
8. **진입 인덱스** — 풀 스캔 제거 (혼자 해보기, 72 → 18) · [문서 §7.5](assets/sql_tuning.html#join)
9. **양끝 필터** — job_id 추가, NL 변환 (hash 8 vs NL 12) · [문서 §7.6](assets/sql_tuning.html#join)
10. **driving 잘못 선택의 비용** — 126 vs 35 · full 강제 232 vs 95 · [문서 §7.7](assets/sql_tuning.html#join)

> 플랜 읽기가 막히면 → [§2.6 혼자 읽는 5단계 루틴](assets/sql_tuning.html#plan)

## [실습 명령어 정리] — Claude 버전 (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | `select ... /*+ gather_plan_statistics */` + `dbms_xplan.display_cursor(null,null,'allstats last')` | 모든 실험의 실측 도구 — Starts·A-Rows·Buffers |
| 2 | `optimizer_features_enable('10.2.0.5' / '10.1.0')` + `no_nlj_prefetch` | 같은 NL이 batched → prefetch → classic 모양으로 바뀜 |
| 3 | `drop table purge` + `create table ... as select`(CTAS) | 인덱스 0개인 emp·dept·loc 재생성 (실험 초기화) |
| 4 | `create unique index` + `alter table add constraint ... primary key using index` ×3 (emp→dept→loc) | 플랜이 CARTESIAN+HASH → NL 부분 → **NL 3단 전부 unique scan**으로 진화 (8→7→7→6) |
| 5 | `dba_constraints`/`dba_cons_columns` · `dba_indexes`/`dba_ind_columns` 조회 | 만든 제약·인덱스 상태 확인 (blevel·leaf_blocks·clustering_factor) |
| 6 | Seattle 쿼리 + `leading(e,d,l)` vs `leading(l,d,e)` | 순서 반대면 Starts 107 → **227**, 방향 맞추면 **72** |
| 7 | `create index` — loc(city)·dept(location_id)·emp(department_id) | filter 3줄 → **access** 전환, 72 → **18** (옵티마이저 기본 9) |
| 8 | job_id='AD_VP' 추가 + `emp_job_idx` + `leading(e,d,l) use_nl(d) use_nl(l)` | 바깥 2행 all-NL **12** vs 옵티마이저 hash **8** |
| 9 | 필터 없는 emp⋈dept, `leading(e,d)` vs `leading(d,e)` (+`no_nlj_prefetch`) | Starts 107 vs 27 → **126 vs 35** |
| 10 | 같은 실험 + `full(e) full(d)` | 안쪽까지 full → **232 vs 95** (Starts×full = 최악) |

## [5줄 요약] — Claude 버전

1. NL 비용 ≈ **바깥 1회 + (바깥 행 수 × 안쪽 1회)** — 바깥(명단)을 최소로: 필터 센 쪽, 없으면 작은 쪽.
2. **인덱스가 없으면 힌트를 줘도** 옵티마이저는 hash·cartesian으로 짠다 — 도구가 선택지를 만든다 (오타 힌트는 조용히 무시).
3. **진입 인덱스**(필터 컬럼·조인키)가 filter를 access로 바꾼다 — Seattle 72→18.
4. 그래도 **작은 테이블은 full+hash가 이길 수 있다** (9 vs 18, 8 vs 12) — 판정은 항상 Buffers 총점.
5. NL 플랜은 버전 최적화로 **모양이 3가지**(classic·prefetch·batch i/o) — 모양이 나와도 항상 작동한다는 뜻은 아니다.

## [건너뛴 것 — 매뉴얼 대비] — Claude 버전

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| Sort Merge·Hash Join 내부 단계 | ① 뒤 차시 | 다음 수업 대기 · [매뉴얼(Concepts)](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/) |
| outer join의 NL 처리 | ①/② | [매뉴얼(Concepts)](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/) |
| prefetch 실제 작동 확인 방법 | ? → 강사 질문 | 질문 후 [문서 §7.8](assets/sql_tuning.html#join)에 답 기록 |

---

## 대조하는 법 (자습 후 2분)

1. 내 review.md와 위 항목을 나란히 놓고 **○(일치)·△(부분)·×(놓침)** 표시
2. **×가 나온 항목 = 오늘의 복습 우선순위** — 위 개념 옆 **[문서 §] 링크로 바로 이동**해 그 부분만 다시 읽기
3. 결과를 review.md 맨 아래 `[대조 결과]`에 한 줄로 (예: "축 ○ · 개념 8/10 · 명령어 △ — cartesian 놓침")
4. 마무리 — [허브에서 73일차 문제 풀기](assets/study_hub_full.html) (날짜칩 73 필터)
