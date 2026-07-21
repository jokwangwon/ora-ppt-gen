# 82일차 복습 시트 (결석 — 동료 필기 기반)

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **병렬의 모든 비용은 '집합을 건너는 통신'에서 온다 — 재분배를 없애고(파티션 wise 조인), 넘길 데이터를 줄이는(gby_pushdown) 게 병렬 튜닝의 전부다. 그리고 DoP 2인데 프로세스는 4개(추출 집합 + 정렬 집합).**

어제 개막한 §14를 v$pq_tqstat으로 파헤친 날 — Producer/Consumer, IN-OUT 5종, PQ Distrib(RANGE/HASH/KEY), gby_pushdown, 파티션 wise 조인(full/partial). 병렬 파트 마무리.

## [개념 제목] (수업 등장 순)

1. **추출 집합 vs 정렬 집합** — DoP 2인데 프로세스 4개(P002·P003 추출 / P000·P001 정렬) · [문서 §14.4](assets/sql_tuning.html#px)
2. **왜 집합을 나누나** — 한 프로세스가 다 하면 QC가 재정렬해야 함 → 추출이 RANGE로 미리 분배 · [문서 §14.4](assets/sql_tuning.html#px)
3. **병렬 산수** — 프로세스=DoP×2, 통신 채널=DoP² · [문서 §14.5](assets/sql_tuning.html#px)
4. **QC·병렬 서버·서버 풀** — min 4/max 40 미리 띄움, large pool(shared server·UGA·RMAN) · [문서 §14.5](assets/sql_tuning.html#px)
5. **서버 집합(server set)** — DoP·오퍼레이션 종류에 따라 1~여러 개 · [문서 §14.5](assets/sql_tuning.html#px)
6. **intra / inter-operation** — 집합 내 무통신 / 집합 간 통신(테이블 큐) · [문서 §14.4](assets/sql_tuning.html#px)
7. **IN-OUT 5종** — P->S·P->P·S->P(통신○) / PCWC·PCWP(통신✗), S->P만 직렬 · [문서 §14.6](assets/sql_tuning.html#px)
8. **PQ Distrib** — RANGE(정렬)·HASH(조인/해시집계)·KEY(파티션) · [문서 §14.7](assets/sql_tuning.html#px)
9. **gby_pushdown** — 추출하며 미리 group by(HASH GROUP BY ×2), no_gby_pushdown이면 ×1 · [문서 §14.8](assets/sql_tuning.html#px)
10. **full partition wise join** — 둘 다 조인 키 파티션, 재분배 없음(none,none·PARTITION LIST ALL) · [문서 §14.9](assets/sql_tuning.html#px)
11. **partial partition wise join** — 한쪽만 파티션, KEY로 재분배(none,partition·SEND PARTITION KEY) · [문서 §14.9](assets/sql_tuning.html#px)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령/플랜 | 결과 요지 |
|---|------|-----------|
| 1 | `parallel(e 2)` order by + v$pq_tqstat | **프로세스 4개** — Ranger QC / Producer P002·P003(추출 53309·54559) / Consumer P000·P001(정렬 55000·52000) |
| 2 | 〃 TQ10001 | 정렬 집합이 producer로 → QC가 107000행 머지 → user |
| 3 | `show parameter parallel_min_servers` | **4** — 병렬 없어도 미리 떠 있음 |
| 4 | `show parameter parallel_max_servers` | **40** — 부족 시 여기까지 추가(large pool) |
| 5 | IN-OUT 판별 | 화살표(P->S·P->P·S->P)=통신○ / PCWC·PCWP=통신✗ / S->P만 직렬 |
| 6 | `parallel(e 2)` group by (gby_pushdown 기본) | **HASH GROUP BY ×2** — 추출(Id 6 중간집계)→PX SEND HASH→정렬(Id 3 머지) |
| 7 | v$pq_tqstat (pushdown) | Producer P002·P003 각 12행(미리 집계) → Consumer P000 8·P001 16 |
| 8 | `no_gby_pushdown` | HASH GROUP BY **×1** — 추출이 원본 107K(P000 87000·P001 20000) 그대로 넘김 |
| 9 | emp_part·dept_part 생성 (department_id list 파티션) | 조인 키 = 파티션 키로 준비 |
| 10 | full PWJ: `pq_distribute(e,none,none)` | **PX PARTITION LIST ALL** + HASH JOIN — 재분배 없음 |
| 11 | 〃 v$pq_tqstat | P000이 2번 파티션, P001이 1·3·4번 파티션 조인 → QC 106행 붙여 전달 |
| 12 | emp_non 생성(넌파티션) | partial 준비 |
| 13 | partial PWJ: `pq_distribute(e,none,partition)` | **PX SEND PARTITION (KEY)** + HASH JOIN BUFFERED — emp_non을 부서코드 KEY로 재분배 |
| 14 | 〃 v$pq_tqstat | P002·P003 추출→P000(46, null 포함)·P001(61) 재분배→조인결과 45·61→QC 106 |

## [5줄 요약]

1. **DoP 2인데 프로세스 4개** — order by는 추출 집합(P002·P003)과 정렬 집합(P000·P001)이 따로. 프로세스=DoP×2, 통신 채널=DoP². 한 프로세스가 다 하면 QC가 재정렬해야 하니 나눈다.
2. **IN-OUT은 통신 여부** — 화살표(P->S·P->P·S->P)는 집합을 건너니 통신○, PCWC·PCWP는 한 집합 안이라 통신✗. S->P만 직렬 오퍼레이션(큰 테이블이면 병목 점검).
3. **PQ Distrib이 연산을 말한다** — RANGE=정렬(범위 분배), HASH=조인/해시집계(해시 분배), KEY=파티션 맞춤(PART KEY). 재분배는 S->P·P->P에서.
4. **gby_pushdown은 미리 세기** — 추출하며 부서별 중간 집계(HASH GROUP BY ×2)로 넘길 건수를 줄인다. §8.13 '더 앞 단계에서 더 적은 행으로'의 병렬판. no_gby_pushdown이면 원본 그대로.
5. **파티션 wise 조인** — 조인 키=파티션 키면 재분배 없음(full, none,none). 한쪽만 파티션이면 KEY로 재분배(partial, none,partition). 파티션 수만큼 프로세스가 이상적(병렬 프로세스 ≤ 파티션 수).

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| 홀수 DoP가 안 되는 이유 | 노트에 물음표만 | ? → 홈랩 1번 |
| broadcast 분배(작은 테이블 복제) | 실측은 none/partition만 | [매뉴얼 § Parallel Execution](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/parallel-exec-intro.html) |
| parallel DML·DoP 자동 결정(Auto DOP) | 다음 심화 추정 | 위 매뉴얼 같은 장 |
| HASH JOIN BUFFERED의 빌드/프로브 세부 | 노트에 열린 질문 | 위 매뉴얼 · 홈랩 2번 |

## 홈랩 재현 목록 (결석일 — 열린 질문)

1. **홀수 DoP 실험** — parallel(e 3)으로 order by 실행 시 프로세스 수·동작 확인('짝수 개념'의 진짜 이유)
2. **HASH JOIN BUFFERED** — partial 조인에서 빌드/프로브 테이블이 어떻게 만들어지는지 dbms_xplan 상세로
3. **v$pq_tqstat WAITS** — 정렬 집합의 WAITS 955가 유독 큰 의미(이월)
4. **full/partial 직접 실행** — emp_part⋈dept_part(full), emp_non⋈dept_part(partial) 돌려 v$pq_tqstat 행수를 필기와 대조 (특히 partial의 50번 부서만 P000으로 가는 재분배)

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 통신이 곧 비용, 재분배·데이터 줄이기
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과(프로세스 4개 / HASH GROUP BY ×2 / none,none vs none,partition)를 가리고 떠올려보기
4. 마무리 — [허브에서 82일차 문제 풀기](assets/study_hub_full.html) (날짜칩 82 필터)
