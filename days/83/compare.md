# 83일차 복습 시트 (결석 — 동료 필기 기반)

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **데이터를 옮기는 비용을 줄인다 — 병렬은 재분배를 없애고(파티션 wise), I/O는 캐시를 우회하고(direct path), 정렬은 메모리에 담는다(optimal). 세 가지 다 '이동을 줄이는' 이야기.**

병렬 조인 완결(pq_distribute 4조합) + parallel DML + direct path I/O로 병렬 파트 마무리 → 새 주제 PGA·정렬(구조·자동 관리·3등급·정렬 vs 해시).

## [개념 제목] (수업 등장 순)

1. **pq_distribute 4조합** — 무엇이 파티션됐나로 재분배가 갈림 · [문서 §14.10](assets/sql_tuning.html#px)
2. **partition,none의 블룸** — PART JOIN FILTER(:BF0000)로 상대 파티션만 프루닝(§8.11 재등장) · [문서 §14.10](assets/sql_tuning.html#px)
3. **hash/broadcast** — 둘 다 넌파티션: 대용량끼리 hash·hash, 한쪽 작으면 broadcast · [문서 §14.10](assets/sql_tuning.html#px)
4. **parallel DML** — 기본 load는 serial(IN-OUT 공백), enable parallel dml·ORA-12841 · [문서 §14.11](assets/sql_tuning.html#px)
5. **direct path read/write** — 버퍼 캐시 우회(병렬·temp·expdp / DML·append·CTAS·impdp) · [문서 §14.12](assets/sql_tuning.html#px)
6. **serial direct read** — full scan 블록 > _small_table_threshold(704) → PGA로 직접 · [문서 §14.12](assets/sql_tuning.html#px)
7. **PGA 구조** — stack·UGA(cursor state·SQL work area: sort/hash/bitmap area) · [문서 §15.1](assets/sql_tuning.html#pga)
8. **자동 PGA 관리** — target(soft)/limit(hard, 12c)·workarea_size_policy·OLTP 20%/DSS 50% · [문서 §15.2](assets/sql_tuning.html#pga)
9. **정렬 3등급** — optimal(디스크0)/onepass(1회)/multipass(여러 번·저하) · [문서 §15.3](assets/sql_tuning.html#pga)
10. **Used-Temp·direct path temp** — 메모리 부족분(KB)·디스크 소트 대기 · [문서 §15.3](assets/sql_tuning.html#pga)
11. **정렬 vs 해시** — order by/집계=SORT / group by·distinct=HASH(_gby_hash_aggregation_enabled) · [문서 §15.4](assets/sql_tuning.html#pga)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령/플랜 | 결과 요지 |
|---|------|-----------|
| 1 | `pq_distribute(e,none,partition)` dept_part⋈emp_non | PX SEND PARTITION(KEY)·HASH JOIN BUFFERED — emp_non을 부서코드 KEY로 재분배 |
| 2 | `pq_distribute(e,partition,none)` dept_non⋈emp_part | **PART JOIN FILTER CREATE(:BF0000)** + PX PARTITION LIST JOIN-FILTER — 블룸으로 파티션 프루닝 |
| 3 | 〃 v$pq_tqstat | P002·P003 추출 → P000(17)·P001(10) 소비 → 조인 45·61 → QC 106 |
| 4 | `pq_distribute(e,hash,hash)` dept_non⋈emp_non | 둘 다 대용량: 조인 키 해시로 양쪽 동적 파티셔닝 |
| 5 | `pq_distribute(e,broadcast,none)` | 작은 테이블 복제 — **num_rows로 작은 쪽 복제 확인 필수**(큰 쪽 broadcast=재앙) |
| 6 | `insert /*+ parallel */ select /*+ parallel */` (dml 안 켬) | **Id 1 IN-OUT 공백=serial load** — 읽기만 병렬 |
| 7 | `alter session enable parallel dml` (트랜잭션 중) | **ORA-12841** → rollback 후 재실행 |
| 8 | `insert /*+ enable_parallel_dml parallel */` | 12c 힌트로 문장 단위 병렬 DML |
| 9 | serial direct read 확인 | full scan 블록 > **_small_table_threshold 704** → PGA 직접(캐시 우회) |
| 10 | `alter session set events '10949 …'` | direct path read 끔 → **db file scattered read**로 복귀 |
| 11 | `show parameter pga` / `workarea_size_policy` | auto — pga_aggregate_target 내 자동 관리 |
| 12 | OLTP/DSS 산정 | 물리 10GB→OS 2GB 제외 8GB: OLTP SGA 6.4·PGA 1.6 / DSS 4·4 |
| 13 | `alter session set sort_area_size = 1048576` + order by | SORT AREA 초과 → 디스크 소트, **Used-Temp** 등장 |
| 14 | 〃 v$session_event | **direct path write temp 289 / read temp 146** — sort run 디스크 왕복 |
| 15 | `v$sql_shared_cursor`·`v$sql_workarea` | sort_area_size 다르면 **child cursor** 갈림, last_tempseg_size로 추적 |
| 16 | `distinct department_id` | **HASH UNIQUE**(정렬 안 됨) — _gby_hash_aggregation_enabled 기본 TRUE |
| 17 | `opt_param('_gby_hash_aggregation_enabled','false')` | **SORT UNIQUE**(정렬됨) — 옛 알고리즘 |

## [5줄 요약]

1. **pq_distribute는 파티션 여부가 정한다** — none,none(재분배 없음)·none,partition(inner 재분배)·partition,none(outer 재분배+블룸 프루닝)·hash·broadcast(둘 다 넌파티션). broadcast는 작은 쪽이 복제됐는지 꼭 확인.
2. **쓰기도 병렬이 되지만 기본은 아니다** — 병렬 insert도 load는 serial(IN-OUT 공백). enable parallel dml로 켜고(트랜잭션 중이면 ORA-12841) 작업 후 disable.
3. **direct path는 캐시를 우회한다** — 병렬 쿼리·CTAS·append·Data Pump. full scan이 _small_table_threshold(704)를 넘으면 serial direct read로 PGA에 직접 — 병렬 QC Buffers 5의 정체.
4. **정렬은 담기면 빠르고 넘치면 느리다** — optimal(메모리)·onepass(디스크 1회)·multipass(여러 번·저하). 부족분은 Used-Temp(KB)와 direct path read/write temp 대기로 드러난다. PGA는 target(soft)/limit(hard)로 관리.
5. **group by·distinct는 이제 해시** — 중복 뭉치기엔 해시 O(n)가 정렬 O(n log n)보다 유리(_gby_hash_aggregation_enabled). HASH GROUP BY/UNIQUE는 정렬 안 됨 — 순서가 필요하면 order by를 명시.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| 정렬 trace(tracefile_identifier·10046 L8·tkprof) 실물 | 명령만, 캡처 없음 | ? → 홈랩 1번 |
| Auto DOP·parallel_degree_policy | 다음 심화 추정 | [매뉴얼 § Parallel Execution](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/parallel-exec-intro.html) |
| PGA advisor(v$pga_target_advice) | 튜닝 심화 | [매뉴얼 § Memory Architecture](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/memory-architecture.html) |
| hash join의 build/probe 메모리(hash_area) 세부 | 노트에 열린 질문(이월) | 위 매뉴얼 · 홈랩 |

## 홈랩 재현 목록 (결석일)

1. **정렬 trace 뜨기** — tracefile_identifier='sort' → 10046 level 8 → tkprof report.txt sys=no (알럿로그 위치 확인)
2. **broadcast 검증** — pq_distribute(e,broadcast,none) 후 v$pq_tqstat num_rows로 작은 테이블 복제 확인
3. **sort_area_size 스윕** — 1MB→0→키우며 optimal/onepass/multipass 경계와 Used-Temp·direct path temp 대기 관찰
4. **_small_table_threshold(704) 경계** — 그 근처 블록 테이블로 direct read↔scattered read 전환을 10949로 확인
5. (이월) 홀수 DoP·HASH JOIN BUFFERED build/probe 세부

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 재분배·캐시·메모리 세 가지 '이동 줄이기'
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과(4조합 힌트 / ORA-12841 / 704 / optimal→multipass / HASH vs SORT)를 가리고 떠올려보기
4. 마무리 — [허브에서 83일차 문제 풀기](assets/study_hub_full.html) (날짜칩 83 필터)
