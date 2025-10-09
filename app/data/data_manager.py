from __future__ import annotations
import json, time, pathlib, threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import pandas as pd
import requests

KST = timezone(timedelta(hours=9))

class DataManager:
    """DRF에서 하루 1회 동기화→로컬 캐시(Parquet)를 제공하고, 앱은 캐시만 조회."""
    def __init__(self, api_base: str, data_dir: str = "./_cache", verify_ssl: bool = False, timeout: int = 20):
        self.api_base = api_base.rstrip("/")
        self.data_dir = pathlib.Path(data_dir)
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.data_dir / "_meta.json"
        self.lock = threading.Lock()
        self._meta = self._load_meta()

    def _load_meta(self) -> Dict:
        if self.meta_path.exists():
            try:
                return json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_meta(self):
        tmp = json.dumps(self._meta, ensure_ascii=False, indent=2)
        self.meta_path.write_text(tmp, encoding="utf-8")

    def _dataset_paths(self, name: str):
        return (self.data_dir / f"{name}.parquet",)

    def last_sync_at(self, name: str) -> Optional[datetime]:
        ts = self._meta.get(name, {}).get("last_sync_epoch")
        if not ts: return None
        return datetime.fromtimestamp(int(ts), tz=KST)

    def _set_sync_meta(self, name: str, etag: Optional[str] = None):
        entry = self._meta.get(name, {})
        entry["last_sync_epoch"] = int(time.time())
        if etag: entry["etag"] = etag
        self._meta[name] = entry
        self._save_meta()

    # -------- DRF 호출/저장 -------- #
    def _drf_get(self, path: str, params: Optional[dict] = None, etag: Optional[str] = None):
        url = f"{self.api_base}/{path.lstrip('/')}"
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        r = requests.get(url, params=params or {}, headers=headers, timeout=self.timeout, verify=self.verify_ssl)
        if r.status_code == 304:
            return None, etag
        r.raise_for_status()
        return r.json(), r.headers.get("ETag")

    def _save_parquet(self, name: str, data):
        df = pd.DataFrame(data["results"] if isinstance(data, dict) and "results" in data else data)
        path, = self._dataset_paths(name)
        df.to_parquet(path, index=False)
        return df

    def sync_feature(self, name="feature1", path="/api/feature1/", params=None) -> pd.DataFrame:
        with self.lock:
            meta = self._meta.get(name, {})
            etag = meta.get("etag")
            res, new_etag = self._drf_get(path, params=params, etag=etag)
            if res is None:
                return self.load(name, stale_ok=True)
            df = self._save_parquet(name, res)
            self._set_sync_meta(name, etag=new_etag or etag)
            return df

    # -------- 로컬 로드/갱신 -------- #
    def load(self, name: str, stale_ok=True) -> pd.DataFrame:
        path, = self._dataset_paths(name)
        if not path.exists():
            try:
                return self.sync_feature(name=name)
            except Exception:
                return pd.DataFrame()
        return pd.read_parquet(path)

    def refresh_if_stale(self, name: str, max_age_hours=24) -> None:
        last = self.last_sync_at(name)
        if last and (datetime.now(tz=KST) - last) < timedelta(hours=max_age_hours):
            return
        def _bg():
            try:
                self.sync_feature(name=name)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    @staticmethod
    def format_last_sync(dt: Optional[datetime]) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S KST") if dt else "-"
