# FMW 전체 시스템 구조 (Obsidian·Mermaid) — 2025-10-31

> 이 노트는 **Obsidian**에서 바로 렌더링되도록 **Mermaid** 다이어그램으로 구성되었습니다.  
> 그대로 붙여넣거나 파일로 저장해 Vault에 넣으세요.

---

## 1) 시스템 컨텍스트 (사용자↔게이트웨이↔서비스↔데이터)
```mermaid
flowchart LR
    user[내부 사용자\n(Dev/운영/기획)] -->|브라우저| NX[Nginx 게이트웨이\n(IP Allowlist)]
    subgraph HOST[내부 서버(루프백 바인딩)]
      NX -->|/streamlit/* 프록시| ST[Streamlit Viewer\n127.0.0.1:8501]
      NX -->|/api/* 프록시| DJ[Django API/ETL\n127.0.0.1:8000]
      ST -->|스냅샷 로드| FS[(snapshot/\nrecords.csv\nruns_summary.json)]
      DJ -->|읽기·쓰기| DB[(Postgres\nfeatures / changes\nruns / daily_counts\nname_map / mcc_mnc_map)]
    end
    EXT[외부 원천(정책/피처 등)] --> SY[Sync 스크립트/잡]
    SY --> DJ
    classDef comp fill:#f8f8f8,stroke:#666,stroke-width:1px,color:#222;
    class NX,ST,DJ,DB,FS,HOST,SY comp;
```

---

## 2) 데이터 파이프라인(ETL) — 스냅샷 우선
```mermaid
flowchart LR
    A[Extract\n(Sync)] --> B[Normalize\n(name_map 적용)]
    B --> C[MCC/MNC 매핑\n(mcc_mnc_map 보강)]
    C --> D[Upsert → features\n(identity_hash UNIQUE)]
    D --> E[Write changes\n(before/after, run_id)]
    E --> F[Aggregate daily_counts\n(1/7/14/30)]
    F --> G[Write snapshots\nrecords.csv & runs_summary.json\n(임시 생성 → 원자적 교체)]
```

---

## 3) 동작 시나리오 (시퀀스) — 싱크 트리거부터 UI 갱신까지
```mermaid
sequenceDiagram
    participant FE as 사용자(브라우저)
    participant NX as Nginx
    participant ST as Streamlit
    participant DJ as Django API/ETL
    participant DB as Postgres
    participant FS as snapshot 디렉토리

    FE->>NX: GET /streamlit/Home
    NX->>ST: Proxy
    ST-->>FE: Home 렌더(마지막 스냅샷)

    FE->>NX: POST /api/dev/sync/run
    NX->>DJ: Proxy
    DJ->>DB: Upsert features / Insert changes / Insert runs
    DJ->>FS: records.csv, runs_summary.json 임시 생성
    DJ->>FS: 원자적 rename(교체 완료)
    ST-->>FE: (새 스냅샷 감지 시 재로딩)
```

---

## 4) 데이터베이스 ERD (핵심 테이블)
```mermaid
erDiagram
    runs ||--o{ changes : has
    runs ||--o{ daily_counts : generates
    features ||--o{ changes : affects
    name_map ||..|| features : normalizes
    mcc_mnc_map ||..|| features : enriches

    features {
        string identity_hash PK
        string model_name
        string solution
        string feature_group
        string feature
        string mode
        string value
        string region
        string country
        string operator
        string mcc
        string mnc
        datetime effective_at
        datetime synced_at
    }

    changes {
        int id PK
        string identity_hash FK
        string action  "CREATE|UPDATE|DELETE"
        json  before
        json  after
        string reason
        int run_id FK
        datetime changed_at
    }

    runs {
        int id PK
        datetime started_at
        datetime finished_at
        string status  "SUCCESS|FAIL"
        int created
        int updated
        int deleted
        int errors
    }

    daily_counts {
        date date PK
        int created
        int updated
        int deleted
        int errors
        int run_id FK
    }

    name_map {
        int id PK
        string alias
        string canonical
        string type "feature|group|mode|..."
        datetime valid_from
        datetime valid_to
    }

    mcc_mnc_map {
        int id PK
        string mcc
        string mnc
        string region
        string country
        string operator
        datetime valid_from
        datetime valid_to
    }
```

---

## 5) API 개요(참조용)
```mermaid
flowchart TB
  subgraph v1[읽기 전용 v1 API]
    V1A["GET /api/v1/features\n(기본 CSV, ?format=json)"]
    V1B["GET /api/v1/features/{feature_group}"]
  end

  subgraph dev[운영/개발 dev API]
    DV1["POST /api/dev/sync/run\n(싱크 트리거)"]
    DV2["GET /api/dev/runs/summary\n(1/7/14/30일 오버뷰)"]
    DV3["GET /api/dev/changes\n(선택: 상세 추적)"]
  end

  V1A -->|"Streamlit/툴에서 조회"| Streamlit
  V1B --> Streamlit
  DV1 -->|"운영자/CI"| Django
  DV2 --> Streamlit
  DV3 --> Streamlit

  classDef api fill:#eef7ff,stroke:#2b6cb0,color:#1a365d,stroke-width:1px;
  class V1A,V1B,DV1,DV2,DV3 api;
```

---

### 사용 팁
- Obsidian에서 **Mermaid** 플러그인이 활성화되어 있어야 합니다(기본 활성).  
- 다이어그램이 길면 *편집 모드*에서 접고 펼치며 검토하세요.  
- 팀 공유용으로 이 파일을 Vault에 그대로 두거나, 필요한 섹션만 복사해 새 노트를 만들어도 됩니다.