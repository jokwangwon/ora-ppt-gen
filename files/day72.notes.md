# 실행계획 숫자를 읽어 SQL을 판정한다 — 발표 대본

> 72일차 — 실습 플랜을 직접 읽으며


---

## ■ [00] 오늘의 큰 그림

### [1] 실행계획과 tkprof가 남긴 숫자를 읽으면 SQL이 한 일이 보인다
- [다이어그램] (그림)
- [오늘 하루가 이 세 칸이다] SQL을 돌리면 display_cursor나 tkprof가 숫자를 남긴다. 그 숫자 — Starts, E-Rows/A-Rows, Buffers — 를 읽으면 어디가 무거운지, 옵티마이저 추정이 맞았는지가 보인다. 오늘 추적·인덱스·조인은 전부 이 숫자로 판정한다.

**발표 노트 →** 자, 오늘을 한 장으로 묶으면 이겁니다. SQL을 실행하면 실행계획이나 tkprof가 숫자를 잔뜩 남겨요. 우리가 할 일은 그 숫자를 읽는 거예요. Starts, E-Rows와 A-Rows, Buffers. 이걸 읽으면 이 쿼리가 어디서 힘을 쓰는지, 옵티마이저가 예측을 잘했는지가 다 보입니다. 오늘 배우는 건 전부 이 숫자를 읽어서 '어느 쪽이 낫다'를 판정하는 거예요. 오늘은 개념만 보고 끝내지 않고, 실제로 돌린 플랜을 같이 읽어보겠습니다.

### [2] 오늘은 70·71일차에서 시작한 플랜 읽기를 실전 판정까지 끌고 간다
- [다이어그램] (그림)
- [이전 수업과의 연결] Buffers·consistent gets 읽는 법은 70일차 autotrace, tkprof·CF는 71일차. and_equal은 69일차, TX 잠금 진단은 68일차. 오늘 새로 얹는 건 10046·BCHR·bitmap·조인, 그리고 이 숫자들로 경로를 실제로 고르는 판정이다.

**발표 노트 →** 그 전에, 오늘이 갑자기 나온 게 아니에요. 실행계획 Buffers 읽는 법은 70일차, tkprof랑 클러스터링 팩터는 어제 71일차에 했죠. and_equal은 69일차, TX 잠금 진단은 68일차. 오늘 새로 배우는 건 10046, 버퍼 캐시 히트율, bitmap, 조인 — 그리고 이 숫자로 실제 경로를 고르는 판정입니다.

---

## ■ [01] 실행계획 숫자 읽기

### [3] 먼저 개념 — 플랜의 네 숫자가 각각 무엇을 말하나
- [표] 컬럼 | 뜻 | 읽는 법  (4행)
- [access와 filter도 구분] access는 인덱스로 바로 좁힌 조건, filter는 읽고 나서 버린 조건. 핵심 조건이 filter로만 잡히면 인덱스 기회를 놓친 것이다.

**발표 노트 →** 먼저 개념부터 잡고 실제로 읽어봅시다. display_cursor를 allstats last로 뽑으면 이 컬럼들이 나와요. Starts는 그 operation이 몇 번 실행됐나 — 1보다 크면 안쪽이 반복됐다는 뜻이고, 조인에서 진짜 중요해집니다. E-Rows와 A-Rows는 예상과 실제, 벌어지면 통계 문제. Buffers는 논리 I/O, 우리가 줄이려는 숫자. 그리고 access와 filter — access는 인덱스로 좁힌 거, filter는 읽고 버린 거. 이제 실제 플랜에서 이걸 읽어봅니다.

### [4] 실제 플랜을 읽어보자 — dept=80 AND salary=10000
- [코드] | Id | Operation                    | Name        | Starts | E-Rows | A-Rows | Buffers | ⏎ |  0 | SELECT STATEMENT             |             |      1 |        |      3 |       5 | ⏎ |* 1 |  TABLE ACCE
- [이 플랜에서 읽은 것] Starts 다 1(반복 없음). E-Rows 2 vs A-Rows 4 — 추정이 살짝 빗나감. Buffers 합 5가 논리 I/O. salary는 access인데 department_id는 filter → dept를 인덱스로 태우면 더 줄겠다는 판정이 여기서 나온다.

