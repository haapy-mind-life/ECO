# FMW 제품 요구사항 문서 (PRD) — by GPT  
**기준일:** 2025-10-31  
**버전 정책:** 날짜 기반(예: 20251031), V3 표기 제거

---

## 0. 문서 목적
본 문서는 FMW 시스템의 **비즈니스 목표, 아키텍처 원칙, 데이터 모델, API, 운영 정책**을 단일 기준선으로 정의합니다.  
이전 “v3” 등의 버전 표시는 혼란을 유발하므로 **모든 산출물은 날짜 기준 버전**으로만 관리합니다.

---

## 1. 개요 (Overview)
### 1.1 미션
분산된 정책/피처/운영 상태 정보를 내부 사용자에게 **빠르고, 안정적으로, 일관되게** 제공하여 데이터 기반 의사결정을 가속화한다.

### 1.2 해결 과제 (Pain Points)
- 정보 파편화, 비표준 스키마, 운영 자동화 부족, 감사 추적 미흡, 실시간 쿼리 의존에 따른 불안정성

### 1.3 핵심 원칙 (Architecture Principles)
- **Snapshot First**: UI는 미리 생성된 스냅샷(파일/테이블)을 우선 조회 → 빠른 로딩과 장애 격리
- **Dual-Layer Security**: Nginx Allowlist(외부 경계) + App Loopback(내부 경계)
- **Idempotency & Normalization**: `identity_hash` UNIQUE, `name_map` 기반 정규화
- **Enrich Before Upsert**: `mcc_mnc_map`으로 region/country/operator를 사전 보강
- **Separation of Concerns**: features(현재), changes(이력), runs(실행), daily_counts(집계)의 역할 분리

### 1.4 데이터 흐름 (E2E Pipeline)
**Sync → Normalize/Enrich → Upsert(features) → Write changes → Aggregate(daily_counts) → Snapshot → UI**

---

## 2. 성공 지표 (KPIs) & 비기능 요구사항 (NFRs)
### 2.1 성능 KPI
- Home 평균 < **1s**, 주요 조회 P95 < **5s**, `/api/v1/*` P95 < **3s**

### 2.2 신선도 & 안정성
- 일일 동기화 성공률 ≥ **98%**, 분기 Sev‑2 이상 장애 ≤ **1건**

### 2.3 보안 & 운영성
- 비허용 IP **0% 접근**, 일상 점검 시간 ≤ **30분/일**, 온보딩 **≤ 1시간**

### 2.4 복원력
- 백엔드 장애 시에도 마지막 **유효 스냅샷 기반** 서비스 지속

---

## 3. 사용자 페르소나 (JTBD)
- **Developer**: 현재 피처 상태 즉시 확인·공유
- **Operator/Analyst**: 동기화 성공/추세 점검, CSV Export
- **Product/Policy Owner**: 시장/기능 영향도 요약 카드
- **Compliance/Management**: 접근·변경 추적

---

## 4. 범위 (Scope)
### 4.1 포함
- 스냅샷 우선 조회, CSV 기본/JSON 옵션 API, 운영 요약 대시보드, IP Allowlist, 표준 스크립트(Sync.bat, run_all.py 등)

### 4.2 제외(당분간)
- UI CUD, 외부망 공개/멀티테넌시, SSO/RBAC 전면 도입, 실시간 스트리밍 분석

---

## 5. 아키텍처 (Best‑Practice)
### 5.1 구성
- **Gateway**: Nginx(Allowlist, 라우팅, 헤더 전파)
- **Backend**: Django(127.0.0.1:8000, DRF), ETL 파이프라인(비동기 트리거)
- **Viewer**: Streamlit(127.0.0.1:8501, Snapshot 우선 로딩)
- **Storage**: SQLite(초기) → **Postgres(전환 트리거 충족 시)**

### 5.2 전환 트리거 (SQLite → Postgres)
- `features > 5,000,000` rows, 동시 접속자 > 5, 일일 업서트 > 200,000건, **UI 평균 > 8s** 초과 중 하나라도 만족 시 전환

### 5.3 보안 (요약)
- **Nginx**: 내부망 IP만 허용, `X-API-Key` 헤더 전달
- **DRF**: 권한 클래스에서 IP 대역 + API Key 동시 검증
- **프로세스 바인딩**: Django/Streamlit 모두 루프백 바인딩

---

## 6. 데이터 모델 (ERD 요약)
### 6.1 핵심 테이블
- **features**: 현재 상태 원장(정규화, `identity_hash` UNIQUE)
- **changes**: C/U/D 이력(`before_json`, `after_json`, `changed_at`, `run_id`)
- **runs**: 싱크 실행 로그(시작/종료/상태/건수)
- **daily_counts**: 일별 C/U/D/errors 집계(Home 로딩용)
- **name_map**: 별칭↔표준명 정규화 택사노미
- **mcc_mnc_map**: MCC/MNC → region/country/operator 매핑(유효기간 포함)

