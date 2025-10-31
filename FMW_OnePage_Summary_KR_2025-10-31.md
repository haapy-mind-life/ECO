# FMW 원페이지 요약 (인쇄용) — 2025-10-31
**발표자:** 프로젝트 리더(본인) · **청중:** 운영진 3명(BE/DevOps, FE/Streamlit, 리더)

---

## 0) 이 문서 사용법
- **3분 버전**: 아래 *3분 토크 스크립트*만 읽어도 전체 핵심이 전달됩니다.  
- **5분 버전**: *5분 토크 스크립트*를 사용해 조금 더 맥락과 수치를 설명합니다.  
- **추가 자료**: 회의 후 API/데이터모델 세부 문서는 별도 배포.

---

## 1) 지금 왜 필요한가 (비즈니스 배경)
- **Time-to-Data 제거**: 정책/피처 상태를 한 곳에서 즉시 확인(SSOT).  
- **속도·신뢰·운영효율**: 스냅샷-우선으로 빠르고, 장애 시에도 마지막 스냅샷으로 서비스 지속.  
- **파일럿 목표(20명)**: 30일 안에 *가치 증명* (사용성·성능·신선도 지표로 검증).

---

## 2) 무엇을 제공하나 (Phase‑1 범위)
- **뷰어(UI, Streamlit)**: `records.csv`, `runs_summary.json`을 로컬에서 바로 로딩.  
- **API(Django)**  
  - 공개 읽기(v1): `GET /api/v1/features`, `GET /api/v1/features/{feature_group}` (기본 CSV, `?format=json` 선택)  
  - 운영(dev): `POST /api/dev/sync/run`, `GET /api/dev/runs/summary`(1/7/14/30일 오버뷰), `GET /api/dev/changes`(선택)  
- **보안**: Nginx IP Allowlist + 앱 루프백 바인딩(127.0.0.1).  
- **DB**: Postgres(운영 기본), `identity_hash UNIQUE`로 멱등 업서트.  
- **운영**: Windows 서비스(NSSM) 등록, 표준 배치 스크립트(setup/start/stop/reset).

---

## 3) 어떻게 동작하나 (아키텍처 & 파이프라인)
**Nginx → Django(API/ETL) & Streamlit(Viewer) + Postgres**
1. **Sync** 수집  
2. **정규화**(별칭→표준명), **MCC/MNC 보강**(region/country/operator 자동 추가)  
3. **Upsert → `features`**(현재 상태)  
4. **`changes` 기록**(C/U/D diff)  
5. **`daily_counts` 집계**(Home KPI용)  
6. **스냅샷 파일 교체**(임시 파일 생성 → 원자적 rename)

---

## 4) 데이터 모델(핵심)
- **features**: 현재 원장(표준화 필드 + `identity_hash UNIQUE`)  
- **changes**: 모든 변경 이력(before/after, 이유, run_id, 시각)  
- **runs**: 싱크 실행 로그(시작/종료/상태/건수)  
- **daily_counts**: 일별 C/U/D/errors 집계(1/7/14/30)  
- **name_map**: 별칭↔표준명(케이싱/공백 포함)  
- **mcc_mnc_map**: MCC/MNC → 지역/국가/운영자(유효기간 포함 가능)

---

## 5) 성공 지표(KPI/NFR)
- **Adoption**: 주간활성(WAU) ≥ 70%(20명 파일럿)  
- **성능**: Home < 1s, 주요 조회 P95 < 5s, v1 API P95 < 3s  
- **신선도**: 일일 동기화 성공률 ≥ 98%  
- **운영성**: 일상 점검 ≤ 30분/일

---

## 6) 리스크 & 대응
- 대용량 CSV 로드 → 컬럼 축소/지연 로딩/페이지네이션, 캐시  
- DB 동시성 → Postgres + 인덱스/트랜잭션 튜닝  
- 스냅샷 교체 중 정합성 → 임시 파일 + **원자적 교체**  
- DEV API 남용 → Allowlist + (선택) API 키/SSO(Phase‑2)  
- 재해 복구 → 야간 `pg_dump` + 스냅샷 복제 + 복구 리허설

---

## 7) 30‑60‑90 실행 계획
- **30일(MVP)**: features+runs, v1 2종 / dev 1~2종, Home/Overview/Dev 탭 완성  
- **60일**: changes UI·Export, MCC/MNC 맵 검증, 백업 자동화  
- **90일(Phase‑2)**: SSO/RBAC 검토, 규모 확장(사용자↑ 시 UI 대체 고려)

---