**발표 노트 →** 이제 실제 플랜입니다. dept=80 그리고 salary=10000을 돌린 거예요. Starts 보면 다 1이죠, 반복 없음. Id 2번 E-Rows 2인데 A-Rows 4 — 옵티마이저가 2행 예상했는데 실제 4행, 살짝 빗나갔어요. Buffers는 맨 위 5, 이 쿼리의 논리 I/O 총량입니다. 그리고 아래가 핵심이에요. salary는 access, 인덱스로 좁힌 거고 department_id는 filter, 읽고 버린 거예요. 그럼 자연스럽게 판정이 나오죠 — department_id를 filter 말고 access로, dept 인덱스를 태우면 더 줄지 않을까? 바로 다음에 확인합니다.

---

## ■ [02] 추적 도구

### [5] tkprof — SELECT는 Fetch 줄의 query(논리)·disk(물리)를 본다
- [코드] select * from hr.emp where employee_id = 100 ⏎ call     count   disk   query  current  rows ⏎ Fetch        2      9       2       0      1 ⏎ Row Source: TABLE ACCESS BY INDEX ROWID EMP (cr=2 pr=9) ⏎  
- [실제로 읽은 것] Fetch 줄만 본다. query=2가 논리 I/O(consistent gets), disk=9는 물리(캐시 flush 후 첫 read라 큼). Row Source의 cr=2가 그 query와 같은 값 — operation별로 쪼갠 것.

**발표 노트 →** 숫자를 어떻게 얻느냐, 첫 도구 tkprof입니다. employee_id=100을 돌린 실제 결과예요. SELECT니까 Fetch 줄을 봅니다. query가 2, 논리 읽기죠. disk가 9인데 이건 물리 읽기예요 — 아까 버퍼 캐시를 flush하고 처음 읽어서 물리가 크게 나온 겁니다. 튜닝에서 보는 건 query 2고요. 아래 Row Source의 cr=2가 바로 그 query랑 같은 값인데, operation별로 쪼개서 보여주는 거예요.

### [6] 10046 — level 12로 돌리면 bind 값과 wait까지 실제로 찍힌다
- [코드] alter session set events '10046 trace name context forever, level 12'; ⏎   -- level 12 = 4(bind) + 8(wait)  ← 레벨은 더한다 ⏎ exec :b_id := 50;   select * from hr.emp where department_id = :b_id; ⏎   BINDS:
- [레벨은 더한다 — 12 = 4 + 8] 1 기본 · 4 +bind · 8 +wait, 그리고 둘 다 원하면 더해서 12(=4+8). sql_trace로는 안 보이는 '무슨 값으로(bind)·무엇을 기다렸나(wait)'가 level 12에서 다 찍힌다. 느린 게 기다림일 때 필수.

**발표 노트 →** sql_trace만으론 부족할 때 10046을 씁니다. level 12로 돌린 실제 예예요. bind 변수 b_id에 50이 들어간 게 찍혔고, 기다린 이벤트로 db file sequential read랑 scattered read가 나왔죠. 이건 sql_trace로는 안 보이는 정보예요. 레벨은 1이 기본, 4가 bind 추가, 8이 wait 추가, 12가 둘 다입니다. 느린 원인이 읽기가 아니라 '기다림'일 때 이게 꼭 필요해요.

### [7] 버퍼 캐시 히트율은 높다고 좋은 게 아니다
- [코드] BCHR = (1 - disk / (query + current)) * 100 ⏎ -- 나쁜 계획:  query 100,000  disk 50  ->  BCHR 99.95% ⏎ -- 좋은 계획:  query    200   disk 20  ->  BCHR 90.9%  (논리 I/O 500배 적음)
- [히트율 높은 쪽이 오히려 500배 느리다] 실행계획이 나빠 논리 읽기가 폭증하면 BCHR은 오히려 100%에 가까워진다(위 나쁜 계획 99.95%). 디스크는 안 가고 캐시에서만 잔뜩 읽어서다. 지표는 히트율이 아니라 논리 I/O(Buffers) 절대량이다.

