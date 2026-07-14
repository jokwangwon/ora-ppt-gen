# 80일차 복습 시트 (결석 — 동기 자료 기반)

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리. **캡처 없는 실험은 맨 아래 홈랩 목록.**

---

## [오늘의 축]

> **낭비는 두 곳에서 온다 — 같은 블록을 다시 집는 것(운반단위 arraysize로 줄인다), 안 읽어도 될 세그먼트를 읽는 것(pruning으로 줄인다). 그리고 파티션 운영은 에러 번호→처방 세트(14074→split · 14402→row movement · 14400→maxvalue)로 외운다.**

전반부 부분범위처리·arraysize 산수(535,000행 실측), 후반부 정적/동적 pruning과 파티션 관리 명령 전체(split/add/rename/drop/truncate/merge/exchange/shrink).

## [개념 제목] (수업 등장 순)

1. **부분범위처리** — 운반단위까지만 처리 후 잠정 멈춤. 웹 page·Developer 50이 이 원리 · [문서 §12](assets/sql_tuning.html#ar)
2. **전체범위 강제 & 대안** — 그룹함수/order by/union·minus·intersect → index·union all+not exists·not exists·exists · [문서 §12.1](assets/sql_tuning.html#ar)
3. **운반단위 산수** — rows÷roundtrips=arraysize (35,668→15 · 5,351→100 · 536→1000 · 269→2000) · [문서 §12.2](assets/sql_tuning.html#ar)
4. **gets의 정체와 임계점** — gets≈블록수+fetch 재방문, 바닥은 블록 수(≈3,300) · [문서 §12.2](assets/sql_tuning.html#ar)
5. **arraysize × 파티션** — 두 다이얼은 다른 낭비를 줄인다 (15면 파티션도 I/O 증가) · [문서 §12.3](assets/sql_tuning.html#ar)
6. **정적 pruning** — 상수 조건, 플랜 생성 시 결정, Pstart/Pstop=번호 · [문서 §11.8](assets/sql_tuning.html#pt)
7. **동적 pruning** — 바인드 조건, 실행 시점 결정, KEY 표기, I/O는 같다 · [문서 §11.8](assets/sql_tuning.html#pt)
8. **split / add(ORA-14074)** — 중간 경계는 split만, add는 끝에만 · [문서 §11.9](assets/sql_tuning.html#pt)
9. **rename(통계 유지) / drop(복구=로그마이너) / truncate partition** · [문서 §11.9](assets/sql_tuning.html#pt)
10. **row movement(ORA-14402) / maxvalue(ORA-14400)** — 경계 넘는 update·insert의 처방 · [문서 §11.10](assets/sql_tuning.html#pt)
11. **merge(통계 자동 수집·문법 주의) / exchange(세그먼트 맞교환·truncate 대용)** · [문서 §11.10](assets/sql_tuning.html#pt)
12. **1행 1,006블록 → shrink space cascade** — HWM의 기억, row movement 선행 · [문서 §11.11](assets/sql_tuning.html#pt)

## [실습 명령어 정리] (자료 등장 순 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | sal_emp 생성(rownum × connect by level≤5000) | **535,000행**, 3,254블록(동기)/3,774(강사) — "나는 왜 항상 작은가?" = 환경 차 |
| 2 | `set autotrace trace stat` + 전량 조회 (arraysize 15) | gets **38,685** · roundtrips **35,668** → 535,000÷35,668=**14.99≈15** |
| 3 | `set arraysize 100` | gets 8,513 · roundtrips 5,351 (99.98) |
| 4 | `set arraysize 1000` | gets 3,732 · roundtrips 536 (998.13) |
| 5 | `set arraysize 2000` | gets 3,467 · roundtrips 269 (1,988.8) — **"비약적으로 줄지 않는 임계점"** |
| 6 | `set arraysize 5000` | roundtrips 108 — 자료의 '53500/108=495.3'은 **0 누락 오기로 보임**(535,000÷108≈4,954, 재확인) |
| 7 | `show parameter db_file_multiblock_read_count` | 128 — multi block I/O는 운반단위에 좌우(3,774/128 어림) |
| 8 | arraysize 15/1000/2000 × `allstats last +partition` | **캡처 없음** — 홈랩 1번 |
| 9 | sal_emp를 range(salary) 4파티션 재생성 + `granularity=>'auto',degree=>2` | 파티션 실험 준비 |
| 10 | index range scan × arraysize 15/100/1000 | **캡처 없음** — 강사 관찰: 15면 파티션도 I/O↑, 100+면 비파티션보다↓ |
| 11 | 상수 조건 조회 | **정적 pruning** — 플랜 생성 시 파티션 확정(Pstart/Pstop 번호) |
| 12 | `:b_start/:b_stop` 바인드 between 조회 | **동적 pruning** — 실행 시점 결정, KEY 표기(캡처 없음), I/O는 동일 |
| 13 | `split partition p3 at(20000) into (p3,p4)` | 중간 경계 생성 — 기존 p3 데이터 분배 |
| 14 | `add partition … less than(10000)` | **ORA-14074** — 마지막 경계보다 작으면 add 불가 → split |
| 15 | `rename partition p5_1 to p5` | interval의 SYS_P 이름 정리용 — **통계 유지** |
| 16 | `drop partition p5` | 복구는 timebased recovery — 시점은 **로그마이너**(supplemental log부터) |
| 17 | `truncate partition p3` | p3만 비움 — no rows selected |
| 18 | 파티션 키 update 18000 / 21000 | 파티션 내 OK / **ORA-14402** → `enable row movement` 후 성공, 작업 후 disable |
| 19 | insert 29000 (pmax 없음) | **ORA-14400** → `add partition pmax` 후 수용 |
| 20 | `split partition pmax at(30000)` | pmax에 경계 만들기 — add는 14074라 split만 가능 |
| 21 | `merge partitions p4,p5 into partition p5` | 문법 주의(복수/단수) — merge 순간 **통계 자동 수집** 확인 |
| 22 | `exchange partition p5 with table exch_emp` | **세그먼트 맞교환**(이동 없음) — 재실행하면 원위치, load·truncate 대용 |
| 23 | 파티션별 통계 조회 | **P3: NUM_ROWS 1, BLOCKS 1,006** — "버그 냄새가 난다" |
| 24 | `enable row movement` → `modify partition p3 shrink space cascade` → disable | HWM 아래 낭비 회수 (후속 blocks 캡처 없음 — 홈랩 5번) |
| 25 | `gather_table_stats(…,partname=>'p3',granularity=>'partition')` | 특정 파티션만 통계 — 이름은 문자열 취급 |

## [5줄 요약]

1. **부분범위처리 = 운반단위에서 멈추기.** 집계·order by·union/minus/intersect는 전체범위 강제 — 대안은 인덱스 정렬과 union all+not exists/not exists/exists.
2. **roundtrips는 산수다** — 총 행수÷arraysize. 15→35,668회 왕복이 2000→269회로. fetch count 감소 = 네트워크 부하 감소.
3. **gets ≈ 블록 수 + fetch 재방문** — 38,685의 대부분은 재방문이었고, 바닥은 블록 수(≈3,300). 임계점 아래로는 안 내려가니 무작정 크게가 답이 아니다.
4. **pruning은 정적(상수→플랜 때 번호)·동적(바인드→실행 때 KEY)** — I/O는 같고 '언제 아느냐'만 다르다.
5. **파티션 운영은 에러→처방 세트** — 14074=중간 경계 add→split, 14402=경계 넘는 update→row movement(후 disable), 14400=받을 곳 없음→maxvalue. merge는 통계 덤, exchange는 이름표 교환(load·truncate 대용), 1행 1,006블록은 HWM의 기억→shrink cascade.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| 파티션 인덱스(local/global) | ① 다음 차시 추정 | [매뉴얼 § Partition Administration](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/partition-admin.html) |
| 동적 pruning KEY 표기 실물 | 자료에 캡처 없음 | 홈랩 2번 → 위 매뉴얼 |
| coalesce(hash 전용 축소) 등 나머지 관리 명령 | ④ 심화 | 위 매뉴얼 같은 장 |
| exchange의 인덱스/제약 옵션(including indexes 등) | ④ 심화 | 위 매뉴얼 같은 장 |

## 홈랩 재현 목록 (결석일 — 캡처 없는 실험)

1. **arraysize × 파티션 Buffers 매트릭스** — salary between 5000 and 8000을 arraysize 15/100/1000/2000, 비파티션/파티션/인덱스 조합으로 `allstats last +partition` 실측 (강사 관찰 수치화)
2. **동적 pruning KEY 확인** — `between :b_start and :b_stop` 플랜의 Pstart/Pstop 표기
3. **split·merge 후 high_value/데이터 분배** — dba_tab_partitions 전후 비교
4. **exchange 왕복 검증** — 2회 실행 후 원위치 확인
5. **shrink 효과 측정** — p3 blocks 1,006 → shrink space cascade 후 값 / arraysize 5000의 '495.3' 오기 검산(535,000÷108≈4,954)
6. (이월) 79일차 peek 순서 통제 · ACS aware=Y 전환

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 두 다이얼(재방문·pruning)과 에러 3종 처방 세트
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(35,668→15 / 3,467 임계점 / 1행 1,006블록)를 가리고 떠올려보기
4. 마무리 — [허브에서 80일차 문제 풀기](assets/study_hub_full.html) (날짜칩 80 필터)
