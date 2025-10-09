from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd  # type: ignore
import streamlit as st
from app.data.sample_features import visualization_capabilities, visualization_group_titles
from app.views.state import FilterState

def render_visualization(filter_state: FilterState, dataframe: "pd.DataFrame"):
    st.title("📈 시각화 작업 공간")
    st.info("이 영역은 **작업 중(WIP)** 입니다. 차트/지도 템플릿은 단계적으로 연결됩니다.")
    st.caption("선택한 FEATURE GROUP에 따라 사용 가능한 시각화가 달라집니다.")

    groups = filter_state.active_visualization_groups(dataframe)
    titles = visualization_group_titles()
    capabilities = visualization_capabilities()

    if not groups:
        st.info("사이드바와 홈 화면에서 FEATURE GROUP을 선택하면 여기에서 사용할 수 있는 시각화 유형이 노출됩니다.")
        return filter_state

    readable = [titles.get(group, group) for group in groups]
    selected_label = st.selectbox("시각화 그룹", readable, key="viz_group_selector")
    inverse_titles = {v: k for k, v in titles.items()}
    selected_group = inverse_titles.get(selected_label, selected_label)

    st.markdown("### 지원되는 시각화")
    for item in capabilities.get(selected_group, []):
        st.markdown(f"- {item}")

    # 간단 막대그래프(참고용)
    st.divider()
    st.markdown("### 미리보기(샘플)")
    base = filter_state.apply(dataframe)
    if base.empty:
        st.info("선택된 데이터가 없습니다. 홈에서 필터를 확장해 보세요.")
        return filter_state

    required_columns = {"model", "operator", "feature_name"}
    missing = required_columns - set(base.columns)
    if missing:
        readable = ", ".join(sorted(missing))
        st.warning(f"시각화 미리보기를 표시하려면 다음 컬럼이 필요합니다: {readable}")
        st.caption("데이터 소스에 해당 컬럼을 추가하거나 필터를 조정해 주세요.")
        return filter_state

    c1, c2 = st.columns(2)
    with c1:
        st.caption("모델별 FEATURE 개수")
        g = base.groupby("model")["feature_name"].nunique().reset_index(name="count").sort_values("count", ascending=False)
        st.bar_chart(g, x="model", y="count", use_container_width=True)
    with c2:
        st.caption("사업자별 FEATURE 개수")
        g2 = base.groupby("operator")["feature_name"].nunique().reset_index(name="count", ascending=False)
        g2["operator"] = g2["operator"].fillna("(N/A)")
        st.bar_chart(g2, x="operator", y="count", use_container_width=True)

    return filter_state
