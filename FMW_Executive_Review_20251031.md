# FMW Executive Review — Leadership Meeting Pack
**Date:** 2025-10-31  
**Presenter:** Project Lead (You)  
**Audience:** 3-person leadership (Ops/BE-DevOps, FE/Streamlit, Project Lead)

---

## 0) How to use this pack (20–30 min)
- **1–3 min** Executive Overview (Sections 1–2)  
- **7–10 min** Core Design & Data/API (Sections 3–5)  
- **5–7 min** KPIs, Risks, Decisions (Sections 6–8)  
- **5–7 min** Roadmap & Q&A (Sections 9–10)  
> **Speaker Tip:** 각 섹션의 *Speaker Notes*를 그대로 읽으셔도 자연스럽게 진행됩니다.

---

## 1) Purpose & Context (Why now)
- **Mission:** 내부 사용자의 *time-to-data*를 제거, 정책/피처 상태의 **SSOT** 구축
- **Scope (Phase‑1/20 users):** 읽기 전용 **Snapshot‑First** UI, 내부망, IP Allowlist 보안
- **Outcome:** 속도/신뢰/운영효율을 KPI로 1개월 내 **가치 증명(Proof of Value)**

**Speaker Notes**  
“오늘은 왜/무엇/어떻게를 20분에 정리하고, 당장 실행할 결정을 받겠습니다.”

---

## 2) One‑page Architecture
**Pattern:** Snapshot‑First + Dual‑Layer Security + Idempotent Upsert

```
[Users(20) in LAN]
        │
   (IP Allowlist)
      Nginx
   ┌───────────────┬───────────────────────────────┐
   │ /streamlit/*  │   /(api/*)                    │
   │ → 127.0.0.1:8501  → 127.0.0.1:8000            │
   └───────────────┴───────────────────────────────┘
        │                          │
   Streamlit (UI)            Django REST + ETL
        │                          │
        └─────reads snapshots──────┼────→ Postgres (UNIQUE identity_hash)
                                   │
 ETL: Sync → Normalize/Enrich(MCC/MNC) → Upsert(features)
      → Write(changes) → Aggregate(daily_counts) → Snapshot Write
```

**Speaker Notes**  
“핵심은 *스냅샷 우선*으로 빠르고 안정적으로 보여주고, 백엔드 장애와 분리합니다. 보안은 Nginx와 루프백 이중 경계입니다.”

---

## 3) Data Model (responsibility split)
- **features**: 현재 상태 원장 (정규화, `identity_hash` UNIQUE)
- **changes**: C/U/D 이력(`before_json`, `after_json`, `changed_at`, `run_id`)
- **runs**: 싱크 실행 로그(시작/종료/상태/건수)
- **daily_counts**: 일별 C/U/D/errors 집계 (Home 카드용)
- **name_map**: 별칭 → 표준명
- **mcc_mnc_map**: MCC/MNC → region/country/operator 보강 (유효기간)

**Speaker Notes**  
“역할을 분리해 단순·확장·감사 대응을 모두 잡습니다.”

---

## 4) API Surface (kept small & clear)
### Public v1 (read‑only; CSV default, `?format=json` optional)
- `GET /api/v1/features` — 필터 가능한 전체 스냅샷
- `GET /api/v1/features/{feature_group}` — 그룹별 슬라이스
- (대용량 다운로드는 `?download=1` 옵션으로 노출)

### DEV (ops/internal; allowlist + optional API key)
- `POST /api/dev/sync/run` — ETL 비동기 트리거
- `GET /api/dev/runs/summary?days=1|7|14|30&yesterday=bool` — 오버뷰 집계
- `GET /api/dev/changes` , `GET /api/dev/changes/diff` — 이력 조회/비교
- `GET/PUT /api/dev/slsi/allow_list` — 내부 허용리스트 관리(옵션)

**Speaker Notes**  
“API는 다섯 손가락 안에 유지합니다. 운영 API는 내부망 전용으로 안전하게.”

---

## 5) MCC/MNC enrichment (searchability)
- Sync 후, features에 MCC/MNC가 있으면 `mcc_mnc_map`으로 **region/country/operator 자동 보강**
- UI 필터/검색의 실사용성 ↑, 운영자 확인 속도 ↑

**Speaker Notes**  
“사용자 입장에선 MCC/MNC보다 지역·국가·운영자가 바로 보이는 게 핵심 가치입니다.”

---

## 6) KPIs & NFRs (Phase‑1 targets)
- **Perf:** Home avg < **1s** / 주요 조회 P95 < **5s** / v1 API P95 < **3s**
- **Freshness:** 일일 동기화 성공률 **≥ 98%**
- **Adoption:** WAU **≥ 70%** (20명)
- **Ops burden:** 일상 점검 **≤ 30분/일** (3명)
- **Security:** 비허용 IP 접근 0, DEV API 외부 접근 0

**Speaker Notes**  
“숫자로 성패를 가르겠습니다. 미달 시 즉시 설계 조정합니다.”

---

## 7) Top Risks & Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Large CSV load | 느린 UX | Snapshot partitioning, column pruning, lazy paging, cache |
| DB concurrency | 장애 위험 | **Postgres** + 적절 인덱스, 트랜잭션 튜닝 |
| Snapshot write vs read | 파일 깨짐 | Temp 파일 + **atomic rename** |
| DEV API abuse | 부하/보안 | IP allowlist + API key + audit log |
| Backup & restore | 데이터 유실 | Nightly `pg_dump` + snapshot copy + 복구 리허설 |

**Speaker Notes**  
“핵심 5가지만 잡으면 Phase‑1은 안전합니다.”

---

## 8) Decisions Needed Today (Go/No‑Go items)
1) **DB: Postgres 고정** (운영 전환 전 필수)  
2) **API 표면 확정** (v1 2종 + dev 3종 + `?download=1`)  
3) **Windows 서비스 등록** (Django/Streamlit/ETL 전부)  
4) **KPI 승인** (Perf/Freshness/Adoption/Ops)

**Speaker Notes**  
“이 4가지만 합의하면 바로 배포 캘린더에 올리겠습니다.”

---

## 9) 30–60–90 (Actionable roadmap)
- **D+0~7 (Build/Hardening)**: Postgres 전환, Windows 서비스(NSSM), atomic snapshot, API 통합 테스트
- **D+8~21 (Pilot/Measure)**: 20명 사용 개시, WAU/Perf/Freshness 대시보드
- **D+22~30 (Decide/Scale)**: KPI 리뷰 → Phase‑2 Go/No‑Go (SSO/RBAC 설계 착수)

**Speaker Notes**  
“30일 안에 가치, 60일 안에 규모, 90일 안에 보안을 검증하겠습니다.”

---

## 10) Roles & Next Steps
- **BE/DevOps:** Postgres, API, Windows 서비스, 백업/복구 자동화
- **FE/Streamlit:** Snapshot 로딩 최적화, Home/Overview/History/Dev 탭 완성
- **Project Lead:** KPI 모니터링, 리스크 관리, 주간 리포트

---

## Appendix A — Demo Script (5 min)
1) Home: `/api/dev/runs/summary` 카드 (1/7/14/30)  
2) Overview: `features` 필터 & CSV export  
3) History: `changes` diff 예시  
4) Dev: `sync/run` 트리거 → runs 로그 확인

## Appendix B — Glossary
- **Snapshot‑First:** UI는 DB 대신 사전 계산된 스냅샷을 우선 조회
- **identity_hash:** 핵심키 조합의 SHA‑256, 멱등/중복방지
- **allowlist:** 허용된 IP만 접근 가능
