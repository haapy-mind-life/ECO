"""Home view that focuses on feature discovery and filtering."""
from __future__ import annotations

import streamlit as st

from app.data.sample_features import distinct_values
from app.views.state import FilterState


def _multiselect(label: str, options, default, key: str):
    return st.multiselect(
        label,
        options,
        default=default,
        key=key,
        placeholder="검색하거나 값을 입력하세요",
    )


def render_home(filter_state: FilterState, dataframe):
    """Render the main landing page with detailed filters."""

    st.title("📊 Feature Monitoring Home")
    st.caption(
        "필터를 선택하면 중앙 영역에 해당 FEATURE GROUP의 레코드가 즉시 표시됩니다."
    )

    st.markdown(
        """
        - 좌측 사이드바에서 **모델**과 **FEATURE GROUP**을 선택하면 전체 필터가 좁혀집니다.
        - 아래 상세 필터에서 MCC, MNC, 국가/사업자 등을 추가로 지정해 원하는 레코드를 찾을 수 있습니다.
        - 선택한 레코드는 테이블 형태로 표시되어 바로 운영자가 검토할 수 있습니다.
        """
    )

    st.subheader("상세 필터")
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_state.mcc = _multiselect(
            "MCC",
            distinct_values("mcc"),
            filter_state.mcc,
            "home_mcc",
        )
        filter_state.mnc = _multiselect(
            "MNC",
            distinct_values("mnc"),
            filter_state.mnc,
            "home_mnc",
        )

    with col2:
        filter_state.regions = _multiselect(
            "지역",
            distinct_values("region"),
            filter_state.regions,
            "home_region",
        )
        filter_state.countries = _multiselect(
            "국가",
            distinct_values("country"),
            filter_state.countries,
            "home_country",
        )

    with col3:
        filter_state.operators = _multiselect(
            "사업자",
            distinct_values("operator"),
            filter_state.operators,
            "home_operator",
        )
        filter_state.features = _multiselect(
            "FEATURE",
            distinct_values("feature_name"),
            filter_state.features,
            "home_feature",
        )

    filtered_df = filter_state.apply(dataframe)

    st.divider()
    st.subheader("선택한 FEATURE GROUP 레코드")

    st.write(
        f"총 **{len(filtered_df)}**건이 선택되었습니다. 필요한 데이터를 바로 다운로드할 수 있도록 준비 중입니다."
    )

    st.dataframe(
        filtered_df,
        hide_index=True,
        use_container_width=True,
    )

    st.info(
        "해당 화면은 한 명의 담당자가 운영하도록 설계되었습니다. 홈 화면에서 바로 필터를 적용한 후 데이터를 검토하고 관리할 수 있습니다."
    )

    return filter_state