### 6.2 주요 컬럼(발췌)
- features: `identity_hash`, `model_name`, `solution`, `feature_group`, `feature`, `mode`, `value`, `mcc`, `mnc`, `region`, `country`, `operator`, `sp_fci`, `sync_time`
- changes: `id`, `identity_hash`, `action(create|update|delete)`, `before_json`, `after_json`, `changed_at`, `run_id`
- runs: `run_id`, `started_at`, `finished_at`, `status(started|succeeded|failed)`, `created`, `updated`, `deleted`, `errors`

---

## 7. API 설계 (날짜 버전 정책, v1/DEV)
### 7.1 공개 읽기 전용 — `/api/v1`
- `GET /api/v1/features` : 필터 가능한 전체 스냅샷(CSV 기본, `?format=json` 옵션)
- `GET /api/v1/features/{feature_group}` : 그룹별 스냅샷
- `GET /api/v1/features/download` : 대용량 다운로드(스트리밍 권장)

### 7.2 내부 운영 — `/api/dev`
- `POST /api/dev/sync/run` : ETL 비동기 트리거 (예: **Sync.bat** 호출)
- `GET /api/dev/runs/summary?days=1|7|14|30&yesterday=bool` : 오버뷰 집계 반환
- `GET /api/dev/changes` , `GET /api/dev/changes/diff` : 이력 조회/비교
- `GET/PUT /api/dev/slsi/allow_list` : 내부 허용 리스트 관리(옵션)

> **정책**: `/api/dev/*` 는 **내부망 + API Key** 2중 보호. 외부 차단.

---

## 8. 파이프라인 & 스냅샷
### 8.1 단계
1) **Sync** (스크립트 실행: `scripts/Sync.bat` → 폴더 내 모든 싱크 스크립트 순차 실행)  
2) **Normalize/Name Mapping** (`name_map` 적용)  
3) **Enrich** (`mcc_mnc_map`으로 region/country/operator 추가)  
4) **Upsert(features)** (`identity_hash` 기반 멱등 업서트)  
5) **Write changes** (C/U/D diff 저장)  
6) **Aggregate(daily_counts)** (Home·요약용)  
7) **Snapshot Write** (records.csv / runs_summary.json / parquet 옵션)

### 8.2 운영 스크립트
- `scripts/Sync.bat` : 싱크 + ETL 오케스트레이션
- `infra/run_all.py` : 서비스 생명주기(start/stop/status)

---

## 9. UI(Streamlit) 정보 구조
- **Home**: `runs_summary.json` 기반 KPI 카드(오늘/어제/7/14/30일)
- **Overview**: `features` 스냅샷 테이블(필터/다운로드)
- **History**: `changes` 이력 조회/검색/필터
- **Detail**: 고급 필터, CSV Export
- **Dev**: 수동 싱크 트리거, 로그 확인(개발자용)

---

## 10. 운영 및 관측성
- 표준 로그 디렉토리(Nginx/Django/Streamlit)
- `/api/dev/runs/summary` 수집 및 대시보드화
- 데이터 보존: `daily_counts` 90일, `changes` 180일(팀 정책에 맞게 조정)

---

## 11. 마이그레이션 & 호환성
- 레거시(v3 등) 명시적 제거. 모든 산출물은 **날짜 버전(예: 20251031)** 로 관리.  
- DB 전환(포스트그레스) 시, DDL 스크립트/마이그레이션 파일 제공.

---

## 12. 부록 (샘플 스니펫)

### 12.1 Nginx 내부망 보호 예시
```nginx
location /api/dev/ {
  allow 127.0.0.1;
  allow 10.0.0.0/8;
  allow 192.168.0.0/16;
  deny all;

  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-API-Key $http_x_api_key;
  proxy_pass http://127.0.0.1:8000;
}
```

### 12.2 DRF 권한 예시
```python
from rest_framework.permissions import BasePermission
import os

class IsInternalAndKey(BasePermission):
    def has_permission(self, request, view):
        ip = request.META.get("REMOTE_ADDR", "")
        allowed = ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.")
        api_key = request.headers.get("X-API-Key")
        return allowed and api_key and api_key == os.getenv("DEV_API_KEY")
```

### 12.3 SQLite → Postgres 전환 체크(지표)
- features row 수, UI 평균 로드, 동시 접속 수, 일일 업서트 건수

---

## 13. 로드맵 (추천)
- **즉시**: UI/ETL PoC(0.5M/1M/5M), DEV API 보안 반영, OpenAPI 보강
- **중기**: Postgres 전환, SSO/RBAC, 운영 대시보드 고도화
- **장기**: 컨테이너화, HA, 구조화 로그·메트릭, DuckDB/Polars 검토

---

## 14. 변경 이력
- 20251031 — 최초 통합본(by GPT). v3 삭제, 날짜 버전 정책 확정, MCC/MNC 매핑 단계 명시.
