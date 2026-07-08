# 77일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **조건은 이동하고(pushdown·pullup), 집계 서브쿼리는 분석함수가 된다 — 그리고 그 모든 판단의 재료가 통계(Part 09 개막): RBO의 규칙이 아니라 CBO의 비용, 하드웨어까지 아는 시스템 통계, all_rows냐 first_rows냐.**

쿼리 변환 3탄(조건절 이동·집계 서브쿼리 제거)으로 Part 08을 닫고, 분석함수 도구를 손에 쥔 뒤, 옵티마이저 본편(Part 09)이 열린 날.

## [개념 제목] (수업 등장 순)

1. **조건절 pushdown** — 복합 뷰 merging 실패 시 밖의 상수 조건을 뷰 안으로 → group by 할 데이터양 축소 · [문서 §8.12](assets/sql_tuning.html#qt)
2. **SORT GROUP BY NOSORT** — 인덱스가 group by 키 순서를 제공해 정렬 생략("인덱스가 정렬 대체" 3번째 재등장) · [문서 §8.12](assets/sql_tuning.html#qt)
3. **조건절 pullup** — 뷰 안의 조건을 꺼내 반대편 뷰 안으로 재주입, 양쪽 Predicate에 access(=20) · [문서 §8.12](assets/sql_tuning.html#qt)
4. **_pred_move_around** — 조건절 이동 전체를 제어(기본 TRUE), off 상태에선 push_pred(조인 조건 pushdown)가 대타 · [문서 §8.12](assets/sql_tuning.html#qt)
5. **집계 서브쿼리 제거(_remove_aggr_subquery)** — 집계 상호관련 서브쿼리를 분석함수로 변환(VW_WIF_1·WINDOW BUFFER) · [문서 §8.13](assets/sql_tuning.html#qt)
6. **분석함수 over()** — 전체/누적/partition별 집계를 행마다 · [문서 §8.14](assets/sql_tuning.html#qt)
7. **rank vs dense_rank** — 동점 뒤 갭(1,1,3) vs 연이음(1,1,2) · [문서 §8.14](assets/sql_tuning.html#qt)
8. **top-n의 rownum 함정** — rownum이 order by보다 먼저 적용 → 인라인 뷰 or rank()로 · [문서 §8.14](assets/sql_tuning.html#qt)
9. **listagg** — 여러 행 값을 가로 한 줄로 · [문서 §8.14](assets/sql_tuning.html#qt)
10. **RBO → CBO** — 규칙 순위(10g 중단) vs 비용 예측(oracle 7~), OBJECT 통계(tab$·col$·ind$) · [문서 §9.1](assets/sql_tuning.html#opt)
11. **시스템 통계(aux_stats$)** — noworkload(CPUSPEEDNW·IOSEEKTIM·IOTFRSPEED) vs workload(SREADTIM·MBRC…) · [문서 §9.2](assets/sql_tuning.html#opt)
12. **optimizer_mode** — all_rows(전체 처리율, 10g 기본) vs first_rows_n(첫 응답, OLTP) · [문서 §9.3](assets/sql_tuning.html#opt)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | group by 뷰 밖에서 `where department_id=20` | **조건절 pushdown** — SORT GROUP BY NOSORT + access(=20), Buffers **2** |
| 2 | 뷰 단독 group by | HASH GROUP BY, 107행 전체, **6** |
| 3 | where를 뷰 안에 직접 쓴 문장 | pushdown 결과와 **plan hash 동일**(2036705853) |
| 4 | =20 있는 뷰 a ⋈ 조건 없는 뷰 b | **pullup** — 양쪽 뷰에 access(=20), b도 2블록만, 총 **4** |
| 5 | `_pred_move_around` 조회 | TRUE (조건절 이동 제어 파라미터) |
| 6 | `opt_param('_pred_move_around','false') no_push_pred(b)` | b가 107행 전체 group by, **8** |
| 7 | 같은 off 상태 + `push_pred(b)` | NL + **VIEW PUSHED PREDICATE**(조인 조건 pushdown이 대타), **4** |
| 8 | 부서 평균 초과자 (집계 상호관련 서브쿼리) | 자동 변환 — **VW_WIF_1 + WINDOW BUFFER**, 38행, **8** |
| 9 | `opt_param('_remove_aggr_subquery','false')` | **VW_SQ_1**(서브쿼리를 group by 뷰로 unnest 후 조인) — EMP 두 번 읽어 **17** |
| 10 | Id 6/2/1 수동 재구성 (group by 뷰→merge→hash) | 자동 변환 플랜을 SQL로 역산하는 연습 |
| 11 | `sum(salary) over(...)` 시리즈 | 전체합·누적합·부서별합·부서별누적 (avg·count 동일 패턴) |
| 12 | 분석함수+case 인라인 뷰로 부서 평균 초과자 | 서브쿼리 없이 같은 결과 — WINDOW BUFFER, **8** |
| 13 | `where rownum<=10 order by salary desc` | **함정** — 랜덤 10건 뽑고 나서 정렬 |
| 14 | 인라인 뷰 order by → 밖 rownum / `rank()<=10` | 올바른 top-n 두 가지 (동점은 rank/dense_rank 차이) |
| 15 | `listagg(last_name,',') within group(...)` | 세로 값들을 가로 한 줄로 (group by별도 가능) |
| 16 | `_optimizer_cost_model` 조회 | CHOOSE — 시스템 통계 있으면 CPU 모델, 없으면 I/O 모델 |
| 17 | `sys.aux_stats$` 조회 | noworkload 3종만 값 있음 (CPUSPEEDNW 2547·IOSEEKTIM 10·IOTFRSPEED 4096) |
| 18 | `gather_system_stats('NOWORKLOAD'/'start'/'stop')` | 시스템 통계 수집 — workload는 부하 구간에서 |
| 19 | `set_system_stats('SREADTIM',1.2)` 등 | 개발 DB 통계를 운영에 수동 반영 |
| 20 | dept=50: `all_rows` vs `first_rows(10)` | full 9 vs **INDEX RANGE SCAN**(E-Rows 10) — 목표가 다르면 플랜이 다르다 |

## [5줄 요약]

1. **상수 조건도 이동한다** — 밖→안(pushdown)으로 group by 양을 줄이고, 안→밖→반대편 안(pullup)으로 양쪽 뷰가 같은 조건을 얻는다. 제어는 `_pred_move_around`.
2. **집계 상호관련 서브쿼리는 분석함수가 된다** — VW_WIF_1·WINDOW BUFFER가 흔적. EMP를 두 번 읽던 일(17)이 한 번(8)으로.
3. **top-n에서 rownum은 order by보다 먼저 먹는다** — 인라인 뷰로 정렬을 먼저 끝내거나 rank() over()로. 동점 처리까지 챙기면 dense_rank.
4. **CBO는 규칙이 아니라 비용** — OBJECT 통계(tab$·col$·ind$)에 시스템 통계(aux_stats$)까지, 하드웨어 성능(I/O 속도·CPU)을 알고 비용을 계산한다. RBO는 10g에서 중단.
5. **optimizer_mode = 최적화 목표 선언** — all_rows(전체 처리율)와 first_rows_n(첫 응답)은 같은 쿼리에 다른 플랜(full 9 vs index)을 만든다. 목표를 정해줘야 옵티마이저가 맞게 판단한다.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| OBJECT 통계 수집(dbms_stats.gather_table_stats 옵션들) | ① 다음 차시 예고 (09 본편 계속) | 다음 수업 대기 |
| 카디널리티 추정 공식·selectivity | ① 다음 차시 예고 | [매뉴얼 § Optimizer Statistics Concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/optimizer-statistics-concepts.html) |
| WINDOW SORT vs WINDOW BUFFER 차이 | ④ 내부 심화 | [문서 §8.13](assets/sql_tuning.html#qt) 개념만 |
| first_rows가 플랜을 실제로 어떻게 계산하나 | ④ 비용 모델 내부 | ? → 강사 질문 |

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 조건절 이동 2방향과 집계→분석함수, 그리고 CBO의 재료
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(2·4·8 / 8 vs 17 / full 9 vs index)를 가리고 떠올려보기 — 특히 "VW_WIF_1이 왜 더 싼가?"
4. 마무리 — [허브에서 77일차 문제 풀기](assets/study_hub_full.html) (날짜칩 77 필터)