## A. 3분 토크 스크립트 (그대로 읽기용)
**[0:00–0:20] 오프닝**  
“핵심은 *데이터를 빠르고 믿을 수 있게 한 곳에서 본다*입니다. 실시간 쿼리 대신 **스냅샷-우선**으로 UI를 구성해 속도와 안정성을 동시에 잡았습니다.”

**[0:20–1:10] 무엇을 제공?**  
“Phase‑1은 내부 20명 파일럿입니다. Streamlit은 `records.csv`와 `runs_summary.json`을 바로 읽습니다. API는 단순합니다. 읽기 전용 v1 두 개(`features`, `features/{group}`), 운영용 dev 두세 개(`sync/run`, `runs/summary`, 선택 `changes`). 보안은 Nginx 허용 IP와 앱 루프백으로 막습니다.”

**[1:10–2:10] 어떻게 동작?**  
“Sync→정규화(MCC/MNC 보강)→`features` 업서트→`changes` 이력→`daily_counts` 집계→스냅샷 교체 순서입니다. 스냅샷은 원자적으로 교체돼서 보는 중에도 안전합니다.”

**[2:10–2:40] 지표와 리스크**  
“Home < 1초, 조회 P95 < 5초, 동기화 성공률 98%가 목표입니다. 대용량 CSV·DB 동시성·스냅샷 교체 같은 리스크는 페이징·Postgres·원자적 교체로 대응합니다.”

**[2:40–3:00] 오늘 결정**  
“**Postgres 사용**, **API 표면 확정**, **Windows 서비스 등록**, **KPI 승인**—이 네 가지만 합의되면 바로 배포 캘린더에 올리겠습니다.”

---

## B. 5분 토크 스크립트 (맥락·수치 포함)
**[0:00–0:20] Hook**: “팀이 *어제 기준 상태*를 1초 내 확인하고, 장애 시에도 마지막 유효 상태로 계속 보고 싶다—이게 목표입니다.”  
**[0:20–0:50] Pain**: “문서와 시스템이 흩어져 탐색 비용이 크고, 실시간 쿼리는 느리고 불안정했습니다.”  
**[0:50–1:30] Solution**: “**스냅샷‑우선** 전략으로 UI는 사전 계산 파일을 읽습니다. 백엔드는 분리되어 장애 전파가 되지 않습니다. 보안은 Nginx Allowlist + 루프백 바인딩입니다.”  
**[1:30–2:20] Architecture & Data**: “Sync→정규화→업서트→이력→집계→스냅샷. `features/changes/runs/daily_counts/name_map/mcc_mnc_map`로 역할을 분리했고, MCC/MNC가 들어오면 지역·국가·운영자를 자동 보강합니다.”  
**[2:20–3:00] API**: “v1 두 개로 조회를 단순화했고, dev API로 동기화와 오버뷰를 봅니다. 기본 CSV, 필요 시 `?format=json`으로 개발 친화성을 유지합니다.”  
**[3:00–3:40] KPIs & Risks**: “Home<1s, P95<5s, Sync≥98%, WAU≥70%. 대용량은 페이징/지연 로딩, 동시성은 Postgres, 파일 교체는 원자적 처리로 안전하게 갑니다.”  
**[3:40–4:20] 30‑60‑90**: “30일 MVP(뷰/주요 API), 60일 changes UI·백업 자동화, 90일 SSO/RBAC와 스케일 전략 검토.”  
**[4:20–5:00] Decisions**: “오늘 ①Postgres ②API 표면 ③Windows 서비스 ④KPI를 승인받고 바로 실행에 들어가겠습니다.”

---

## C. SW 전문가 리뷰(요약)
- **강점**: 스냅샷‑우선으로 UX/복원력↑, 데이터 모델 책임 분리로 성능·감사 용이, API 표면 최소화로 유지보수성↑.  
- **보완**: (1) CSV가 커지면 페이지·컬럼 축소 필요, (2) DEV API는 Allowlist+토큰 고려, (3) 스냅샷 파일 교체는 원자성 필수.  
- **즉시 액션**: Postgres 고정, NSSM 서비스 등록, 야간 백업 자동화, 성능 PoC(최대 레코드 기준) 진행.

---

## D. 발표자 체크리스트(회의 전 5분)
- [ ] 데모 순서: Home → Overview → Dev(sync)  
- [ ] 수치 한 줄: “Home<1s / P95<5s / Sync≥98% / WAU≥70%”  
- [ ] 의사결정 4가지 확인: Postgres · API 표면 · Windows 서비스 · KPI 승인  
- [ ] 리스크 3가지 대비: CSV·동시성·스냅샷 교체