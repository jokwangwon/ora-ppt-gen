# 79일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **공유된 플랜은 '첫 값'이 정하고(bind peeking), 읽을 세그먼트는 'where절의 키'가 정한다(partition pruning) — 둘 다 실행계획에 증거(bind_capture · Pstart/Pstop)가 찍힌다.**

전반부는 커서 공유의 이득(리터럴 5커서→FORCE 1커서)과 함정(peeking+치우침+히스토그램), 오라클의 해법 ACS와 수동 분기. 후반부는 파티션 5형제(뷰·range·interval·hash·list·composite)와 Pstart/Pstop 읽기.

## [개념 제목] (수업 등장 순)

1. **리터럴 5문장 = 커서 5개** — sql_id/hash_value는 텍스트 해시, plan_hash_value(2466118986)는 플랜 해시 · [문서 §10.1](assets/sql_tuning.html#cs)
2. **cursor_sharing=FORCE** — 리터럴→`:"SYS_B_0"` 치환, 커서 1개(PARSE 5·LOADS 1) · [문서 §10.2](assets/sql_tuning.html#cs)
3. **bind peeking** — `_optim_peek_user_binds`, 첫 실행 값으로 플랜 수립→전원 재사용 · [문서 §10.3](assets/sql_tuning.html#cs)
4. **히스토그램+FORCE 함정** — peek=50이면 전원 full(plan_hash 3956160932) · [문서 §10.4](assets/sql_tuning.html#cs)
5. **v$sql_bind_capture** — 첫 캡처 값(10 or 50)만 — "플랜을 누가 정했나"의 증거 · [문서 §10.5](assets/sql_tuning.html#cs)
6. **ACS** — is_bind_sensitive(Y=관찰 중) / is_bind_aware(N=분화 전), child cursor 세분화 · [문서 §10.6](assets/sql_tuning.html#cs)
7. **수동 분기** — `:b_id in (50,80)` FILTER 게이트 + union all, 거짓 브랜치 Starts 0 · [문서 §10.7](assets/sql_tuning.html#cs)
8. **파티션 왜** — 관리(보관주기)·성능(random I/O 한계→pruning)·경합(hash) · [문서 §11.1](assets/sql_tuning.html#pt)
9. **파티션 뷰(~7)** — CHECK+UNION ALL, `filter(NULL IS NOT NULL)` 게이트 · [문서 §11.2](assets/sql_tuning.html#pt)
10. **range(8)·interval(11g)** — less than·maxvalue / 간격 자동 증설(SYS_P769) · [문서 §11.3~11.4](assets/sql_tuning.html#pt)
11. **hash(8i)·list(9i)** — 2^n·=/in만 pruning·경합 완화 / 값 목록·default(NULL 포함) · [문서 §11.5~11.6](assets/sql_tuning.html#pt)
12. **composite 4×4 — Pstart/Pstop** — 확정 축=SINGLE·미확정 축=ALL, 서브번호는 전체 일련번호(13~16) · [문서 §11.7](assets/sql_tuning.html#pt)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | emp 재생성(random) + emp_idx(unique)·emp_dept_idx | 실습 준비 — 107행, dept 10=1명·50=45명·80=34명 |
| 2 | 리터럴 employee_id=100~104 ×5 → v$sql | sql_id **5개**·LOADS 1씩(hard parse 5번), plan_hash **동일** |
| 3 | `alter session set cursor_sharing=force` 후 동일 5문장 | `:"SYS_B_0"` 커서 **1개** — PARSE 5·LOADS 1·EXEC 5 |
| 4 | FORCE + dept 10→20→50→80 (히스토그램 없음) | E-Rows 10 index plan — 순서 바꿔도 동일(균등 가정) |
| 5 | EXACT + 리터럴 dept 50, 10 | 커서 2개, 둘 다 같은 index plan(E-Rows 10) |
| 6 | `gather_table_stats(... 'for columns department_id size 12')` | DEPARTMENT_ID **FREQUENCY** — 이제 50=45명을 안다 |
| 7 | FORCE + 50 먼저 (재현) | plan_hash **3956160932 = FULL**, E-Rows 45 — 10·20·80도 full |
| 8 | (같은 조건 1차 실측) | E-Rows 45의 **index plan(cost 6, LOADS 3)** — 원인 미설명, 홈랩 재확인 |
| 9 | `var b_id` :b_id=10 먼저 → 50 재사용 | index 플랜 고정 — bind_capture VALUE_STRING **10** |
| 10 | flush 후 :b_id=50 먼저 → 10 재사용 | **FULL** 플랜 고정 — bind_capture **50** |
| 11 | `is_bind_sensitive, is_bind_aware` 조회 | **Y / N** — 관찰 시작, child 분화 전 |
| 12 | allstats last 값별 실측 | 10→A-Rows 1·Buf 3 / 50→45·**9**(index) vs **6**(full 힌트) / 80→34·8 |
| 13 | `:b_id in (50,80)` full + `not in` index, union all | FILTER 게이트 — :b_id=50: full 브랜치 Starts 1, index 브랜치 **Starts 0·Buf 0** |
| 14 | PL/SQL if-else + bulk collect | 같은 분기를 절차적으로 — 부서 없으면 안내 메시지 |
| 15 | p1/p2/p3 + CHECK + UNION ALL 뷰, dept=10 | P1만 읽음(Buf 7) — P2/P3 `filter(NULL IS NOT NULL)` **Starts 0** (전체 조회는 Buf 18) |
| 16 | `partition by range(hire_date)` 4개(pmax 포함) | high_value는 dba_tab_partitions에 — `partition(p2004)` 지정 조회 |
| 17 | `interval(numtoyminterval(1,'year'))` 재생성 | 경계 밖 값 → **SYS_P769·770 자동 생성** (maxvalue 불필요) |
| 18 | interval 함수 4종 | to_yminterval('1-10')→10-MAY-28 · to_dsinterval('10 10:10:10')→21-JUL-26 |
| 19 | `partition by hash(employee_id) partitions 4` | SYS_P771~774, high_value 없음 — =·in만 pruning |
| 20 | `partition by list(department_id)` + values(default) | dept NULL인 **Grant(178)**가 default 파티션에 |
| 21 | `range(salary) subpartition by hash(employee_id) subpartitions 4` | 4×4 = **세그먼트 16개**(SYS_SUBP1084~1099) |
| 22 | `+partition` 포맷으로 6가지 조건 실측 | 두 키=1/16(Buf 2~3) · 한 키=4/16(Starts 4) · HASH 번호는 **전체 일련번호**(pmax h3=15) |

## [5줄 요약]

1. **sql_id는 텍스트의 해시** — 값만 다른 리터럴 5문장이 같은 플랜을 5번 hard parse했다. FORCE가 `:"SYS_B_0"`으로 묶어 커서 1개로.
2. **bind peeking은 첫 값이 모두의 플랜을 정한다** — 10 먼저면 50도 index(9블록, full이면 6), 50 먼저면 10도 full. 증거는 v$sql_bind_capture의 첫 캡처 값.
3. **함정의 재료는 3개** — peeking + 치우친 분포 + 히스토그램. 히스토그램이 없으면 어떤 값이든 E-Rows 10이라 함정 자체가 안 보인다.
4. **해법은 ACS(sensitive→aware child 분화) 또는 분기 SQL** — FILTER 게이트(`:B_ID=50 OR 80`)가 거짓 브랜치를 Starts 0으로 잠근다. 파티션 뷰의 `NULL IS NOT NULL`과 같은 무늬.
5. **파티션은 읽을 범위를 설계로 줄인다** — range=이력·interval=자동 증설·hash=경합(=·in만)·list=그룹+default. composite의 Pstart/Pstop: 확정 축 SINGLE·미확정 축 ALL, 두 키를 다 주면 16분의 1(Buffers 2).

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| 히스토그램+FORCE 실측 불일치(index cost 6 vs full) | 노트에 원인 설명 없음 | ? → 홈랩 flush로 순서 통제 재현 |
| ACS aware=Y 전환(child cursor 실제 분화) | 수업은 sensitive=Y까지 | [매뉴얼 § Cursor Sharing](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/improving-rwp-cursor-sharing.html) · 홈랩 관찰 |
| 파티션 인덱스(local/global) | ① 다음 차시 추정 | [매뉴얼 § Partitioning Concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/partition-concepts.html) |
| reference·system 등 그 외 파티션 유형 | ④ 심화 | 위 매뉴얼 같은 장 |

## 홈랩 재현 목록

1. **peek 순서 통제 실험** — flush → FORCE+히스토그램에서 50 먼저/10 먼저 각각 → 공유 플랜이 full/index로 갈리는지 재확인 (수업 실측 8번 불일치 해소)
2. **aware=Y 잡기** — :b_id 10↔50 반복 실행하며 v$sql의 is_bind_aware·child_number 관찰
3. (이월) SA_REP·dept=50 E-Rows 10 — 히스토그램 후에도 10인 이유

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — peeking의 3재료와 pruning의 SINGLE/ALL 규칙
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(5커서→1커서 / Buf 9 vs 6 / 7 vs 18블록 / 1/16·4/16·Pstop 15)를 가리고 떠올려보기
4. 마무리 — [허브에서 79일차 문제 풀기](assets/study_hub_full.html) (날짜칩 79 필터)
