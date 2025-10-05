"""Utilities for synchronising feature datasets with remote APIs.

This module keeps a lightweight abstraction for environments where the
application runs inside the company network (on-prem) and can reach the
protected Django REST API.  The implementation stores snapshots on disk in
Parquet format so repeated reads remain fast for the Streamlit app.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

_KST = timezone(timedelta(hours=9))


@dataclass(slots=True)
class DataManager:
    """Fetches feature datasets and caches them locally in Parquet files."""

    api_base: str
    data_dir: str
    verify_ssl: bool = True
    token: str | None = None
    timeout: int = 20

    def __post_init__(self) -> None:
        self._base = self.api_base.rstrip("/")
        self._dir = Path(self.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    def refresh_if_stale(self, key: str, *, max_age_hours: int = 24) -> bool:
        """Synchronise ``key`` if the cached dataset is older than ``max_age_hours``.

        Returns ``True`` when a refresh was attempted successfully.
        """

        last = self.last_sync_at(key)
        if last is not None:
            age = datetime.now(timezone.utc) - last
            if age < timedelta(hours=max_age_hours):
                return False
        try:
            self._sync(key)
            return True
        except requests.RequestException:
            # Network failures should not crash the Streamlit app; the caller can
            # fall back to the previously cached dataset or sample data.
            return False

    def load(self, key: str) -> pd.DataFrame:
        """Return the cached dataset for ``key`` or an empty frame."""

        path = self._dataset_path(key)
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)

    def last_sync_at(self, key: str) -> Optional[datetime]:
        """Return the last successful sync timestamp in UTC."""

        meta_path = self._meta_path(key)
        if not meta_path.exists():
            return None
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        raw = payload.get("last_sync")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def format_last_sync(value: Optional[datetime]) -> str:
        """Return a human friendly last-sync message in KST."""

        if value is None:
            return "미싱크"
        return value.astimezone(_KST).strftime("%Y-%m-%d %H:%M:%S KST")

    # ------------------------------------------------------------------
    # Internal helpers
    def _sync(self, key: str) -> None:
        response = self._fetch_remote(key)
        dataframe = self._normalise_payload(response)
        if dataframe.empty:
            # Persist an empty frame to avoid repeatedly hitting the API when
            # there is no data yet.
            dataframe = pd.DataFrame()
        dataframe.to_parquet(self._dataset_path(key), index=False)

        meta = {"last_sync": datetime.now(timezone.utc).isoformat()}
        self._meta_path(key).write_text(json.dumps(meta), encoding="utf-8")

    def _fetch_remote(self, key: str) -> Any:
        url = f"{self._base}/api/{key.strip('/')}/"
        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = requests.get(
            url,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalise_payload(payload: Any) -> pd.DataFrame:
        if isinstance(payload, dict) and "results" in payload:
            payload = payload["results"]
        if isinstance(payload, list):
            return pd.DataFrame.from_records(payload)
        if isinstance(payload, dict):
            return pd.DataFrame([payload])
        return pd.DataFrame()

    def _dataset_path(self, key: str) -> Path:
        return self._dir / f"{key}.parquet"

    def _meta_path(self, key: str) -> Path:
        return self._dir / f"{key}.meta.json"
