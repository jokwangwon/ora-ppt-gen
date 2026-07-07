# 76일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **쿼리 변환 2탄 — 변환의 방향은 언제나 "더 앞 단계에서, 더 적은 행으로". null도 anti로(NA·LNNVL), or는 union all로(OR-expansion), 서브쿼리 필터는 앞으로(push_subq), 뷰는 해체하거나(view merging) 조건을 안으로(pushdown), 조인 전엔 bloom filter.**

어제(75일차)가 "서브쿼리를 어떻게 푸나"였다면 오늘은 변환 6종을 한 바퀴 — 전부 행 수를 앞에서 줄이는 이야기. 중간에 히스토그램(같은 술어 다른 플랜)이 로드맵 09 예고편으로 등장.

## [개념 제목] (수업 등장 순)

1. **null-aware anti join (ANTI NA)** — 10g까지는 is not null 명시해야 anti, 19c는 NOT IN 그대로도 `MERGE JOIN ANTI NA` · [문서 §8.6](assets/sql_tuning.html#qt)
2. **LNNVL** — 조건이 거짓이거나 null이면 참. `LNNVL(x<>:B1)` = `x is null or x=:B1` · [문서 §8.6](assets/sql_tuning.html#qt)
3. **OR-expansion** — or 조건을 union all 형태로 변환해 가지마다 인덱스. `use_concat`/`no_expand`, CONCATENATION operation · [문서 §8.7](assets/sql_tuning.html#qt)
4. **LNNVL로 중복 제거** — union all 두 가지에서 겹치는 행을 둘째 가지에서 자동 제외 · [문서 §8.7](assets/sql_tuning.html#qt)
5. **FREQUENCY 히스토그램** — 값별 분포를 알아서 같은 술어도 값 따라 index(10번=1행)/full(50번=45행) · [문서 §8.8](assets/sql_tuning.html#qt)
6. **pushing subquery (push_subq)** — unnest 안 된 서브쿼리 필터를 가능한 앞 단계로 → 다음 단계로 넘어가는 행 106→1 · [문서 §8.9](assets/sql_tuning.html#qt)
7. **view merging** — 뷰 해체 후 메인과 통합(simple/complex), 불가 목록(union·rownum·분석함수…), `merge`/`no_merge` · [문서 §8.10](assets/sql_tuning.html#qt)
8. **TP (Transitive Predicate)** — 상수 조건이 조인절을 타고 반대쪽 테이블에 전파(`access(E.DEPARTMENT_ID=20)`) · [문서 §8.10](assets/sql_tuning.html#qt)
9. **조인 조건 pushdown (push_pred)** — 조인 조건을 뷰 안으로 → `VIEW PUSHED PREDICATE`, 뷰 안에서 driving 값으로 인덱스 · [문서 §8.11](assets/sql_tuning.html#qt)
10. **bloom filter** — build 키의 비트 요약(:BF0000)을 probe에 배포, 조인 전에 건수 축소(107→2). `px_join_filter` · [문서 §8.11](assets/sql_tuning.html#qt)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | `not in (... where department_id is not null)` | **HASH JOIN ANTI**, 16행, Buffers **3** |
| 2 | `not in` 그대로 (19c, 힌트 없음) | **MERGE JOIN ANTI NA** — null 의미 유지(0행), Buffers **5**, SORT UNIQUE |
| 3 | `not in (select /*+ no_unnest */ ...)` | FILTER 방식, Buffers **57** — EMP full **Starts 27**, 술어 `LNNVL(<>:B1)` |
| 4 | `job='IT_PROG' or department_id=20` | or → **full 7** (각각 단독은 index 4 + 4) |
| 5 | union / union all 수동 재작성 | union은 SORT UNIQUE 추가 · union all+`lnnvl(department_id=20)` = **6** |
| 6 | `use_concat` | **CONCATENATION** — 두 가지 다 index, `filter(LNNVL)` 자동, **6** |
| 7 | `no_expand` | 변환 금지 → full **7** |
| 8 | `department_id=10` vs `=50` | 10(1행)=index **3** / 50(45행)=**full 9** — E-Rows 45 정확 |
| 9 | `dba_tab_columns` 히스토그램 조회 | DEPARTMENT_ID: distinct 11 · buckets 11 · **FREQUENCY** |
| 10 | `use_concat` + `or department_id=50` | 가지마다 다른 접근 — job index + 50 full, **13** |
| 11 | 3테이블 exists (힌트 없음) | 옵티마이저가 unnest → locations driving 3중 NL, **7** (adaptive) |
| 12 | `exists(/*+ no_unnest */)` | FILTER **맨 마지막** — MERGE JOIN 106행 만든 뒤 거름, **25** |
| 13 | `exists(/*+ no_unnest push_subq */)` | dept 단계에서 **먼저** 거름(27→1행) → 1행만 NL, **24** |
| 14 | Id 3·4·5 재구성: `full(d)` + exists no_unnest | FILTER + LOC_ID_PK(:B1), **22** — 플랜→SQL 역산 연습 |
| 15 | 인라인 뷰 2개 조인 (힌트 없음) | **view merging** — VIEW 없음, 직접 조인과 plan hash 동일, **6** |
| 16 | `no_merge` 양쪽 | **VIEW** operation 등장 + HASH JOIN |
| 17 | 뷰 안 `department_id=20` | **TP** — emp 쪽에 `access(E.DEPARTMENT_ID=20)` 자동 생성 |
| 18 | group by 뷰 (힌트 없음) | **complex view merging** — 조인 먼저, HASH GROUP BY 꼭대기, **4** |
| 19 | `no_merge push_pred` | **VIEW PUSHED PREDICATE** — 뷰 안에서 인덱스, **5** |
| 20 | `no_merge no_push_pred` | 뷰 전체 group by 후 HASH JOIN **8** + **:BF0000 bloom filter** (EMP 107→**2**) |
| 21 | `no_px_join_filter(e)` | bloom 제거 — EMP full **107행 그대로** group by |

## [5줄 요약]

1. **19c의 anti는 null을 안다** — NOT IN 그대로도 ANTI **NA**로 풀린다(결과는 여전히 null 의미 유지). LNNVL = "거짓이거나 모름이면 참"으로 null 의미를 술어 한 줄에 담는 장치.
2. **OR-expansion = or를 union all로** — 가지마다 인덱스를 태우고, 겹치는 행은 둘째 가지의 LNNVL이 뺀다. use_concat/no_expand.
3. **히스토그램이 있으면 같은 술어도 값 따라 플랜이 갈린다** — 50번 부서(45행)는 full이 정답, 강제 인덱스는 이득 0. 통계 본편은 09에서.
4. **push_subq·pushdown·bloom의 공통 문법 = 먼저 거르기** — 서브쿼리 필터를 앞 단계로(106→1행), 조인 조건을 뷰 안으로(group by 전에 축소), build 요약을 probe에 미리(107→2행).
5. **view merging은 뷰를 없애는 변환** — simple은 통째로 해체, complex(group by)도 해체 가능, union·rownum·분석함수가 있으면 불가. 안 쓴 상수 조건이 Predicate에 보이면 TP.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| star transformation·기타 변환 | ④ DW 심화 | [매뉴얼(SQL Tuning Guide)](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/) |
| 히스토그램 종류(HEIGHT-BALANCED·HYBRID)와 수집 | ① 로드맵 09 예정 | 다음 차시 대기 |
| bloom filter의 false positive(오탐) 원리 | ④ 알고리즘 내부 | [문서 §8.11](assets/sql_tuning.html#qt) 개념만 · CS 기본서 |
| adaptive plan의 동작(Note에 계속 등장) | ① 뒤 차시 추정 | ? → 강사 질문 |

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 변환 6종이 각각 "무엇을 앞으로 당기는지"
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(3·5·57 / 7→6 / 25→24 / 8→5 / 107→2)를 가리고 떠올려보기 — 특히 "push_subq는 Buffers가 아니라 뭘 줄였나?"
4. 마무리 — [허브에서 76일차 문제 풀기](assets/study_hub_full.html) (날짜칩 76 필터)
