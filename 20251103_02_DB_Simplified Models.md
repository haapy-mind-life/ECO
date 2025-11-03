# 🗄️ FMW DB — Simplified Models (v1/dev/ops) · 2025‑11‑03

**목표:** 이름을 **단순·직관**하게 재정렬. 당장 구현 가능한 **핵심 컬럼만** 정의. (FK/MV/파티셔닝은 보류)

- **네임 컨벤션:** DB = `snake_case`(복수형), Django Model = `PascalCase`(단수), DRF = `kebab-case`(복수)
- **시간대:** 저장 UTC, 표시 KST
- **보안:** Nginx IP Allowlist + `X-API-Key(ops)`(ops 전용)
- **동기화:** NSSM 매일 06:00 KST (→ ops.SyncHistory 기록)

---

## 1) 모델 카탈로그 (최종)

### v1

- **Feature** → `features`
- **AllowList**(feature_group 파생) → 뷰 `v1_allow_list`
- **BlockList**(feature_group 파생) → 뷰 `v1_block_list`
- **RelFeatures** → `rel_features`
- **AsRel** → `as_rel`
- **UeCapa** → `ue_capa`

### dev

- **SlsiAllowList** → `slsi_allow_list`
- **MtkAllowList** → `mtk_allow_list`
- **SlsiBlockList** → `slsi_block_list`
- **MtkBlockList** → `mtk_block_list`
- **UeCapaRecord** → `ue_capa_record`
- **NameMap** → `name_map`
- **MccMncMap** → `mcc_mnc_map`

### ops (신설)

- **ReqLog** → `req_log`
- **ErrLog** → `err_log`
- **SyncHistory**(+ DailyCount 포함) → `sync_history`
- **ChangeHistory** → `change_history`

> 기존 혼용 명칭은 **호환 뷰**로 유지: `accesslog`→`req_log`, `runs/sync_history` 통합 등 (§5 참조)

---

## 2) 최소 스키마 (DDL, PG 기준 — SQLite도 가능하도록 단순화)

### 2.1 v1

```sql
CREATE TABLE features (
  id BIGSERIAL PRIMARY KEY,
  model_name TEXT NOT NULL,
  solution TEXT NOT NULL CHECK (solution IN ('slsi','mtk')),
  feature_group TEXT NOT NULL,
  feature TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('allow','block','none')),
  value TEXT,
  mcc TEXT, mnc TEXT, region CHAR(2), country CHAR(2), operator TEXT,
  identity_hash TEXT UNIQUE NOT NULL,
  sync_time TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_features_recent ON features(sync_time DESC) WHERE sync_time >= now() - interval '90 days';
CREATE INDEX idx_features_solution_model ON features(solution, model_name);
CREATE INDEX idx_features_group_feature ON features(feature_group, feature);

CREATE VIEW v1_allow_list AS SELECT * FROM features WHERE mode='allow';
CREATE VIEW v1_block_list AS SELECT * FROM features WHERE mode='block';

CREATE TABLE rel_features (
  id BIGSERIAL PRIMARY KEY,
  parent_feature_hash TEXT NOT NULL,
  child_feature_hash  TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('depends_on','conflicts_with','implies'))
);
CREATE INDEX idx_rel_parent ON rel_features(parent_feature_hash);
CREATE INDEX idx_rel_child  ON rel_features(child_feature_hash);

CREATE TABLE as_rel (
  id BIGSERIAL PRIMARY KEY,
  a_dim TEXT NOT NULL, a_value TEXT NOT NULL,
  b_dim TEXT NOT NULL, b_value TEXT NOT NULL,
  rel_type TEXT NOT NULL CHECK (rel_type IN ('maps_to','excludes','aliases')),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(a_dim,a_value,b_dim,b_value,rel_type)
);

CREATE TABLE ue_capa (
  id BIGSERIAL PRIMARY KEY,
  model_name TEXT NOT NULL,
  category TEXT NOT NULL,
  item TEXT NOT NULL,
  capa_value TEXT,
  source TEXT,
  reported_at TIMESTAMPTZ
);
CREATE INDEX idx_ue_model ON ue_capa(model_name);
```

### 2.2 dev

```sql
CREATE TABLE slsi_allow_list (LIKE features INCLUDING ALL);
CREATE TABLE mtk_allow_list  (LIKE features INCLUDING ALL);
CREATE TABLE slsi_block_list (LIKE features INCLUDING ALL);
CREATE TABLE mtk_block_list  (LIKE features INCLUDING ALL);

CREATE TABLE ue_capa_record (
  id BIGSERIAL PRIMARY KEY,
  model_name TEXT,
  raw_payload JSONB,
  source TEXT,
  received_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE name_map (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,
  alias TEXT NOT NULL,
  canonical TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(kind, alias)
);

CREATE TABLE mcc_mnc_map (
  id BIGSERIAL PRIMARY KEY,
  mcc VARCHAR(3) NOT NULL,
  mnc VARCHAR(3) NOT NULL,
  region CHAR(2), country CHAR(2), operator TEXT,
  UNIQUE(mcc, mnc)
);
```

### 2.3 ops (신설)

