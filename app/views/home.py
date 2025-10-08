from __future__ import annotations
import pandas as pd
import streamlit as st
from app.data.data_manager import DataManager
from app.data.sample_features import distinct_values, FEATURE_GROUP_SCHEMA
from app.views.state import FilterState
import re

def _mccmnc_ok(s: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{2}", s.strip()))

def _multiselect(label: str, options, default, key: str, help_text: str | None = None):
    return st.multiselect(
        label,
        options,
        default=default,
        key=key,
        placeholder="검색하거나 값을 입력하세요",
        help=help_text,
    )


def render_home(filter_state: FilterState, dataframe: pd.DataFrame):
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
            mccmnc = st.text_input(
                "MCC-MNC(정확히: NNN-NN)",
                key="home_mccmnc",
                placeholder="예: 450-05",
                help="모바일 국가/사업자 코드. 예) 450-05는 한국 SKT",
            )
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
            st.session_state["home_mccmnc"] = ""

    with col2:
        if "region" in dims:
            filter_state.regions = _multiselect(
                "지역",
                distinct_values("region"),
                filter_state.regions,
                "home_region",
                help_text="대륙 또는 권역 단위입니다.",
            )
        else:
            filter_state.regions = []
        if "country" in dims:
            filter_state.countries = _multiselect(
                "국가",
                distinct_values("country"),
                filter_state.countries,
                "home_country",
                help_text="국가(ISO 명칭) 기준으로 좁혀볼 수 있습니다.",
            )
        else:
            filter_state.countries = []

    with col3:
        if "operator" in dims:
            filter_state.operators = _multiselect(
                "사업자",
                distinct_values("operator"),
                filter_state.operators,
                "home_operator",
                help_text="통신사/사업자명을 기준으로 필터링합니다.",
            )
        else:
            filter_state.operators = []
        filter_state.features = _multiselect(
            "FEATURE",
            distinct_values("feature_name"),
            filter_state.features,
            "home_feature",
            help_text="관심 있는 FEATURE 이름을 직접 선택합니다.",
        )

    with st.expander("고급 옵션(드문 조건)"):
        st.caption("자주 사용하지 않는 조건을 필요할 때만 펼쳐서 사용하세요.")
        if "status" in dataframe.columns:
            filter_state.statuses = _multiselect(
                "상태",
                distinct_values("status"),
                filter_state.statuses,
                "home_status",
                help_text="FEATURE 제공 상태(Available, Pilot 등)를 기준으로 필터링합니다.",
            )
        else:
            filter_state.statuses = []

        if "visualization_group" in dataframe.columns:
            filter_state.visualization_groups = _multiselect(
                "시각화 그룹",
                distinct_values("visualization_group"),
                filter_state.visualization_groups,
                "home_viz_group",
                help_text="각 FEATURE가 지원하는 시각화 번들을 선택합니다.",
            )
        else:
            filter_state.visualization_groups = []

    filtered_df = filter_state.apply(dataframe).copy()

    applied_filters: list[tuple[str, str, str]] = []
    for key, label, values in [
        ("models", "모델", filter_state.models),
        ("feature_groups", "FEATURE GROUP", filter_state.feature_groups),
        ("regions", "지역", filter_state.regions),
        ("countries", "국가", filter_state.countries),
        ("operators", "사업자", filter_state.operators),
        ("features", "FEATURE", filter_state.features),
        ("statuses", "상태", filter_state.statuses),
        ("visualization_groups", "시각화 그룹", filter_state.visualization_groups),
    ]:
        for value in values:
            applied_filters.append((key, label, value))

    if filter_state.mcc and filter_state.mnc and len(filter_state.mcc) == len(filter_state.mnc):
        for mcc, mnc in zip(filter_state.mcc, filter_state.mnc):
            applied_filters.append(("mcc_mnc", "MCC-MNC", f"{mcc}-{mnc}"))
    else:
        for value in filter_state.mcc:
            applied_filters.append(("mcc", "MCC", value))
        for value in filter_state.mnc:
            applied_filters.append(("mnc", "MNC", value))

    if applied_filters:
        st.write("**적용된 필터**")
        chip_cols = st.columns(min(6, len(applied_filters)))
        for idx, (key, label, value) in enumerate(applied_filters):
            col = chip_cols[idx % len(chip_cols)]
            if col.button(f"✕ {label}: {value}", key=f"chip_{key}_{idx}"):
                if key == "mcc_mnc":
                    try:
                        mcc, mnc = value.split("-", 1)
                    except ValueError:
                        mcc = value
                        mnc = ""
                    filter_state.mcc = [v for v in filter_state.mcc if v != mcc]
                    filter_state.mnc = [v for v in filter_state.mnc if v != mnc]
                else:
                    current = list(getattr(filter_state, key, []))
                    setattr(filter_state, key, [v for v in current if v != value])
                if key in {"mcc", "mnc", "mcc_mnc"} and not (filter_state.mcc or filter_state.mnc):
                    st.session_state["home_mccmnc"] = ""
                st.rerun()

    # KPI
    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("행 수", len(filtered_df))
    with k2:
        st.metric("모델 수", int(filtered_df["model"].nunique()) if not filtered_df.empty and "model" in filtered_df else 0)
    with k3:
        st.metric("FEATURE 수", int(filtered_df["feature_name"].nunique()) if not filtered_df.empty and "feature_name" in filtered_df else 0)
    with k4:
        st.metric("사업자 수", int(filtered_df["operator"].nunique()) if not filtered_df.empty and "operator" in filtered_df else 0)

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

    if "last_updated" in filtered_df.columns:
        filtered_df["last_updated"] = pd.to_datetime(filtered_df["last_updated"], errors="coerce")

    # 표시 컬럼 우선순위
    preferred = ["feature_group","feature_name","model","region","country","operator","mcc","mnc","status","last_updated"]
    cols = [c for c in preferred if c in filtered_df.columns] + [c for c in filtered_df.columns if c not in preferred]

    st.subheader("검색 결과")
    column_config: dict[str, object] = {}
    if "feature_group" in filtered_df.columns:
        column_config["feature_group"] = st.column_config.Column("FEATURE GROUP", pinned="left")
    if "feature_name" in filtered_df.columns:
        column_config["feature_name"] = st.column_config.Column("FEATURE", pinned="left")
    if "model" in filtered_df.columns:
        column_config["model"] = st.column_config.Column("MODEL", pinned="left")
    if "last_updated" in filtered_df.columns:
        column_config["last_updated"] = st.column_config.DateColumn("업데이트", format="distance", help="마지막 변경 시점과의 상대 시간을 표시합니다.")

    st.dataframe(
        filtered_df[cols],
        hide_index=True,
        use_container_width=True,
        column_config=column_config,
    )

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
