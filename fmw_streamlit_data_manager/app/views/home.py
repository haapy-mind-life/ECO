from __future__ import annotations
import streamlit as st
import pandas as pd
from app.data.data_manager import DataManager
from app.data.api import list_feature_records, list_features, list_feature_groups
from app.data.sample_features import ensure_columns

dm = DataManager()

def _sidebar_filters():
    st.sidebar.header("탐색(사이드바)")
    groups = list_feature_groups()
    group_names = [g.get("name") for g in groups] if isinstance(groups, list) else []
    sel_group = st.sidebar.selectbox("Feature Group", group_names) if group_names else None

    feat_names: list[str] = []
    if sel_group:
        feats = list_features(sel_group)
        feat_names = [f.get("name") for f in feats] if isinstance(feats, list) else []

    sel_feature = st.sidebar.selectbox("Feature", feat_names) if feat_names else None

    # 상세 필터
    st.sidebar.subheader("상세 필터")
    model = st.sidebar.text_input("Model(포함 검색)")
    operator = st.sidebar.text_input("Operator(포함 검색)")
    region = st.sidebar.text_input("Region(=)")
    country = st.sidebar.text_input("Country(=)")
    mode = st.sidebar.selectbox("Mode", ["", "allow", "block"], index=0)
    run_query = st.sidebar.button("데이터 조회")

    return sel_group, sel_feature, {"model": model, "operator": operator, "region": region, "country": country, "mode": mode}, run_query

def render_home():
    st.title("FMW Overview")
    st.caption("06:00 자동 동기화 + 수동 실행, 변경 이력 확인, 그룹→피처→필터 탐색 구조")

    # 캐시가 비어 있으면 백그라운드로 기본 동기화 유도
    dm.refresh_if_stale("feature_groups", max_age_hours=24)
    dm.refresh_if_stale("import_runs", max_age_hours=1)

    # 사이드바
    sel_group, sel_feature, filters, run_query = _sidebar_filters()

    # 오버뷰 카드 (간단)
    col1, col2, col3 = st.columns(3)
    runs_df = dm.runs()
    col1.metric("최근 Run 수", int(len(runs_df)))
    col2.metric("마지막 그룹 동기화", dm.format_last_sync(dm.last_sync_at("feature_groups")))
    col3.metric("마지막 로그 동기화", dm.format_last_sync(dm.last_sync_at("feature_record_logs")))

    st.divider()

    st.subheader("데이터 조회")
    if run_query and sel_group and sel_feature:
        # API로 최신 조회 후 캐시 저장
        df = dm.sync_records(sel_group, sel_feature,
                             model=filters.get("model") or None,
                             operator=filters.get("operator") or None,
                             region=filters.get("region") or None,
                             country=filters.get("country") or None,
                             mode=(filters.get("mode") or None) if filters.get("mode") else None)
        df = ensure_columns(df)
        st.dataframe(df, use_container_width=True)
        st.download_button("CSV 다운로드", df.to_csv(index=False).encode("utf-8"), file_name=f"{sel_group}_{sel_feature}.csv", mime="text/csv")
    else:
        st.info("사이드바에서 그룹과 피처를 선택하고 '데이터 조회'를 클릭하세요.")
