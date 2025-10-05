"""Streamlit entry point implementing the dual cloud/on-prem workflow."""
from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from app.core.navigation import get_pages
from app.data.runtime_loader import load_runtime_context
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


def main():
    st.set_page_config(page_title="Feature Monitoring Portal", layout="wide")

    filter_state = _init_session_state()
    context = load_runtime_context()

    dataframe = context.dataframe
    st.session_state["data_manager"] = context.data_manager
    st.session_state["last_sync_txt"] = context.last_sync_text
    st.session_state["active_dataframe"] = dataframe

    selected_label = _render_sidebar(filter_state, dataframe)
    pages = {page.label: page.renderer for page in get_pages()}

    updated_state = pages[selected_label](filter_state, dataframe)
    st.session_state.filter_state = updated_state


if __name__ == "__main__":
    main()