**발표 노트 →** 세 번째, 버퍼 캐시 히트율입니다. 공식은 논리 읽기 중 디스크 안 가고 캐시에서 찾은 비율이에요. 함정을 숫자로 보죠. 나쁜 계획은 논리 10만에 디스크 50이라 99.95%, 좋은 계획은 논리 200에 디스크 20이라 90.9%. 히트율은 나쁜 쪽이 높은데 실제 일량은 500배 많아요. 그러니 히트율 말고 논리 I/O 절대량을 보라는 겁니다.

---

## ■ [03] 접근 경로

### [8] 같은 쿼리라도 경로마다 Buffers가 갈린다 — 한눈에
- [다이어그램] (그림)
- [네 경로의 Buffers] 기본(EMP_SAL_IDX) 5, dept 인덱스 강제 4, and_equal 10(최악), index_combine 4. 옵티마이저 기본이 최선이 아니다 — 숫자로 고른다. 왜 and_equal이 10인지는 다음 장 실제 플랜에서.

**발표 노트 →** 그 숫자로 실제 판정을 해봅니다. 똑같은 쿼리를 네 경로로 돌려 Buffers를 비교한 거예요. 기본이 5, dept 인덱스 강제가 4, and_equal이 10으로 최악, index_combine이 4. 옵티마이저 기본이 최선이 아니었죠. 근데 and_equal이 왜 10이나 나오는지, 다음 장에서 실제 플랜으로 봅시다.

### [9] 왜 and_equal이 최악인가 — 실제 플랜을 보면 안다
- [코드] /*+ and_equal(e emp_dept_idx emp_sal_idx) */   ...   Buffers 10 ⏎ |* 1 |  TABLE ACCESS BY INDEX ROWID EMP           |    10 | ⏎ |  2 |   AND-EQUAL                                |     8 | ⏎ |* 3 |    
- [두 인덱스를 각각 훑어 합친다] and_equal은 EMP_SAL_IDX(5)와 EMP_DEPT_IDX(3)를 따로 스캔해 rowid를 교집합(AND-EQUAL 8)한 뒤 테이블 접근. 그래서 단일 인덱스(4~5)보다 오히려 많다. 실측 없이 힌트를 믿으면 이렇게 손해.

**발표 노트 →** and_equal이 왜 10인지 실제 플랜을 보면 딱 나와요. Id 3에서 EMP_SAL_IDX를 스캔해 Buffers 5, Id 4에서 EMP_DEPT_IDX를 스캔해 3, 이 둘의 rowid를 Id 2 AND-EQUAL에서 교집합하느라 8, 그리고 테이블 접근까지 10이에요. 인덱스 하나만 타면 4~5인데, 두 개를 각각 훑어 합치니까 오히려 더 많은 거죠. 그래서 힌트를 실측 없이 믿으면 안 됩니다 — 숫자가 말해줘요.

---

## ■ [04] 인덱스 종류

### [10] B*tree는 OLTP, bitmap은 DW — 정반대 상황용이다
- [표] 기준 | B*tree | bitmap  (4행)
- [고르는 기준] 값 종류가 적고 대량 조회하는 DW면 bitmap이 AND/OR을 싸게 처리한다(앞 index_combine=4). 동시 DML 잦은 OLTP엔 독 — 다음 장에서 실제로 본다.

**발표 노트 →** 인덱스 종류입니다. B*tree랑 bitmap은 정반대 도구예요. B*tree는 유일하거나 종류 많은 컬럼, 동시 수정 많은 OLTP. bitmap은 성별처럼 값 몇 개 없는 컬럼, 대량 조회 DW. bitmap은 AND OR을 싸게 처리하지만 DML 비용이 커요. 그게 왜 문제인지 다음 장에서 실제 잠금을 봅니다.

### [11] bitmap은 한 값이 여러 행을 잠근다 — 구조부터
- [다이어그램] (그림)
- [한 조각이 범위를 덮는다] bitmap은 키 하나(gender=m)가 그 값을 가진 여러 행을 한 조각으로 덮는다. A가 그 조각을 잠그면 같은 m을 넣는 C는 다른 행이어도 대기.

