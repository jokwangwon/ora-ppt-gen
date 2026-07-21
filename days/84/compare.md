# 84일차 복습 시트

> 오늘 하루를 한 장으로 — 축·개념·명령어·요약. 막히는 개념은 옆의 [문서 §] 링크로 바로 이동해 다시 읽고, 마지막에 허브에서 문제로 마무리.

---

## [오늘의 축]

> **튜닝의 마지막 질문은 '무엇을 메모리에 남길까' — 자주 쓰는 건 KEEP으로 붙잡고, 한번 훑을 건 RECYCLE로 격리하고, 나머지는 자동 관리(ASMM·AMM)에 맡긴다. 그리고 오늘 RAC 설치가 시작됐다.**

버퍼 캐시 풀(DEFAULT/KEEP/RECYCLE/nK) + Redo Log Buffer + 메모리 자동화 3세대(자동 PGA 9i→ASMM 10g→AMM 11g)로 SQL 튜닝편 메모리 무대 완료. 후반 RAC 설치 개막(인프라).

## [개념 제목] (수업 등장 순)

1. **Data Buffer Cache** — 블록 복사본 저장, 물리 I/O 최소화, 공유·동적 크기 · [문서 §16.1](assets/sql_tuning.html#mem)
2. **KEEP 풀** — 빈도 높고 작은 테이블 붙잡아 둠(db_keep_cache_size) · [문서 §16.1](assets/sql_tuning.html#mem)
3. **RECYCLE 풀** — 빈도 낮고 대용량 격리해 DEFAULT 보호(db_recycle_cache_size) · [문서 §16.1](assets/sql_tuning.html#mem)
4. **nK 풀 & nonstandard 블록** — 표준(8K) 외 블록은 db_nk_cache_size 먼저 · [문서 §16.2](assets/sql_tuning.html#mem)
5. **buffer_pool 지정** — storage(buffer_pool keep) 세그먼트 꼬리표(테이블·인덱스 개별) · [문서 §16.2](assets/sql_tuning.html#mem)
6. **Redo Log Buffer** — 변경 기록·목적=복구·순수 select 제외(for update는 포함) · [문서 §16.3](assets/sql_tuning.html#mem)
7. **자동 PGA(9i)** — pga_aggregate_target, 작업 공간만 · [문서 §16.4](assets/sql_tuning.html#mem)
8. **ASMM(10g)** — sga_target, SGA 자동 구성요소, mman · [문서 §16.4](assets/sql_tuning.html#mem)
9. **AMM(11g)** — memory_target, SGA+PGA 통째(설정 시 sga/pga target 0) · [문서 §16.4](assets/sql_tuning.html#mem)
10. **자동에서 빠지는 것** — keep/recycle/nK cache·log_buffer는 수동 · [문서 §16.4](assets/sql_tuning.html#mem)

## [실습 명령어 정리] (실행 순서 + 결과 요지)

| # | 명령 | 결과 요지 |
|---|------|-----------|
| 1 | `show parameter pga` | pga_aggregate_limit 2G · target 0 (§15 복습) |
| 2 | `v$sgainfo` / `v$buffer_pool` | Buffer Cache Size·DEFAULT 8192 37202 buffers |
| 3 | `alter system set db_keep_cache_size = 16m scope=both` | **KEEP 1958** 생김 — DEFAULT 37202→**35244**(1958 떼옴) |
| 4 | `alter table hr.employees storage(buffer_pool keep)` | dba_tables.buffer_pool KEEP — 데이터 이동 아니라 꼬리표 |
| 5 | `alter index hr.emp_emp_id_pk storage(buffer_pool keep)` | 인덱스도 개별 지정 → default로 되돌림 |
| 6 | `alter system set db_recycle_cache_size = 16m` + `storage(buffer_pool recycle)` | RECYCLE 풀·테이블 지정 |
| 7 | `alter system set db_4k_cache_size = 16m` | 4K 캐시 먼저 열기(표준 db_block_size 8K와 별개) |
| 8 | `create tablespace oltp_tbs … blocksize 4k …` | 4K 테이블스페이스 — dba_tablespaces block_size 4096 |
| 9 | `create table hr.oltp_emp tablespace oltp_tbs as select…` | employees 8블록(8K) → oltp_emp 세그먼트 256블록(uniform 1m) |
| 10 | Redo: redo entry 생성 SQL | DML·DDL·select for update ○ / 순수 select ✗ |
| 11 | `log_buffer` | static parameter(scope=spfile+재기동) |
| 12 | `show parameter sga_target` / `sga_max_size` | ASMM: sga_target ≤ sga_max_size, 운영 중 조정 |
| 13 | `! ps -ef | grep ora_mman` | **ora_mman** 프로세스 — ASMM의 memory advisor |
| 14 | `v$sga_dynamic_components` / `v$memory_dynamic_components` | ASMM(10g) / AMM(11g) 확인 뷰 |
| 15 | `show parameter memory_target` | AMM: memory_target 1472M → sga_target·pga_target 0 |

## [5줄 요약]

1. **버퍼 캐시는 풀로 나뉜다** — DEFAULT 기본, KEEP(자주 쓰는 작은 걸 붙잡음), RECYCLE(대용량을 격리해 DEFAULT 보호), nK(다른 블록 크기). KEEP/RECYCLE은 정반대 목적이지만 둘 다 DEFAULT LRU를 지킨다.
2. **풀 지정은 세그먼트 꼬리표** — db_..._cache_size로 풀을 열면 DEFAULT에서 buffers를 떼오고, storage(buffer_pool keep)로 테이블·인덱스가 살 곳을 정한다(데이터 이동 아님).
3. **nonstandard 블록은 캐시부터** — 4K 테이블스페이스는 db_4k_cache_size를 먼저 열어야(버퍼 캐시가 블록 크기별로 분리). 작은 블록=OLTP, 큰 블록=DSS 유리.
4. **Redo는 변경만 남긴다** — 목적은 복구. DML·DDL·select for update가 redo entry를 만들고, 순수 select은 바꾼 게 없어 안 만든다. log_buffer는 static(재기동).
5. **자동화는 3세대** — 자동 PGA(9i, pga_aggregate_target)→ASMM(10g, sga_target)→AMM(11g, memory_target, SGA+PGA 통째). 단 keep/recycle/nK cache·log_buffer는 DBA가 의도적으로 격리한 것이라 자동에서 빠져 수동.

## [건너뛴 것 — 매뉴얼 대비 / RAC]

| 안 다룬 것 | 추정 이유 | 공부하러 가기 |
|-----------|----------|--------------|
| RAC 설치 상세(grid·ASM 구성) | 인프라 실습 — 본 문서 범위 밖 | 아래 RAC 설치 요지 · 이미지 압축폴더 |
| v$sga_resize_ops(자동 조정 이력) | 튜닝 심화 | [매뉴얼 § Memory Architecture](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/memory-architecture.html) |
| 블록 크기별 성능 벤치 | 실측 필요 | 홈랩 — 4K vs 8K vs 16K 대량 스캔 비교 |
| memory advisor 뷰(v$pga/sga_target_advice) | 튜닝 심화 | 위 매뉴얼 |

## RAC 설치 요지 (인프라 — 문서 범위 밖, 순서 참고용)

- **IP 체계**: Public(rac1 .190 / rac2 .191) · Private 인터커넥트(rac1-priv .55.190 / rac2-priv .55.191) · VIP(.192/.193) · SCAN(rac-scan .194, 클라이언트 접속)
- **패키지**: oracle-database-preinstall-19c · oracleasm-support · kmod-oracleasm
- **OS 준비**: /etc/hosts(public/private/vip/scan) · limits.conf(nofile·nproc·stack·memlock) · firewalld 중지 · ntpd(시간 동기)
- **유저·그룹**: oracle(oinstall/dba/oper/…) + asmadmin(54331)·asmdba(54332)·asmoper(54333) 추가
- **디렉토리·환경**: /u01/app/{oracle,oraInventory,19.0.0/grid,…} · .bash_profile(ORACLE_HOME·GRID_HOME·SID) · .grid_env(+ASM1)·.db_env(racdb1) 분리
- **복제**: rac1 종료→rac2 복제(새 MAC)→IP·hostname·환경변수(rac2/+ASM2/racdb2) 수정
- 홈랩: 각 단계의 이유 — private=노드 간 인터커넥트, SCAN=단일 접속점, ASM 그룹=스토리지 관리

## 복습 동선 (10분)

1. **[오늘의 축]** 한 줄을 소리 내어 설명해보기 — KEEP/RECYCLE의 정반대 목적, 자동화 3세대
2. **[개념 제목]** 을 훑으며 설명 안 되는 것만 [문서 §] 링크로 이동해 그 부분 재독
3. **[명령어 표]** 의 결과(37202→35244 / redo 생성 SQL / 9i·10g·11g 파라미터)를 가리고 떠올려보기
4. 마무리 — [허브에서 84일차 문제 풀기](assets/study_hub_full.html) (날짜칩 84 필터)
