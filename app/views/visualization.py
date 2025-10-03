"""Visualization view that adapts to the selected feature groups."""
from __future__ import annotations

import streamlit as st

from app.data.sample_features import (
    visualization_capabilities,
    visualization_group_titles,
)
from app.views.state import FilterState


def render_visualization(filter_state: FilterState, dataframe):
    st.title("📈 Visualization Workspace")
    st.caption("선택된 FEATURE GROUP에 따라 사용 가능한 시각화 유형이 달라집니다.")

    groups = filter_state.active_visualization_groups(dataframe)
    titles = visualization_group_titles()
    capabilities = visualization_capabilities()

    if not groups:
        st.info(
            "사이드바와 홈 화면에서 FEATURE GROUP을 선택하면 여기에서 사용할 수 있는 시각화 유형이 노출됩니다."
        )
        st.stop()

    readable = [titles.get(group, group) for group in groups]
    default_label = readable[0]

    selected_label = st.selectbox(
        "시각화 그룹",
        readable,
        key="viz_group_selector",
    )

    # Map back to canonical key
    inverse_titles = {v: k for k, v in titles.items()}
    selected_group = inverse_titles.get(selected_label, selected_label)

    st.markdown("### 지원되는 시각화")
    for item in capabilities.get(selected_group, []):
        st.markdown(f"- {item}")

    st.divider()
    st.markdown("### 시각화 출력")

    if selected_group == "Tabular Only":
        st.success("현재 그룹은 표 기반 시각화만 지원합니다. 아래 표로 데이터를 확인하세요.")
        st.dataframe(
            filter_state.apply(dataframe),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success(
            "차트, 히트맵 지도, KPI 비교 등 다양한 시각화 템플릿을 순차적으로 배치할 예정입니다."
        )
        col1, col2 = st.columns(2)
        with col1:
            st.empty()
            st.warning("📊 라인 차트 영역 – 데이터 연동 대기 중")
        with col2:
            st.empty()
            st.warning("🗺️ 히트맵 지도 영역 – GIS 데이터 연동 대기 중")

        st.info("필요한 경우 아래 표로 세부 데이터를 동시에 확인할 수 있습니다.")
        st.dataframe(
            filter_state.apply(dataframe),
            hide_index=True,
            use_container_width=True,
        )

    st.caption("해당 공간은 시각화 담당자가 독립적으로 관리합니다.")
