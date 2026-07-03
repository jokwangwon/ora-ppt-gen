# 74일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **조인 3형제 완성 — NL의 반복(random access)이 부담이면 정렬(Sort Merge)로, 정렬이 부담이면 해시(Hash)로. 판정은 Buffers + 메모리(Used-Mem)까지.**

수업이 SM 개념→실측, Hash 개념→ora_hash 실습→3테이블, outer join 순서 규칙, index join으로 이어짐 — 전부 "NL 다음 선택지"의 이야기.

## [개념 제목] (수업 등장 순)

1. **Sort Merge Join** — 양쪽 정렬 → merge, 건수 많을 때·sort 부하 감수, PGA sort area · [문서 §7.9](assets/sql_tuning.html#join)
2. **인덱스가 정렬을 대체** — dept 쪽엔 SORT JOIN이 없음 (INDEX FULL SCAN 순서 재활용) · [문서 §7.9](assets/sql_tuning.html#join)
3. **SORT JOIN Starts=27의 비밀** — 정렬은 1번, 탐색만 27번(정렬 재사용) · [문서 §7.9](assets/sql_tuning.html#join)
4. **OMem · 1Mem · Used-Mem · Used-Tmp** — 정렬 메모리 읽는 법 · [문서 §7.9](assets/sql_tuning.html#join)
5. **Hash Join** — 작은 쪽 build(해시 테이블) + 큰 쪽 probe, = 조건 전용, 키 중복 적을수록 유리 · [문서 §7.10](assets/sql_tuning.html#join)
6. **ora_hash 실습** — 해시 버킷을 눈으로 (dept 60 → 버킷 1, emp 60번 사원들도 버킷 1로) · [문서 §7.10](assets/sql_tuning.html#join)
7. **swap_join_inputs** — 옵티마이저가 build/probe를 맞바꿈, no_swap_join_inputs로 고정 · [문서 §7.11](assets/sql_tuning.html#join)
8. **outer join 순서 규칙** — (+) 없는 쪽이 항상 선행(build), leading보다 우선 · [문서 §7.11](assets/sql_tuning.html#join)
9. **오타 사례 2탄** — gather_plan_statistcs → 플랜 Note에 통계 경고 · [문서 §7.11](assets/sql_tuning.html#join)
10. **Index Join** — 한 테이블의 여러 인덱스를 rowid로 해시 조인, SELECT 컬럼 전부 인덱스에 있을 때만 · [문서 §7.12](assets/sql_tuning.html#join)
11. **3형제 선택 기준** — 건수·등호·인덱스·메모리 · [문서 §7.13](assets/sql_tuning.html#join)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | NL 복습: `leading(d,e) use_nl(e)` | batched 모양, Buffers **35** · full 강제(10.1)면 **95** |
| 2 | SM 기본: 힌트 없이 실행 | MERGE JOIN — dept는 **INDEX FULL SCAN**(정렬 대체), emp만 SORT JOIN(Starts 27·Used-Mem 16K), Buffers **15** |
| 3 | SM 강제: `use_merge(e) full(e) full(d)` | 양쪽 SORT JOIN, Buffers **5** (정렬 비용은 Buffers 밖!) |
| 4 | SM 3테이블: `leading(l,d,e) use_merge(d) use_merge(e)` | merge 중첩 — 중간 결과를 다시 SORT JOIN, Buffers **7** |
| 5 | Hash: `leading(d,e) use_hash(e)` | DEPT build(2) + EMP probe(10), Buffers **13** · Used-Mem 1.5M |
| 6 | `ora_hash(department_id,10)` 조회 | 버킷 분류를 눈으로 — dept 60=버킷1, emp 60번 사원들도 버킷1 |
| 7 | Hash 3테이블: `leading(d,e,l) use_hash(e) use_hash(l)` | 옵티마이저가 **LOC을 build로 승격**(swap) — `no_swap_join_inputs(l)`로 원위치 |
| 8 | outer: `where e.department_id = d.department_id(+)` | `leading(d,e)` **무시** — (+) 없는 EMP가 선행, HASH JOIN OUTER, **107행** |
| 9 | `swap_join_inputs(d)` | HASH JOIN **RIGHT OUTER** — DEPT를 build로 |
| 10 | 3테이블 + 인덱스 있는 상태 재실행 | **index$_join$** 등장 — LOC_CITY_IDX ⋈ LOC_IDX 를 rowid로 해시 조인(테이블 안 감) |

## [5줄 요약]

1. **Sort Merge = 양쪽 정렬 후 지퍼처럼 병합** — 건수 많고 random access가 부담일 때. 정렬은 PGA에서.
2. **인덱스가 이미 정렬이면 SORT JOIN이 사라진다** — dept의 INDEX FULL SCAN이 정렬을 대체. SORT JOIN Starts가 커도 **정렬은 1번**(재사용).
3. **Hash = 작은 쪽을 버킷에 담고(build) 큰 쪽이 찾아간다(probe)** — = 조인 전용, 키 중복 적을수록 유리.
4. **outer join은 (+) 없는 쪽이 무조건 선행** — leading보다 우선하는 문법 규칙. 뒤집으려면 swap_join_inputs.
5. **Buffers만으론 판정 불완전** — SM full이 5로 최저지만 정렬(Used-Mem)·해시(hash area) 비용은 Buffers 밖에 있다. 메모리 컬럼까지 같이 본다.

## [건너뛴 것 — 매뉴얼 대비]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| Used-Tmp가 실제로 뜨는 상황(대용량 정렬) | ⑤ 실습 데이터가 작음 | [매뉴얼(Concepts)](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/) · 대용량 실습 때 확인 |
| hash 충돌이 성능에 미치는 영향 | ④ 내부 심화 | [문서 §7.10](assets/sql_tuning.html#join) 개념만 |
| adaptive plan (outer join 플랜의 Note) | ① 뒤 차시 추정 | ? → 강사 질문 |

---

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — 3형제가 각각 무엇의 해결책인지
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과 숫자(35·15·5·13 / 107행)를 가리고 떠올려보기 — 특히 "SM이 5인데 왜 최고가 아닌가?"
4. 마무리 — [허브에서 74일차 문제 풀기](assets/study_hub_full.html) (날짜칩 74 필터)
