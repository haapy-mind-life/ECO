"""Runtime-aware data loading helpers for the Streamlit app."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
import streamlit as st

from .data_manager import DataManager
from .sample_features import load_feature_dataframe


@dataclass(frozen=True)
class RuntimeContext:
    """Encapsulates the dataset and metadata required by the UI."""

    dataframe: pd.DataFrame
    last_sync_text: str
    data_manager: Optional[DataManager]


@st.cache_data(ttl=86400)
def _cloud_fetch_feature1(
    api_base: str, verify_ssl: bool, token: str | None
) -> tuple[pd.DataFrame, int]:
    """Fetch feature data from the staging API when running on Streamlit Cloud."""

    url = f"{api_base.rstrip('/')}/api/feature1/"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, timeout=20, verify=verify_ssl, headers=headers)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "results" in payload:
        payload = payload["results"]
    dataframe = pd.DataFrame(payload)
    return dataframe, int(time.time())


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_runtime_context() -> RuntimeContext:
    """Return the dataset and metadata for the current runtime environment."""

    runtime_mode = st.secrets.get("RUNTIME_MODE", os.getenv("RUNTIME_MODE", "cloud")).lower()
    api_base = st.secrets.get("API_BASE", os.getenv("API_BASE", "https://10.x.x.x"))
    verify_ssl = _bool(str(st.secrets.get("VERIFY_SSL", os.getenv("VERIFY_SSL", "false"))))
    token = st.secrets.get("API_ACCESS_TOKEN", os.getenv("API_ACCESS_TOKEN"))
    data_dir = os.getenv("DATA_DIR", "./_cache")

    if runtime_mode == "cloud":
        try:
            dataframe, last_epoch = _cloud_fetch_feature1(api_base, verify_ssl, token)
            if dataframe.empty:
                last_sync_text = "샘플 데이터(Cloud API 미접속)"
                dataframe = load_feature_dataframe()
            else:
                last_sync = datetime.fromtimestamp(last_epoch, tz=timezone.utc)
                last_sync_text = DataManager.format_last_sync(last_sync)
            return RuntimeContext(dataframe=dataframe, last_sync_text=last_sync_text, data_manager=None)
        except Exception:
            return RuntimeContext(
                dataframe=load_feature_dataframe(),
                last_sync_text="샘플 데이터(Cloud API 미접속)",
                data_manager=None,
            )

    data_manager = DataManager(
        api_base=api_base,
        data_dir=data_dir,
        verify_ssl=verify_ssl,
        token=token,
    )
    data_manager.refresh_if_stale("feature1", max_age_hours=24)
    dataframe = data_manager.load("feature1")
    if dataframe.empty:
        dataframe = load_feature_dataframe()
    last_sync_text = DataManager.format_last_sync(data_manager.last_sync_at("feature1"))
    return RuntimeContext(dataframe=dataframe, last_sync_text=last_sync_text, data_manager=data_manager)
