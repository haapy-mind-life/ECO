
# FMW Streamlit 데이터 매니저 (샘플)

- **목표**: 매일 **06:00 자동 동기화(cron)** + 수동 실행, 동기화 **변경 이력 화면**, **사이드바 탐색(그룹→피처→필터)** 제공
- **연동**: Django DRF API (예: `/api/feature-groups/`, `/api/features/`, `/api/feature-records/`, `/api/long-records/`, `/api/sync/nightly`)
- **참고**: `.env.example`의 `API_BASE`를 실제 백엔드 주소로 설정

## 빠른 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 환경변수 설정(또는 .env 사용)
export API_BASE="http://localhost:8000/api"

# Streamlit 실행
streamlit run main.py
```

## 운영(권장) — Cron으로 06:00 동기화
서버에서 다음과 같이 등록합니다.

```cron
0 6 * * * API_BASE="http://localhost:8000/api" \
  /usr/bin/python3 /mnt/data/fmw_streamlit_data_manager/scripts/sync_data.py >> /var/log/fmw_sync.log 2>&1
```

또는 앱 내 보조 스케줄/APScheduler도 제공됩니다(세션 재시작 가능성이 있으므로 **cron 병행 권장**).

## 폴더 구조

```
fmw_streamlit_data_manager/
├── .streamlit/
│   └── config.toml
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── navigation.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── data_manager.py
│   │   └── sample_features.py
│   └── views/
│       ├── __init__.py
│       ├── home.py
│       ├── history.py
│       └── visualization.py
├── pages/
│   └── 01_데이터_매니저.py
├── scripts/
│   └── sync_data.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## 주의
- 백엔드 API가 아직 일부 엔드포인트를 노출하지 않았다면(예: `/api/feature-record-logs/`), **동일 경로로 뷰셋 추가** 또는 `ImportRun.stats`를 활용해 기본 이력을 먼저 표기할 수 있습니다.
- 캐시는 기본적으로 `./_cache` 폴더에 Parquet/JSON으로 저장됩니다.
