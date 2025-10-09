from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd  # type: ignore

import re

import streamlit as st

from app.data.data_manager import DataManager
from app.data.sample_features import FEATURE_GROUP_SCHEMA, distinct_values
from app.views.state import FilterState


def _sanitize_default(default, options):
    if default is None:
        return []
    if not isinstance(default, (list, tuple, set)):
        default = [default]
    opts = set(options or [])
    return [v for v in default if v in opts]

def _mccmnc_ok(s: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{2}", s.strip()))

def _multiselect(label: str, options, default, key: str):
    default = _sanitize_default(default, options)
    return st.multiselect(label, options, default=default, key=key, placeholder="검색하거나 값을 입력하세요")


def render_home(filter_state: FilterState, dataframe: "pd.DataFrame"):
    st.title("📊 Feature Monitoring Home")

    # 마지막 DB 싱크 시각
    last_sync_txt = "-"
    dm: DataManager | None = st.session_state.get("data_manager")
    if dm:
        last = dm.last_sync_at("feature1")
        last_sync_txt = dm.format_last_sync(last)
    else:
        last_sync_txt = st.session_state.get("last_sync_txt", "-")
    st.caption(f"마지막 DB 싱크: **{last_sync_txt}** · 싱크 주기: **매일 1회** · 조회 전용")

    # 그룹 인지형: 선택된 그룹에 따라 사용 차원 제어
    # 단일 그룹 선택 시 해당 스키마, 복수 선택이면 모든 차원 노출(보수적)
    dims = {"region","country","operator","mcc_mnc"}
    if filter_state.feature_groups and len(filter_state.feature_groups) == 1:
        g = filter_state.feature_groups[0]
        dims = set(FEATURE_GROUP_SCHEMA.get(g, {}).get("dims", list(dims)))

    st.subheader("상세 필터")
    col1, col2, col3 = st.columns(3)

    with col1:
        if "mcc_mnc" in dims:
            # MCC/MNC는 원본 컬럼이 mcc,mnc로 올 수 있으므로 입력은 NNN-NN
            mccmnc = st.text_input("MCC-MNC(정확히: NNN-NN)", key="home_mccmnc", placeholder="예: 450-05")
            if mccmnc and not _mccmnc_ok(mccmnc):
                st.error("MCC-MNC 형식은 NNN-NN (예: 450-05)")
                st.stop()
            # 필터에 반영: mcc, mnc 분해
            if mccmnc:
                try:
                    mcc, mnc = mccmnc.split("-")
                    filter_state.mcc = [mcc]
                    filter_state.mnc = [mnc]
                except Exception:
                    pass
        else:
            filter_state.mcc, filter_state.mnc = [], []

    with col2:
        if "region" in dims:
            filter_state.regions = _multiselect("지역", distinct_values("region"), filter_state.regions, "home_region")
        else:
            filter_state.regions = []
        if "country" in dims:
            filter_state.countries = _multiselect("국가", distinct_values("country"), filter_state.countries, "home_country")
        else:
            filter_state.countries = []

    with col3:
        if "operator" in dims:
            filter_state.operators = _multiselect("사업자", distinct_values("operator"), filter_state.operators, "home_operator")
        else:
            filter_state.operators = []
        filter_state.features = _multiselect("FEATURE", distinct_values("feature_name"), filter_state.features, "home_feature")

    filtered_df = filter_state.apply(dataframe).copy()

    # KPI
    st.divider()
    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("행 수", len(filtered_df))
    with k2: st.metric("모델 수", int(filtered_df["model"].nunique()) if not filtered_df.empty and "model" in filtered_df else 0)
    with k3: st.metric("FEATURE 수", int(filtered_df["feature_name"].nunique()) if not filtered_df.empty and "feature_name" in filtered_df else 0)
    with k4: st.metric("사업자 수", int(filtered_df["operator"].nunique()) if not filtered_df.empty and "operator" in filtered_df else 0)

    # 빈 결과 가이드
    if filtered_df.empty:
        st.warning("조건에 맞는 결과가 없습니다.")
        with st.expander("추천 검색 보기"):
            st.write("• 인기 FEATURE:", ", ".join(distinct_values("feature_name")[:5]))
            st.write("• 인기 사업자:", ", ".join(distinct_values("operator")[:5]))
            st.write("• 인기 MCC:", ", ".join(distinct_values("mcc")[:5]))
        return filter_state

    # 표 가독성: status 배지화
    if "status" in filtered_df.columns:
        def _badge(x: str) -> str:
            x = (x or "").lower()
            if "avail" in x: return "🟢 Available"
            if "pilot" in x: return "🟡 Pilot"
            if "plan" in x or "progress" in x: return "🔵 Planned"
            return x or "-"
        filtered_df["status"] = filtered_df["status"].map(_badge)

    # 표시 컬럼 우선순위
    preferred = ["feature_group","feature_name","model","region","country","operator","mcc","mnc","status","last_updated"]
    cols = [c for c in preferred if c in filtered_df.columns] + [c for c in filtered_df.columns if c not in preferred]

    st.subheader("검색 결과")
    st.dataframe(filtered_df[cols], hide_index=True, use_container_width=True)

    # CSV 다운로드 가드(2만 행)
    st.divider()
    st.subheader("⬇️ CSV 다운로드")
    row_limit = 20000
    if len(filtered_df) > row_limit:
        st.error(f"보안 정책에 따라 최대 {row_limit:,}행까지 다운로드할 수 있습니다. 현재: {len(filtered_df):,}행")
    else:
        agree = st.checkbox("사내 데이터 보안 정책에 동의합니다.")
        st.caption("※ 외부 반출 금지, 내부 업무 목적에 한함")
        if agree:
            st.download_button(
                "CSV 저장",
                data=filtered_df[cols].to_csv(index=False).encode("utf-8-sig"),
                file_name="feature_records.csv",
                mime="text/csv",
            )

    return filter_state
