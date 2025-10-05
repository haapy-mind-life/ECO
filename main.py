"""Streamlit entry point implementing the dual cloud/on-prem workflow."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import List

import pandas as pd
import requests
import streamlit as st

from app.core.navigation import get_pages
from app.data.data_manager import DataManager
from app.data.sample_features import load_feature_dataframe
from app.views.state import FilterState


def _init_session_state() -> FilterState:
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = FilterState()
    return st.session_state.filter_state


def _sorted_unique(dataframe: pd.DataFrame, column: str) -> List[str]:
    if column in dataframe.columns:
        values = dataframe[column].dropna().astype(str).unique().tolist()
        values.sort()
        return values
    return []


def _render_sidebar(filter_state: FilterState, dataframe: pd.DataFrame) -> str:
    pages = get_pages()
    labels = [page.label for page in pages]

    st.sidebar.title("🧭 내비게이션")
    selected_label = st.sidebar.radio(
        "메인 기능",
        labels,
        key="main_navigation",
    )

    selected_page = next(page for page in pages if page.label == selected_label)
    if selected_page.description:
        st.sidebar.caption(selected_page.description)

    st.sidebar.divider()
    st.sidebar.subheader("공통 필터")

    model_options = _sorted_unique(dataframe, "model")
    feature_group_options = _sorted_unique(dataframe, "feature_group")

    if not model_options:
        model_options = _sorted_unique(load_feature_dataframe(), "model")
    if not feature_group_options:
        feature_group_options = _sorted_unique(load_feature_dataframe(), "feature_group")

    filter_state.models = st.sidebar.multiselect(
        "모델",
        model_options,
        default=filter_state.models,
        key="sidebar_models",
        placeholder="모델을 선택하세요",
    )
    filter_state.feature_groups = st.sidebar.multiselect(
        "FEATURE GROUP",
        feature_group_options,
        default=filter_state.feature_groups,
        key="sidebar_feature_groups",
        placeholder="FEATURE GROUP을 선택하세요",
    )

    st.sidebar.caption("선택한 항목은 모든 화면의 데이터 필터에 바로 반영됩니다.")

    st.sidebar.divider()
    st.sidebar.subheader("확장 앱")
    st.sidebar.caption("추가 기능(챗봇, 자동화 등)을 연결할 영역입니다.")

    return selected_label


@st.cache_data(ttl=86400)
def _cloud_fetch_feature1(api_base: str, verify_ssl: bool, token: str | None) -> tuple[pd.DataFrame, int]:
    """Fetch feature data from the public staging API (cloud mode)."""

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


def main():
    st.set_page_config(page_title="Feature Monitoring Portal", layout="wide")

    filter_state = _init_session_state()

    runtime_mode = st.secrets.get("RUNTIME_MODE", os.getenv("RUNTIME_MODE", "cloud")).lower()
    api_base = st.secrets.get("API_BASE", os.getenv("API_BASE", "https://10.x.x.x"))
    verify_ssl = _bool(str(st.secrets.get("VERIFY_SSL", os.getenv("VERIFY_SSL", "false"))))
    token = st.secrets.get("API_ACCESS_TOKEN", os.getenv("API_ACCESS_TOKEN"))
    data_dir = os.getenv("DATA_DIR", "./_cache")

    if runtime_mode == "cloud":
        try:
            dataframe, last_epoch = _cloud_fetch_feature1(api_base, verify_ssl, token)
            st.session_state["data_manager"] = None
            if dataframe.empty:
                dataframe = load_feature_dataframe()
                st.session_state["last_sync_txt"] = "샘플 데이터(Cloud API 미접속)"
            else:
                last_sync = datetime.fromtimestamp(last_epoch, tz=timezone.utc)
                st.session_state["last_sync_txt"] = DataManager.format_last_sync(last_sync)
        except Exception:
            dataframe = load_feature_dataframe()
            st.session_state["data_manager"] = None
            st.session_state["last_sync_txt"] = "샘플 데이터(Cloud API 미접속)"
    else:
        data_manager = DataManager(
            api_base=api_base,
            data_dir=data_dir,
            verify_ssl=verify_ssl,
            token=token,
        )
        st.session_state["data_manager"] = data_manager
        data_manager.refresh_if_stale("feature1", max_age_hours=24)
        dataframe = data_manager.load("feature1")
        if dataframe.empty:
            dataframe = load_feature_dataframe()
        st.session_state["last_sync_txt"] = DataManager.format_last_sync(
            data_manager.last_sync_at("feature1")
        )

    st.session_state["active_dataframe"] = dataframe

    selected_label = _render_sidebar(filter_state, dataframe)
    pages = {page.label: page.renderer for page in get_pages()}

    updated_state = pages[selected_label](filter_state, dataframe)
    st.session_state.filter_state = updated_state


if __name__ == "__main__":
    main()
