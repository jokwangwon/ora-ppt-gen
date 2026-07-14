# 81일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **파티션은 조각을, 인덱스는 조각 안을(140→3), Data Pump는 조각의 백업을, 병렬은 조각들의 동시 읽기를 — 전부 '나눈 것'을 다루는 기술이다. 그리고 global의 대가는 통째 UNUSABLE(복구는 파티션별 rebuild).**

①어제 숙제 해결(shrink 1,006→1) ②Data Pump 파티션 복구 3종 ③로컬/글로벌 파티션 인덱스 ④병렬 처리 개막(QC·TQ·RANGE 분배).

## [개념 제목] (수업 등장 순)

1. **shrink 검증** — 1,006블록→1(조회 Buffers 2), HWM 회수 실증 · [문서 §11.12](assets/sql_tuning.html#pt)
2. **_partition_large_extents** — 파티션 초기 익스텐트 8MB(8388608)의 이유 · [문서 §11.12](assets/sql_tuning.html#pt)
3. **directory 객체 + expdp/impdp** — 파티션 테이블 전체 백업·복원(통계까지) · [문서 §11.13](assets/sql_tuning.html#pt)
4. **drop 파티션 복구 절차** — ORA-02149 → sqlfile(DDL만) → split → `:p1 content=data_only` · [문서 §11.13](assets/sql_tuning.html#pt)
5. **파티션만 백업** — `tables=hr.sal_emp:p1`(204KB) → truncate → data_only 복원 · [문서 §11.13](assets/sql_tuning.html#pt)
6. **pruning의 한계** — RANGE SINGLE인데 Buffers 140(조각 안은 full) · [문서 §13.1](assets/sql_tuning.html#pi)
7. **로컬 파티션 인덱스** — 1:1 매핑·개수/키 일치·자동 관리·PREFIXED, 140→**3** · [문서 §13.2](assets/sql_tuning.html#pi)
8. **PARTITION RANGE ITERATOR** — 연속 일부 파티션 반복, INDEX SCAN Starts 2 · [문서 §13.3](assets/sql_tuning.html#pi)
9. **글로벌 파티션 인덱스** — 테이블(employee_id 6개)과 다른 축(hire_date 4개), 인덱스 축 pruning(Buffers 5) · [문서 §13.4](assets/sql_tuning.html#pi)
10. **UNUSABLE** — 힌트 강제=ORA-01502 / 힌트 없으면 full 우회(608블록, 조용한 성능 저하) · [문서 §13.5](assets/sql_tuning.html#pi)
11. **rebuild partition** — ORA-14086(통째 불가) → 조각별 4번, 인덱스에도 split · [문서 §13.5](assets/sql_tuning.html#pi)
12. **병렬 처리 개막** — QC·:TQ·IN-OUT(P->S/P->P·PCWP/PCWC)·v$pq_tqstat·RANGE/ORDER 분배 · [문서 §14](assets/sql_tuning.html#px)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | `enable row movement` → `modify partition p3 shrink space cascade` → disable → partname 통계 | P3 BLOCKS **1,006→1**, `partition(p3)` 조회 Buffers **2** (이후 조회 6 — 시점차, 홈랩) |
| 2 | 딕셔너리 + initial_extent | 전 파티션 **8,388,608(8MB)** — `_partition_large_extents=TRUE`(x$ksppcv) |
| 3 | `create directory pump_dir` + grant | dba_directories에 등록 — Data Pump 준비 |
| 4 | `expdp … tables=hr.sal_emp dumpfile=…` | 237,568B 덤프 |
| 5 | `drop table purge` → `impdp` | 파티션 구조·데이터·**통계까지** 복원(row movement 이력도 p4에 그대로) |
| 6 | `drop partition p1` → `partition(p1)` 조회 | 49행 유실 — **ORA-02149**(파티션 없음) |
| 7 | `impdp … sqlfile=sql_emp.sql` | 실행 없이 **DDL만 추출**(2,801B) — 원래 경계 확인 |
| 8 | `split partition p2 at(5000) into (p1,p2)` | 빈 p1 재생성(통계 NULL) — add는 14074라 split |
| 9 | `impdp … tables=hr.sal_emp:p1 content=data_only` | p1에 **49행 복원** → partname 통계 재수집(49/19/17) |
| 10 | `expdp … tables=hr.sal_emp:p1` → truncate → impdp data_only | 파티션만 백업(204,800B) → 0행 → 49행 |
| 11 | emp_local 생성(107,000행, employee_id 6파티션) + granularity auto | P1 19,999/156 · P3 40,000/296 · PMAX 0 |
| 12 | `where employee_id=1000` (인덱스 없음) | RANGE SINGLE + **FULL, Buffers 140** — 조각 안은 전부 스캔 |
| 13 | `create unique index … (employee_id) local` | **LOCAL·PREFIXED·6파티션**, leaf 41/42/84/42/15/0 |
| 14 | `=1000` 재실행 | BY **LOCAL INDEX ROWID** + UNIQUE SCAN — **Buffers 3** |
| 15 | `between 1000 and 1100` | RANGE SINGLE + BATCHED + RANGE SCAN — 101행, Buffers 19 |
| 16 | `between 1000 and 25000` (P1~P2) index_rs | **RANGE ITERATOR**(1·2) + RANGE SCAN **Starts 2**, Buffers 53 |
| 17 | 〃 index_ffs | FAST FULL SCAN Starts 2 — Buffers 95·Reads 32 (여기선 rs 승) |
| 18 | 〃 + parallel_index 2 | PX BLOCK ITERATOR — QC Buffers 10 (§14 예고) |
| 19 | emp_global + `create index …(hire_date) global partition by range` 4개 | **GLOBAL·PREFIXED·4파티션** — 테이블(6)과 개수·축 다름 |
| 20 | hire_date 2001년 count | RANGE SINGLE = **인덱스 파티션 축** — RANGE SCAN **Buffers 5** (FFS 85) |
| 21 | (테이블 파티션 작업 후 — 캡처 없음) 딕셔너리 | 4파티션 전부 **UNUSABLE** |
| 22 | index_rs 힌트 / 힌트 없이 | **ORA-01502** / RANGE ALL + FULL Starts 5, **Buffers 608**·Reads 604 |
| 23 | `alter index … rebuild` | **ORA-14086** — 통째 불가 |
| 24 | `rebuild partition p2004` ×4 | 전부 USABLE — leaf 77→63 컴팩트 |
| 25 | `alter index … split partition pmax at(2008-01-01)` | 인덱스에도 split — p2007 신설 후 pmax rebuild |
| 26 | emp 재생성(107,000행/760블록) serial full | Buffers **742**·Reads 740 |
| 27 | `parallel(e 2)` count(*) | PX 플랜(QC Buffers 5)·Note DoP 2·direct path read — 워커 통계는 플랜에 0 |
| 28 | `v$pq_tqstat` | Producer **P000·P001 각 1행** → Consumer QC 2행 (DoP 4면 P000~P003→4행) |
| 29 | `parallel(e 2)` + order by | **TQ 2개** — ①PX SEND **RANGE**(P->P) ②SORT ORDER BY ③QC(**ORDER**) |

## [5줄 요약]

1. **shrink는 진짜 든다** — 1,006블록→1(조회 2블록). 그리고 파티션 세그먼트는 기본 8MB로 시작(_partition_large_extents) — HWM의 기억과 시작 크기는 다른 결의 공간 이슈.
2. **Data Pump는 파티션 단위로 돈다** — 전체 덤프면 통계까지 복원, drop한 파티션은 sqlfile(DDL 추출)→split(빈 조각)→`:p1 content=data_only`(데이터만) 3단으로 복구.
3. **파티션은 '어느 조각', 인덱스는 '조각 안 어디'** — pruning만으로 140블록, 로컬 인덱스(1:1·PREFIXED·자동 관리) 후 3블록. 걸치면 ITERATOR + Starts=파티션 수.
4. **global은 조회 축을 얻고 안정성을 낸다** — hire_date 축 pruning으로 5블록. 대신 테이블 파티션 작업에 통째 UNUSABLE(힌트=ORA-01502, 아니면 608블록 조용한 우회) → ORA-14086이라 rebuild partition 조각별.
5. **병렬은 QC가 지휘하고 TQ로 흐른다** — 워커 분담은 v$pq_tqstat(P000·P001 각 1행), 플랜의 0들은 QC 기준 착시. 분배 방식이 연산을 말한다: 합계=RANDOM 1큐, 정렬=RANGE(P->P)→ORDER 2큐.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| UNUSABLE의 방아쇠(어떤 테이블 작업이었나) | 노트에 캡처 없음 | ? → 홈랩 1번 재현 |
| global 인덱스의 update global indexes 옵션 | ④ 심화(작업 시 인덱스 유지) | [매뉴얼 § Partition Administration](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/partition-admin.html) |
| NON-PREFIXED 인덱스 | 수업은 PREFIXED만 실측 | [매뉴얼 § Partitioning Concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/partition-concepts.html) |
| 병렬 DoP 결정 규칙·parallel DML | 다음 차시 추정(개막만) | [매뉴얼 § Parallel Execution](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/parallel-exec-intro.html) |

## 홈랩 재현 목록

1. **UNUSABLE 방아쇠 찾기** — emp_global 테이블 파티션 truncate/drop/split 각각 후 글로벌 인덱스 status 확인, 같은 작업에서 emp_local의 로컬 인덱스는 무사한지 대조
2. shrink 후 blocks **1 vs 6** — 통계 수집 시점 차이 확인
3. (이월) arraysize×파티션 Buffers 매트릭스 · 동적 pruning KEY 표기
4. v$pq_tqstat **WAITS** 컬럼 의미 — 수업 질문 후보

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — '나눈 것'을 다루는 네 기술과 global의 대가
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(1,006→1 / 140→3 / 5 vs 608 / P000·P001 각 1행)를 가리고 떠올려보기
4. 마무리 — [허브에서 81일차 문제 풀기](assets/study_hub_full.html) (날짜칩 81 필터)
