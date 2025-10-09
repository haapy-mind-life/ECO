from __future__ import annotations

from typing import List, Tuple
import os, time, requests
import pandas as pd
import streamlit as st

from app.core.navigation import get_pages
from app.data.sample_features import distinct_values, load_feature_dataframe
from app.data.data_manager import DataManager
from app.views.state import FilterState

# ---------------- URL 상태 동기화 ---------------- #

def _init_session_state() -> FilterState:
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = FilterState()
    return st.session_state.filter_state

@st.cache_data(ttl=86400)  # Cloud: 하루 1회 동기화
def _cloud_fetch_feature1(api_base: str, verify_ssl: bool, token: str | None) -> Tuple[pd.DataFrame, int]:
    url = f"{api_base.rstrip('/')}/api/feature1/"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, timeout=20, verify=verify_ssl, headers=headers)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    df = pd.DataFrame(data)
    last = int(time.time())
    return df, last

def _read_qs_list(name: str) -> List[str]:
    qs = st.query_params
    if hasattr(qs, "get_all"):
        raw_values = qs.get_all(name)
    else:  # pragma: no cover - for older Streamlit fallbacks
        raw = qs.get(name, [])
        if isinstance(raw, str):
            raw_values = [raw]
        else:
            raw_values = list(raw)

    merged: List[str] = []
    for value in raw_values:
        if not value:
            continue
        merged.extend([piece.strip() for piece in value.split(",") if piece.strip()])
    return merged

def _sync_qs_from_state(state: FilterState) -> None:
    # st.query_params는 mapping-like proxy
    # 값이 비어있으면 키를 제거하고, 값이 존재하면 리스트로 설정한다.
    qp = st.query_params
    if state.models:
        qp["models"] = state.models
    elif "models" in qp:
        del qp["models"]

    if state.feature_groups:
        qp["feature_groups"] = state.feature_groups
    elif "feature_groups" in qp:
        del qp["feature_groups"]

# ---------------- 메인 앱 ---------------- #

def _render_sidebar(filter_state: FilterState) -> str:
    pages = get_pages()
    labels = [page.label for page in pages]

    st.sidebar.title("🧭 내비게이션")
    selected_label = st.sidebar.radio("메인 기능", labels, key="main_navigation")

    selected_page = next(p for p in pages if p.label == selected_label)
    if selected_page.description:
        st.sidebar.caption(selected_page.description)

    # 첫 진입 시 URL의 쿼리 파라미터를 공통 필터에 반영
    if not (filter_state.models or filter_state.feature_groups):
        from_qs_models = _read_qs_list("models")
        from_qs_groups = _read_qs_list("feature_groups")
        if from_qs_models:
            filter_state.models = from_qs_models
        if from_qs_groups:
            filter_state.feature_groups = from_qs_groups
        _sync_qs_from_state(filter_state)

    st.sidebar.divider()
    st.sidebar.subheader("공통 필터 (먼저 선택 권장)")

    # 기본값 sanitize: URL에서 들어온 값이 데이터 옵션에 없을 때 multiselect 에러 방지
    model_opts = distinct_values("model")
    if hasattr(filter_state, "models"):
        filter_state.models = [v for v in (filter_state.models or []) if v in model_opts]
    fg_opts = distinct_values("feature_group")
    if hasattr(filter_state, "feature_groups"):
        filter_state.feature_groups = [v for v in (filter_state.feature_groups or []) if v in fg_opts]

    filter_state.models = st.sidebar.multiselect(
        "모델",
        model_opts,
        default=filter_state.models,
        key="sidebar_models",
        placeholder="모델을 선택하세요",
    )
    filter_state.feature_groups = st.sidebar.multiselect(
        "FEATURE GROUP",
        fg_opts,
        default=filter_state.feature_groups,
        key="sidebar_feature_groups",
        placeholder="FEATURE GROUP을 선택하세요",
    )

    st.sidebar.caption("선택한 항목은 모든 화면의 데이터 필터에 바로 반영됩니다.")

    st.sidebar.divider()
    st.sidebar.subheader("확장 앱")
    st.sidebar.caption("추가 기능(챗봇, 자동화 등)을 연결할 영역입니다.")

    _sync_qs_from_state(filter_state)
    return selected_label


def main():
    st.set_page_config(page_title="Feature Monitoring Portal", layout="wide")

    # 런타임 모드 감지
    runtime_mode = st.secrets.get("RUNTIME_MODE", os.getenv("RUNTIME_MODE", "cloud")).lower()
    api_base = st.secrets.get("API_BASE", os.getenv("API_BASE", "https://10.x.x.x"))
    verify_ssl = bool(str(st.secrets.get("VERIFY_SSL", os.getenv("VERIFY_SSL", "false"))).lower() in ("1","true","yes"))
    token = st.secrets.get("API_ACCESS_TOKEN", os.getenv("API_ACCESS_TOKEN", None))
    data_dir = os.getenv("DATA_DIR", "./_cache")

    # 데이터프레임 로딩 (Cloud ↔ On-prem 자동 전환)
    if runtime_mode == "cloud":
        try:
            dataframe, last = _cloud_fetch_feature1(api_base, verify_ssl, token)
            st.session_state["data_manager"] = None
            st.session_state["last_sync_txt"] = time.strftime("%Y-%m-%d %H:%M:%S KST", time.gmtime(last + 9*3600))
        except Exception:
            dataframe = load_feature_dataframe()  # 샘플 폴백
            st.session_state["last_sync_txt"] = "샘플 데이터(Cloud API 미접속)"
    else:
        dm = DataManager(api_base=api_base, data_dir=data_dir, verify_ssl=verify_ssl)
        st.session_state["data_manager"] = dm
        dm.refresh_if_stale("feature1", max_age_hours=24)
        dataframe = dm.load("feature1")
        if dataframe.empty:
            dataframe = load_feature_dataframe()

    # 스키마 정합성 경고(개발자 편의)
    expected = {"feature_group","feature_name","model","mcc","mnc","region","country","operator","status","last_updated","visualization_group"}
    missing = expected - set(dataframe.columns)
    if missing:
        st.warning(f"데이터 컬럼 누락: {sorted(missing)} · 실제 연동 전 스키마를 맞춰주세요.")

    filter_state = _init_session_state()
    selected_label = _render_sidebar(filter_state)

    pages = {page.label: page.renderer for page in get_pages()}
    updated_state = pages[selected_label](filter_state, dataframe)
    st.session_state.filter_state = updated_state
    _sync_qs_from_state(updated_state)


if __name__ == "__main__":
    main()