```sql
-- 1) 요청/접속 로그
CREATE TABLE req_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,   -- 'nginx','django','drf','streamlit','cron'
  ns TEXT NOT NULL,       -- 'v1','dev','ops','admin','streamlit'
  method TEXT NOT NULL, path TEXT NOT NULL,
  status INT NOT NULL, duration_ms INT NOT NULL,
  remote_ip TEXT NOT NULL, api_key_hash TEXT, user_agent TEXT,
  allowed INT DEFAULT 1
);
CREATE INDEX idx_req_recent ON req_log(ts DESC) WHERE ts >= now() - interval '7 days';
CREATE INDEX idx_req_source_ts ON req_log(source, ts DESC);
CREATE INDEX idx_req_ip_ts ON req_log(remote_ip, ts DESC);
CREATE INDEX idx_req_status_ts ON req_log(status, ts DESC);

-- 2) 애플리케이션 오류 로그
CREATE TABLE err_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ DEFAULT now(),
  level TEXT NOT NULL CHECK (level IN ('ERROR','WARN','INFO')),
  logger TEXT, message TEXT NOT NULL, context JSONB
);
CREATE INDEX idx_err_ts ON err_log(ts DESC);

-- 3) 동기화 이력(일별 요약 필드 포함)
CREATE TABLE sync_history (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT UNIQUE NOT NULL,
  started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  status TEXT, created INT, updated INT, deleted INT,
  -- DailyCount를 포함한 요약(선택 필드):
  day DATE,                   -- run 기준 일자
  total_requests BIGINT,      -- 해당 일자 요청 수(선택)
  total_models BIGINT,        -- 해당 일자 모델 수(선택)
  total_features BIGINT,      -- 해당 일자 피처 수(선택)
  notes TEXT
);
CREATE INDEX idx_sync_started ON sync_history(started_at DESC);
CREATE INDEX idx_sync_day ON sync_history(day DESC);

-- 4) 변경 이력
CREATE TABLE change_history (
  id BIGSERIAL PRIMARY KEY,
  changed_at TIMESTAMPTZ NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('created','updated','deleted')),
  identity_hash TEXT,
  model_name TEXT, feature_group TEXT, feature TEXT,
  mode_before TEXT, mode_after TEXT,
  value_before TEXT, value_after TEXT,
  run_id TEXT
);
CREATE INDEX idx_change_when ON change_history(changed_at DESC);
CREATE INDEX idx_change_run ON change_history(run_id);
```

---

## 3) API 매핑 (새 이름 · 하위호환 없음)

- **인증/권한:** v1/dev = Nginx IP Allowlist, ops = IP Allowlist + `X-API-Key`

### 3.1 v1

- `GET /api/v1/features` — 필터: `model_name, solution, feature_group, feature, mode, mcc, mnc, region, country, operator`
- `GET /api/v1/allow-list` · `GET /api/v1/block-list` — 뷰 기반(모드 파생)
- `GET /api/v1/rel-features` — 피처 관계
- `GET /api/v1/as-rel` — 도메인 매핑
- `GET /api/v1/ue-capa` — 단말 기능

### 3.2 dev

- `GET /api/dev/slsi/allow-list` · `GET /api/dev/mtk/allow-list`
- `GET /api/dev/slsi/block-list` · `GET /api/dev/mtk/block-list`
- `GET /api/dev/ue-capa-record`
- `GET /api/dev/name-map` · `GET /api/dev/mcc-mnc-map`

### 3.3 ops (새 이름 고정)

- 로그/이력 원본
    - `GET /api/ops/req-log` — (= ReqLog)
    - `GET /api/ops/err-log` — (= ErrLog)
    - `GET /api/ops/sync-history` — (= SyncHistory)
    - `GET /api/ops/change-history` — (= ChangeHistory)
- 대시보드 메트릭
    - `GET /api/ops/metrics/models[?solution=]` → `{count}`
    - `GET /api/ops/metrics/features[?solution=]` → `{count}`
    - `GET /api/ops/metrics/records[?solution=]` → `{count}`
    - `GET /api/ops/models?solution=&q=&limit=&offset=` → `[{model_name, features}]`
    - `GET /api/ops/features?solution=&group=&q=&limit=&offset=` → `[{feature_group, feature}]`
    - `GET /api/ops/unique-ips?win=1d|7d|30d` → `[ {day, unique_ips} ]`
    - `GET /api/ops/ip-top?win=7d&limit=20` → `[{remote_ip, hits}]`
    - `GET /api/ops/traffic-summary?win=60m` → `[{source, requests, err5xx, err4xx, p95_ms}]`
    - `GET /api/ops/traffic-detail?win=60m&limit=200` → `[{source, ns, method, path, requests, p95_ms}]`
    - `POST /api/ops/sync/run` → 수동 동기화 트리거 `{run_id, status}`

**응답 규칙**

- 키는 소문자·snake_case, 리스트 페이징: `limit, offset`, 총계: `X-Total-Count` 헤더.

## 4) 호환성 (COMPAT 뷰)

> **삭제됨.** 하위 호환이 필요 없다는 요구에 따라 COMPAT 뷰/라우팅을 제거합니다. ) 호환성 **정책 변경:** 하위 호환(레거시 API/뷰) **미제공**. 애플리케이션과 문서는 모두 위 §3의 새 엔드포인트만 사용합니다.

---

## 5) 품질/성능 가드레일

- **도메인 제약:** `solution IN('slsi','mtk')`, `mode IN('allow','block','none')`, `mcc=^\d{3}$`, `country=^[A-Z]{2}$`
- **인덱스 우선:** 최근 구간(partial) + 조합 인덱스(source/ip/status)
- **중복 방지:** `features.identity_hash` UNIQUE, `sync_history.run_id` UNIQUE

---

## 6) DoD (완료 기준)

- [ ] 테이블 4(v1) + 7(dev) + 4(ops) 생성
- [ ] **하위 호환 라우팅/뷰 없음** 확인(새 엔드포인트만 유효)
- [ ] `/api/ops/metrics/*`·`/api/ops/req-log`·`/api/ops/err-log`·`/api/ops/sync-history`·`/api/ops/change-history` 응답 P95 < 3s(60m 창)
- [ ] 1/7/30일 **Unique IP 그래프** 렌더 확인
- [ ] 최근 7일 **동기화 상세/요약** 교차검증