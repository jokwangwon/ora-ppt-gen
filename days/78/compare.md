# 78일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **E-Rows는 산수다 — selectivity(1/값 종류) × 총 행수. 균등 가정이 빗나가는 곳에 히스토그램(method_opt)을 만들고, 통계는 자동 수집(stale 10%)로 신선하게, 이력·export·restore로 시간 여행까지 — 통계의 수명주기 전체를 관리한다.**

옵티마이저 3단 파이프라인(Transformer→Estimator→Plan Generator)으로 E-Rows의 정체를 풀고, 통계의 생성·감시·잠금·백업·복원을 한 바퀴 돈 날.

## [개념 제목] (수업 등장 순)

1. **옵티마이저 3단 파이프라인** — Query Transformer(=Part 08) → Estimator(비용 계산) → Plan Generator(후보 생성) + Row Source Generator · [문서 §9.4](assets/sql_tuning.html#opt)
2. **selectivity / cardinality / cost** — 1/num_distinct · 총행수×selectivity(**=E-Rows**) · 표준화된 I/O 예측 · [문서 §9.4](assets/sql_tuning.html#opt)
3. **dynamic sampling** — 통계가 없으면 파싱 시점 즉석 샘플링, 플랜 Note에 표시(level=2) · [문서 §9.5](assets/sql_tuning.html#opt)
4. **균등 가정의 한계** — size 1 수집 시 부서 10번(1명)도 50번(45명)도 E-Rows 10 · [문서 §9.5](assets/sql_tuning.html#opt)
5. **히스토그램 유형** — Frequency(값 수=버킷 수) / height balanced(값 수>버킷 수), 버킷 최대 2048(11g 254) · [문서 §9.6](assets/sql_tuning.html#opt)
6. **method_opt** — size 1(안 만듦)/컬럼 지정/254 전체(주의!)/repeat/auto(col_usage$)/skewonly · [문서 §9.6](assets/sql_tuning.html#opt)
7. **no_invalidate** — 수집 후 LCO 무효화 제어, 기본 auto_invalidate(18000초에 걸쳐 조금씩) · [문서 §9.7](assets/sql_tuning.html#opt)
8. **cascade / degree** — 인덱스 통계 동시 수집 / 병렬 수집 · [문서 §9.7](assets/sql_tuning.html#opt)
9. **자동 통계 수집(10g)** — autotask + 유지보수 윈도우(평일 22시 4h·주말 6시 20h), 대상=무통계+10% 변화 · [문서 §9.8](assets/sql_tuning.html#opt)
10. **stale 추적** — dba_tab_modifications(DML 카운터) · stale_stats YES/NO · stale_percent 변경 · [문서 §9.8](assets/sql_tuning.html#opt)
11. **lock_table_stats / statistics_level** — 수집 잠금(ALL) / typical(기본)·basic·all · [문서 §9.8](assets/sql_tuning.html#opt)
12. **통계 시간 여행** — export(stattab)·diff 리포트·import·restore(시점 복원 — **수업 실측에선 히스토그램 제외**, 재확인 권장)·31일 이력·purge·set_table_stats · [문서 §9.9](assets/sql_tuning.html#opt)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | `v$version` · `optimizer_features_enable` · `v$sys_optimizer_env` | 옵티마이저 영향 요소를 눈으로 확인 |
| 2 | dba_tables⋈dba_tab_columns로 selectivity·cardinality 계산 | JOB_ID: 19종 → sel .0526 · card **5.63** / DEPARTMENT_ID: 11종 → card **9.73** |
| 3 | `delete_table_stats` 후 조회 | 플랜 Note **dynamic sampling (level=2)** — 즉석 샘플링 |
| 4 | `gather_table_stats(... 'for all columns size 1')` | 히스토그램 없이 수집 — IT_PROG E-Rows **6**(107/19), full scan |
| 5 | `department_id=10` 조회 (히스토그램 없음) | E-Rows **10**(107/11) vs 실제 **1** — 균등 가정의 빗나감 |
| 6 | job_id/department_id 분포 group by | IT_PROG 5 · SA_REP 30 / 10번 1명 · 50번 45명 — 치우친 분포 확인 |
| 7 | `'for columns size 20 job_id'` + flush shared_pool | JOB_ID FREQUENCY — IT_PROG **E-Rows 5 정확**, EMP_JOB_IDX 인덱스 |
| 8 | `job_id='SA_REP'` 조회 | A-Rows 30인데 **E-Rows 10** — 노트에 설명 없음, 홈랩 재확인 |
| 9 | `'for columns size 20 job_id,department_id'` | 둘 다 FREQUENCY — dept=10 **E-Rows 1 정확** (50번은 여전히 10, 홈랩 재확인) |
| 10 | `'for all columns size auto'` | col_usage$ 기반 — JOB_ID·DEPARTMENT_ID에만 FREQUENCY 자동 생성 |
| 11 | `no_invalidate=>true` + `_optimizer_invalidation_period` | LCO 무효화 제어 — 기본 auto_invalidate, **18000초** |
| 12 | `cascade=>true` / `gather_index_stats` | 인덱스 통계 동시/단독 수집 |
| 13 | `dba_autotask_client` | **auto optimizer stats collection ENABLED** (윈도우 그룹 ORA$AT_WGRP_OS) |
| 14 | `dba_scheduler_windows` | 평일 22시 **4시간** · 주말 6시 **20시간** — SET_ATTRIBUTE로 시각·duration 변경 |
| 15 | `dbms_auto_task_admin.disable(...)` | 자동 수집 DISABLED · `statistics_level=typical` 확인(basic이면 장치들 눈멂) |
| 16 | insert 2·update 15·delete 5 → `dba_tab_modifications` | DML 카운터 누적 — 10% 초과 시 `stale_stats=YES`, 재수집하면 리셋+NO |
| 17 | `set_table_prefs('stale_percent','40')` | 테이블별 stale 임계치 변경 (dba_tab_stat_prefs) |
| 18 | `lock_table_stats` | stattype_locked=**ALL** — 통계 수집 차단 |
| 19 | `create_stat_table` → `export_table_stats` | 통계를 tab_stat 테이블에 백업 |
| 20 | 1000행 추가 후 `diff_table_stats_in_stattab` | 비교 리포트 — ROWS 100 vs **1100**, COL1 NDV 100 vs 101, HIST NO vs YES |
| 21 | `import_table_stats` / `restore_table_stats('시각')` | 백업/이력 시점으로 복원 — **수업 실측에선 히스토그램이 restore 안 됨**(FREQUENCY→NONE · 문서상 제약 목록엔 없어 재확인 권장) |
| 22 | `get_stats_history_retention`(31) → `alter_...(7)` → `purge_stats` | 이력 보유 기간 변경·시점 기준 삭제 · `set_table_stats`로 수동 지정 |
| 23 | (곁가지) time_zone·timestamp·interval 실습 | current_date/timestamp 계열과 to_yminterval/to_dsinterval — SQL 문법 복습 |

## [5줄 요약]

1. **E-Rows = 총 행수 × (1/값 종류 수)** — 옵티마이저 3단 파이프라인의 Estimator가 하는 산수. 73일차부터 본 E-Rows의 정체가 풀렸다.
2. **히스토그램은 균등 가정의 해독제** — 없으면 부서 10번(1명)도 50번(45명)도 E-Rows 10. size 20 job_id처럼 치우친 컬럼에만 골라 만든다(254 전체는 주의).
3. **통계가 없으면 dynamic sampling** — 플랜 Note가 통계 건강 상태 표시등. 운영에서 이 Note는 "통계 수집이 필요하다"는 신호.
4. **자동 수집은 밤에 stale을 찾는다** — 평일 22시/주말 6시 윈도우, 대상은 무통계 + 10% 변화(dba_tab_modifications가 증거). 임계치는 stale_percent, 막으려면 lock_table_stats.
5. **통계는 시간 여행이 된다** — 31일 이력에서 restore, export로 백업, diff로 비교. 단 **수업 실측에선 히스토그램이 복원되지 않았으니**(재확인 권장) export가 안전벨트.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| SA_REP·dept=50의 E-Rows 10 (히스토그램 후에도) | 노트에 설명 없음 | ? → 강사 질문 · 홈랩 재현 |
| height balanced·HYBRID 히스토그램 실물 | ① 뒤 차시 추정 | [매뉴얼 § Optimizer Statistics Concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/optimizer-statistics-concepts.html) |
| dynamic sampling level별 차이(0~11) | ④ 심화 | [매뉴얼 § SQL Processing](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/sql-processing.html) 주변 장 |
| 시간대·interval 타입 심화 | SQL 문법 곁가지 | 명령어 표 23번으로만 정리 |

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — E-Rows 공식과 통계 수명주기 5단계(수집→감시→잠금→백업→복원)
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(5.63·9.73 / 6→5·10→1 / 10%·18000·31일)를 가리고 떠올려보기 — 특히 "E-Rows 10은 어디서 온 숫자인가?"
4. 마무리 — [허브에서 78일차 문제 풀기](assets/study_hub_full.html) (날짜칩 78 필터)
