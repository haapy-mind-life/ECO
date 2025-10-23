from __future__ import annotations
import os, requests
from typing import Any, Dict, Optional

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api").rstrip("/")
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() in ("1","true","yes")

API_KEY = os.getenv("API_KEY")

def _get(path: str, params: Optional[Dict[str, Any]] = None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    headers = {"X-API-KEY": API_KEY} if API_KEY else {}
    r = requests.get(url, params=params or {}, headers=headers, verify=VERIFY_SSL, timeout=30)
    r.raise_for_status()
    return r.json()

def _post(path: str, json_body: Optional[Dict[str, Any]] = None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    headers = {"X-API-KEY": API_KEY} if API_KEY else {}
    r = requests.post(url, json=json_body or {}, headers=headers, verify=VERIFY_SSL, timeout=60)
    r.raise_for_status()
    return r.json()

# ---- READ APIs ----
def list_feature_groups():
    return _get("/feature-groups/")

def list_features(group_name: str):
    return _get("/features/", {"group": group_name})

def list_feature_records(group_name: str, feature_name: str, **filters):
    params = {"group": group_name, "feature": feature_name}
    params.update({k: v for k, v in filters.items() if v})
    return _get("/feature-records/", params)

def list_long_records(**filters):
    # 피벗/다운로드 친화 Long 뷰 (백엔드 구현 필요 시 /feature-records/로 대체)
    return _get("/long-records/", filters)

def list_runs(page: int = 1, page_size: int = 50):
    # ImportRun 리스트 (views.GenericViewSet list)
    return _get("/sync/", {"page": page, "page_size": page_size})

def list_feature_record_logs(page: int = 1, page_size: int = 100, **filters):
    # 선택: 백엔드에 /feature-record-logs/가 구현되어 있다면 사용
    return _get("/feature-record-logs/", {"page": page, "page_size": page_size, **filters})

# ---- WRITE / ACTION APIs ----
def trigger_nightly_sync(source_tag: str | None = None):
    payload = {"source_tag": source_tag} if source_tag else None
    return _post("/sync/nightly", payload)