**발표 노트 →** bitmap의 최대 함정, 구조부터 봅시다. bitmap은 키 하나가 여러 행을 한 덩어리로 덮어요. A가 gender=m을 넣으면서 그 m 덩어리를 잠그면, C가 다른 행이지만 역시 m을 넣으려 하면 같은 덩어리라 기다려야 합니다. 이제 실제 세션에서 이게 어떻게 보이는지 봅시다.

### [12] 실제로 세션이 막힌다 — enq: TX - row lock contention
- [코드] -- 세션1: insert ...values(1,'m','y')   세션2: insert ...values(3,'m','y') ⏎ SQL> select sid, blocking_session, event from v$session where event like '%TX%'; ⏎  SID  BLOCKING_SESSION  EVENT ⏎  286  255   
- [다른 행인데 막혔다] 286은 (3,'m','y'), 255는 (1,'m','y') — 행은 다르지만 gender='m'이 같다. 같은 bitmap 조각을 두고 286이 255에 막혔다. B*tree라면 안 막혔을 경합이다. 그래서 bitmap은 OLTP 금지.

**발표 노트 →** 실제로 세션이 막히는 걸 봅시다. 세션1이 gender m인 1번 행을 넣고 커밋 안 한 상태에서, 세션2가 역시 m인 3번 행을 넣으려 해요. v$session을 보면 286번 세션이 255번한테 막혀서 enq: TX - row lock contention으로 대기 중이죠. 1번 행이랑 3번 행은 완전히 다른 행인데, gender가 둘 다 m이라 같은 bitmap 조각을 건드려서 막힌 거예요. B*tree였으면 안 막혔을 경합입니다. 그래서 bitmap은 동시 수정 많은 OLTP엔 절대 안 씁니다. 진단은 68일차에 배운 blocking_session 그대로고요.

---

## ■ [05] 조인

### [13] 조인은 건수로 방법을, 힌트로 순서를 정한다
- [표] 구분 | 내용 | 힌트  (4행)
- [방법과 순서는 다른 축] 바깥이 1행이면 순서를 바꿔도 Buffers는 같다. 바깥이 여러 행이면 누가 driving이냐로 반복 횟수가 달라진다 — 곧 Starts로 본다.

**발표 노트 →** 조인입니다. 방법은 셋 — 건수 적으면 Nested Loop(use_nl), 많으면 Sort Merge나 Hash. 그리고 방법과 순서는 다른 얘기예요. 순서는 ordered나 leading으로 정합니다. 바깥이 1행이면 순서 바꿔도 Buffers가 같은데, 바깥이 여러 행이면 누가 먼저 도느냐로 반복이 확 달라져요. 그걸 Starts로 봅니다.

### [14] NL은 바깥 각 행마다 안쪽을 반복한다 — 구조
- [다이어그램] (그림)
- [바깥(driving)이 반복을 정한다] 바깥 EMPLOYEES의 각 행마다 안쪽 DEPARTMENTS를 인덱스로 조회해 붙인다. 바깥이 작을수록 안쪽 반복이 적어 NL이 싸다. driven(안쪽)엔 조인키 인덱스가 있어야 반복이 싸다. 실제 플랜 두 개로 확인한다.

**발표 노트 →** NL이 실제로 어떻게 도는지, 구조부터요. 바깥 테이블이 driving이고, 그 각 행마다 안쪽을 반복 조회합니다. 바깥이 작을수록 안쪽이 덜 돌아서 싸요. 이제 실제 플랜 두 개로 확인합니다 — 바깥이 1행일 때랑 여러 행일 때.

### [15] 실제 ① 바깥이 1행 — employee_id=100
- [코드] |  1 |  NESTED LOOPS                               |    4 |  Starts ⏎ |  2 |   TABLE ACCESS BY INDEX ROWID EMPLOYEES     |    2 |    1   << outer/driving ⏎ |* 3 |    INDEX UNIQUE SCAN EMP_EMP_ID_PK   
- [한 번씩만 돈다 · |* = Predicate 있음] Starts 다 1, 순서 3->2->5->4->1, Buffers 4. |* 3·5는 아래 Predicate에 조건 있다는 표시 — 3=access(EMP_ID=100), 5=access(조인키). Id5 access(조인키)가 곧 driven이 인덱스로 붙은 증거다.

