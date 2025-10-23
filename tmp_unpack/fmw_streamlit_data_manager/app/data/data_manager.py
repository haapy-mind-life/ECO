from __future__ import annotations
import json, os, pathlib, threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import pandas as pd

from app.data.api import (
    list_feature_groups, list_features, list_feature_records,
    list_long_records, list_runs, list_feature_record_logs, trigger_nightly_sync
)

KST = timezone(timedelta(hours=9))

class DataManager:
    """DRF에서 읽어와 Parquet/JSON 캐시를 제공. 앱은 캐시 우선 조회."""
    def __init__(self, data_dir: str = "./_cache"):
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 캐시 경로 ----------
    def _path(self, name: str, suffix: str) -> pathlib.Path:
        return self.data_dir / f"{name}{suffix}"

    def _ts_path(self, name: str) -> pathlib.Path:
        return self._path(name, "._last_sync.json")

    # ---------- 공통: 마지막 동기화 시간 ----------
    def last_sync_at(self, name: str) -> Optional[datetime]:
        p = self._ts_path(name)
        if not p.exists():
            return None
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
            if meta.get("last_sync_kst"):
                return datetime.fromisoformat(meta["last_sync_kst"])
        except Exception:
            pass
        return None

    def _save_last_sync(self, name: str):
        meta = {"last_sync_kst": datetime.now(tz=KST).isoformat(timespec="seconds")}
        self._ts_path(name).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # ---------- 동기화 ----------
    def sync_groups(self) -> pd.DataFrame:
        rows = list_feature_groups()
        df = pd.DataFrame(rows)
        df.to_parquet(self._path("feature_groups", ".parquet"), index=False)
        self._save_last_sync("feature_groups")
        return df

    def sync_features_for_group(self, group_name: str) -> pd.DataFrame:
        rows = list_features(group_name)
        df = pd.DataFrame(rows)
        df.to_parquet(self._path(f"features__{group_name}", ".parquet"), index=False)
        self._save_last_sync(f"features__{group_name}")
        return df

    def sync_records(self, group_name: str, feature_name: str, **filters) -> pd.DataFrame:
        rows = list_feature_records(group_name, feature_name, **filters)
        df = pd.DataFrame(rows)
        df.to_parquet(self._path(f"records__{group_name}__{feature_name}", ".parquet"), index=False)
        self._save_last_sync(f"records__{group_name}__{feature_name}")
        return df

    def sync_runs(self) -> pd.DataFrame:
        resp = list_runs(page=1, page_size=100)
        results = resp.get("results", resp) if isinstance(resp, dict) else resp
        df = pd.DataFrame(results)
        df.to_parquet(self._path("import_runs", ".parquet"), index=False)
        self._save_last_sync("import_runs")
        return df

    def sync_logs(self) -> pd.DataFrame:
        try:
            resp = list_feature_record_logs(page=1, page_size=1000)
            results = resp.get("results", resp) if isinstance(resp, dict) else resp
            df = pd.DataFrame(results)
        except Exception:
            df = pd.DataFrame(columns=[
                "run", "action", "feature", "model_name", "operator",
                "region", "country", "sp_type", "mcc", "mnc",
                "before_mode", "after_mode", "before_value", "after_value", "logged_at"
            ])
        df.to_parquet(self._path("feature_record_logs", ".parquet"), index=False)
        self._save_last_sync("feature_record_logs")
        return df

    def trigger_sync_now(self, source_tag: str | None = None) -> Dict:
        return trigger_nightly_sync(source_tag=source_tag)

    # ---------- 로딩 ----------
    def load_parquet(self, name: str) -> pd.DataFrame:
        p = self._path(name, ".parquet")
        if p.exists():
            return pd.read_parquet(p)
        return pd.DataFrame()

    def groups(self) -> pd.DataFrame:
        return self.load_parquet("feature_groups")

    def features_for_group(self, group_name: str) -> pd.DataFrame:
        return self.load_parquet(f"features__{group_name}")

    def records(self, group_name: str, feature_name: str) -> pd.DataFrame:
        return self.load_parquet(f"records__{group_name}__{feature_name}")

    def runs(self) -> pd.DataFrame:
        return self.load_parquet("import_runs")

    def logs(self) -> pd.DataFrame:
        return self.load_parquet("feature_record_logs")

    # ---------- 스테일 시 백그라운드 동기화 ----------
    def refresh_if_stale(self, name: str, max_age_hours=24) -> None:
        last = self.last_sync_at(name)
        if last and (datetime.now(tz=KST) - last) < timedelta(hours=max_age_hours):
            return
        def _bg():
            try:
                if name == "feature_groups":
                    self.sync_groups()
                elif name == "import_runs":
                    self.sync_runs()
                elif name == "feature_record_logs":
                    self.sync_logs()
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    @staticmethod
    def format_last_sync(dt: Optional[datetime]) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S KST") if dt else "-"
