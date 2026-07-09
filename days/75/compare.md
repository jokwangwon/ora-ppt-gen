# 75일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.
> **※ 결석일** — 동기 수강생 노트(PDF) 기반으로 작성. 플랜 캡처가 없는 실험은 맨 아래 "홈랩 재현" 목록으로.

---

## [오늘의 축]

> **옵티마이저는 내 SQL을 다시 쓴다(Query Transformation) — 서브쿼리는 filter(캐시로 버티기) ↔ unnest(semi/anti 조인으로 풀기), 안 읽어도 되는 테이블은 조인 제거. 플랜에 filter 술어가 보이면 "다시 확인하라"는 신호.**

수업이 서브쿼리 4종 → filter 방식(47) → filter optimization(214→12) → unnest(semi 12) → qb_name 제어 → 조인 제거(PK-FK) → semi/anti로 이어짐 — 전부 "내가 쓴 문장과 실제 도는 문장이 다르다"의 이야기.

## [개념 제목] (수업 등장 순)

1. **Query Transformation** — 결과 동일 + 비용 절감 기대 시 SQL 재작성(8i부터 단계적) · [문서 §8 도입](assets/sql_tuning.html#qt)
2. **서브쿼리 4종** — nested / correlated(메인 행 수만큼 반복) / inline view / scalar(값 1개·cache) · [문서 §8.1](assets/sql_tuning.html#qt)
3. **filter 방식** — `no_unnest`, FILTER는 NL과 같은 반복 구조, 술어 `IS NOT NULL`·`=:B1` 읽기 · [문서 §8.2](assets/sql_tuning.html#qt)
4. **filter optimization** — input 값 cache, 최악 214블록이 실측 **12번**(department_id 종류 수만큼) · [문서 §8.2](assets/sql_tuning.html#qt)
5. **unnest** — 서브쿼리→조인 변환, 액세스 경로·조인 방법·순서의 3형제 도구가 전부 열림 · [문서 §8.3](assets/sql_tuning.html#qt)
6. **qb_name(sub) / @sub** — unnest된 서브쿼리 테이블을 힌트로 잡는 법(10g~) · [문서 §8.3](assets/sql_tuning.html#qt)
7. **서브쿼리 ≠ 조인** — 결과 건수부터 다름(1:m), m:1처럼 보장될 때만 변환. distinct inline view 우회는 곤란 · [문서 §8.3](assets/sql_tuning.html#qt)
8. **조인 제거(join elimination)** — 1쪽 미참조 + **PK·FK 제약** 있으면 1쪽을 아예 안 읽음(내부적으로 `is not null` 문장) · [문서 §8.4](assets/sql_tuning.html#qt)
9. **semi join** — IN/EXISTS, 변환된 쪽 기본 후행(RIGHT 변형 예외), match되면 브레이크. `nl_sj·merge_sj·hash_sj`, SORT UNIQUE=1쪽화 · [문서 §8.5](assets/sql_tuning.html#qt)
10. **NOT IN의 null 함정** — 서브쿼리에 null 있으면 0건(AND 진리표) · [문서 §8.5](assets/sql_tuning.html#qt)
11. **anti join** — NOT IN/NOT EXISTS, 없는 행을 찾음. `nl_aj·merge_aj·hash_aj` · [문서 §8.5](assets/sql_tuning.html#qt)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | emp/dept 재생성(drop→CTAS) + 제약·인덱스 조회 | 제약 0 · 인덱스 0 상태에서 시작 |
| 2 | `in (select /*+ no_unnest */ ...)` | **FILTER** 방식, Buffers **47** — EMP full 11 + DEPT full **Starts 12**/36, 술어 `filter(IS NOT NULL)`·`filter(=:B1)` |
| 3 | `exists (select /*+ no_unnest */ 'x' ...)` | 상호관련 filter — null 제외 **11번**+1 수행, 같은 47 |
| 4 | `count(*) from hr.dept` | dept full 1회 = **2블록** → 최악 107×2=**214** 계산의 근거 |
| 5 | filter optimization 확인 | 실측 서브쿼리 수행 **12번**뿐 — input 값(:B1) cache, 종류 수만큼만 |
| 6 | dept_idx(unique)+PK 생성 → 제약·인덱스 조회 | blevel 0(root=leaf 1블록), CF 좋음 |
| 7 | 힌트 없음 IN 재실행 | 옵티마이저 스스로 unnest → **HASH JOIN RIGHT SEMI**, Buffers **12** (DEPT 2 + EMP 10) |
| 8 | `unnest` + `leading(d,e)` use_nl/use_merge/use_hash | 조인 3형제로 순서·방법 제어 (수치 캡처 없음 → 홈랩) |
| 9 | `qb_name(sub)` + `leading(d@sub,e) use_nl(e) full(d@sub)` | @블록이름으로 서브쿼리 테이블 지정 성공 |
| 10 | emp_dept_idx 생성 → `leading(e,d@sub) use_nl(d@sub)` | 진입 인덱스 태우기 (수치 캡처 없음 → 홈랩) |
| 11 | employees⋈departments `e.*` 조회 | **조인 제거** — DEPT를 안 읽음, 내부적으로 `where department_id is not null` |
| 12 | `_optimizer_join_elimination_enabled` false/true | 세션 레벨 on/off — false면 다시 조인 플랜 |
| 13 | emp에 FK 추가 → IN 서브쿼리 재실행 | CTAS 사본도 조인 제거 작동 · `no_eliminate_join(d)`로 개별 비활성(수업 표기 no_eliminated_join은 오타) |
| 14 | `location_id=1500` 서브쿼리 vs 조인 vs no_unnest | 같은 결과 3가지 플랜 비교 — 작은 쪽 driving으로 unnest |
| 15 | `d.*` 조인 vs `(select distinct ...)` inline view | 수동 unnest 우회 — "이러시면 곤란해요" |
| 16 | dept where IN emp → SEMI · `merge_sj` · `hash_sj` | operation에 **SEMI** · merge_sj의 **SORT UNIQUE**=m쪽 1쪽화 |
| 17 | `not in (select department_id from emp)` | **0건** — 서브쿼리 null 하나로 전멸(AND 진리표) |
| 18 | `is not null` 추가 / NOT EXISTS → `nl_aj·merge_aj·hash_aj` | **ANTI** 조인 3형제 (각 플랜 캡처 없음 → 홈랩) |

## [5줄 요약]

1. **쿼리 변환 = 옵티마이저가 플랜을 만들기 전에 SQL 자체를 고쳐 쓰는 것** — 내가 쓴 문장과 도는 문장이 다를 수 있다. filter 술어가 그 신호.
2. **filter 방식은 NL과 같은 반복이지만 cache가 구한다** — 최악 214블록이 input 캐시 덕에 12번(값 종류 수)으로. `:B1`이 캐시 바인딩의 흔적.
3. **unnest되면 3형제 도구가 전부 열린다** — 서브쿼리인 채로는 순서·방법을 못 고르고, 조인이 되어야 leading/use_xx가 통한다(@sub로 지정).
4. **조인 제거는 FK가 증명해줄 때만** — "emp의 부서는 반드시 dept에 있다"는 보장이 있어야 1쪽을 안 읽어도 결과가 같다.
5. **semi는 만나면 멈추고(브레이크), anti는 없어야 담는다** — 변환된 서브쿼리는 항상 후행. NOT IN은 null 하나로 전멸하니 is not null 또는 NOT EXISTS.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| view merging·predicate pushing 등 나머지 변환 | ① 뒤 차시 추정 | [매뉴얼 § Query Transformations](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/query-transformations.html) |
| scalar subquery cache 실습 | ① 개념만 언급 | [문서 §8.1](assets/sql_tuning.html#qt) 개념만 |
| shared cursor (강사가 화두만 던짐) | ① 뒤 차시 추정 | ? → 강사 질문 |

## [홈랩 재현 권장 — 결석으로 플랜 캡처가 없는 실험]

노트에 SQL은 있는데 실행 결과 수치가 없는 것들. 홈랩에서 직접 돌려 Buffers를 채울 것:

1. `unnest` + `leading(d,e)` × **use_nl / use_merge / use_hash** 각각의 Buffers (74일차 35·15·13과 비교)
2. dept_idx 생성 **후** `exists no_unnest` — filter 방식이 인덱스로 얼마나 좋아지는가
3. emp_dept_idx 생성 후 `leading(e,d@sub) use_nl(d@sub)` — 진입 인덱스 NL 수치
4. `merge_sj` 플랜에서 **SORT UNIQUE** 위치 직접 확인 · `hash_sj`와 Buffers 비교
5. `nl_aj / merge_aj / hash_aj` 각 ANTI 플랜 모양

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — filter·unnest·조인 제거가 각각 언제 나오는지
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(47 → 12 / 214 → 12번 / Starts 12)를 가리고 떠올려보기 — 특히 "왜 107번이 아니라 12번인가?"
4. 마무리 — [허브에서 75일차 문제 풀기](assets/study_hub_full.html) (날짜칩 75 필터)