**발표 노트 →** 첫 번째, 바깥이 1행인 경우. employee_id=100이니 바깥 EMPLOYEES가 한 행, 안쪽도 한 번만. Starts 다 1이죠. 순서는 3-2-5-4-1, Buffers 4. 그리고 Id 옆의 별표 보이시죠? 아래 Predicate에 조건 있다는 표시예요. Id5가 access, 그것도 조인키로 access했다는 건 driven인 DEPARTMENTS를 인덱스로 붙였다는 증거입니다. driven엔 인덱스가 있어야 한다는 게 여기서 확인돼요.

### [16] 실제 ② 바깥이 여러 행 — location_id=1400에서 Starts가 반복을 드러낸다
- [코드] -- location 1400 → 부서 60 (1행) → 그 부서 사원 5명 ⏎ -- 이번엔 DEPARTMENTS가 바깥(driving): 조건이 부서를 먼저 거름 ⏎ | Id | Operation                          | Buffers | Starts | A-Rows | ⏎ |  3 |   DEPARTMENTS (BY INDEX R
- [바깥은 고정이 아니다 — 조건이 driving을 정한다] location 1400은 부서를 먼저 1행(60번)으로 걸러 이번엔 DEPARTMENTS가 바깥. 그 부서 사원이 5명이라 안쪽 EMPLOYEES가 5번 반복 = Starts 5. ①(emp_id=100)은 사원이 바깥이었는데 여기선 뒤집혔다 — 먼저 걸러지는 쪽이 driving이고, 그 건수가 안쪽 반복(Starts)을 정한다. 실행순서가 3→2→5→4→5→4…→1로 길어지는 건 이 반복 때문이다.

**발표 노트 →** 두 번째가 학생분이 어렵다고 표시한 그 부분입니다. 천천히 갈게요. 이번엔 location_id=1400으로 조회해요. 1400 위치엔 부서가 60번 하나 있고, 그 60번 부서에 사원이 5명 있습니다. 그러니까 바깥이 5행인 거예요. 플랜에서 Id 6, 사원 행을 읽는 operation의 Starts를 보세요. 5로 찍혀 있죠. 바깥 부서에서 나온 사원이 5명이라 사원 행 읽기를 5번 반복했다는 뜻이에요. 그래서 실행 순서가 3-2-5-4에서 끝나지 않고 5-4-5-4 이렇게 다섯 번 반복돼서 3-2-5-4-5-4...-1로 길어지는 겁니다. 어렵게 느껴졌던 그 긴 순서가, 사실은 Starts 5, 다섯 번 반복이라는 한 숫자로 설명돼요. 그러니까 실행 순서가 헷갈리면 Starts부터 보세요. 안쪽이 몇 번 돌았는지가 거기 다 있습니다.

---

## ■ [06] 빈틈 & 궁금한 점

### [17] 여기서 남는 질문 — 확인하고 넘어가면 좋은 것들
- · 옵티마이저가 5를 골랐는데 dept 힌트가 4였다 → E-Rows≪A-Rows가 근거, 통계 추정 어긋남 의심 (확인 권장) / and_equal은 옛 방식 → 요즘 옵티마이저는 거의 안 쓰고 index_combine이 대체 / location_id=1400을 optimizer_features 옛 버전으로 돌리면 plan이 바뀐다 → 버전별 NL prefetch 차이 (참고만) / 실행순서가 길고 헷갈리면 항상 Starts부터 → 안쪽 반복 횟수가 거기 있다

**발표 노트 →** 마지막으로 질문 몇 개. 첫째, 옵티마이저가 5를 골랐는데 우리가 강제한 4가 나았죠? E-Rows와 A-Rows가 벌어진 걸 보면 통계 추정이 어긋난 것 같아요, 확인해볼 만합니다. 둘째, and_equal은 옛 방식이라 요즘은 index_combine이 대체해요. 셋째, location_id=1400을 옛 옵티마이저 버전으로 돌리면 plan이 바뀌는데 버전 차이라 참고만 하세요. 넷째, 실행순서가 길고 헷갈리면 항상 Starts부터 보세요 — 안쪽이 몇 번 돌았는지가 거기 다 있습니다. 노트 밖 얘기는 확인 권장으로 표시해뒀어요.
