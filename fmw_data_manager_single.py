
# FMW 데이터 매니저 (단일 파일 / CSV 리더)
# 사용법:
#   streamlit run fmw_data_manager_single.py
# 기본 동작:
#   - 같은 폴더의 fmw_sample_data.csv 를 자동 로드
#   - 없으면 사이드바에서 CSV 업로드
#   - 좌측: 그룹 → 피처 → 상세 필터 → 조회
#   - 필터링 결과 다운로드 가능

import os
import io
from typing import Optional
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(__file__)
DEFAULT_CSV = os.path.join(APP_DIR, "fmw_sample_data.csv")
REQUIRED_COLUMNS = [
    "feature_group","feature_name","model_name","mcc","mnc",
    "region","country","operator","sp_fci","mode","value","status","updated_at"
]

st.set_page_config(page_title="FMW 데이터 매니저 (단일파일)", layout="wide", page_icon="🗂️")

@st.cache_data
def read_csv_safe(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 모든 필요한 컬럼이 존재하도록 보정
    for c in REQUIRED_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    # 문자열로 통일 (필터 편의)
    for c in REQUIRED_COLUMNS:
        df[c] = df[c].astype(str)
    return df[REQUIRED_COLUMNS]

def load_data() -> Optional[pd.DataFrame]:
    df = None
    # 1) 루트에 기본 CSV 있으면 자동 로드
    if os.path.exists(DEFAULT_CSV):
        try:
            df = read_csv_safe(DEFAULT_CSV)
        except Exception as e:
            st.warning(f"기본 CSV 로드 실패: {e}")
            df = None
    # 2) 사이드바 업로드 우선 적용
    up = st.sidebar.file_uploader("CSV 업로드 (선택)", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up, dtype=str, keep_default_na=False)
        except Exception as e:
            st.error(f"업로드 CSV 읽기 실패: {e}")
    return df

def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("탐색")
    groups = sorted(df["feature_group"].dropna().unique().tolist())
    group = st.sidebar.selectbox("Feature Group", [""] + groups)
    feats = sorted(df.loc[df["feature_group"].eq(group), "feature_name"].dropna().unique().tolist()) if group else []
    feature = st.sidebar.selectbox("Feature", [""] + feats) if feats else ""

    st.sidebar.subheader("상세 필터")
    model = st.sidebar.text_input("Model 포함")
    operator = st.sidebar.text_input("Operator 포함")
    region = st.sidebar.text_input("Region =")
    country = st.sidebar.text_input("Country =")
    mcc = st.sidebar.text_input("MCC =")
    mnc = st.sidebar.text_input("MNC =")
    mode = st.sidebar.selectbox("Mode", ["", "allow", "block"], index=0)
    run = st.sidebar.button("데이터 조회")

    return {
        "group": group,
        "feature": feature,
        "model_like": model,
        "operator_like": operator,
        "region": region,
        "country": country,
        "mcc": mcc,
        "mnc": mnc,
        "mode": mode,
        "run": run,
    }

def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    q = df.copy()
    if f["group"]:
        q = q[q["feature_group"] == f["group"]]
    if f["feature"]:
        q = q[q["feature_name"] == f["feature"]]
    if f["mode"]:
        q = q[q["mode"] == f["mode"]]
    if f["region"]:
        q = q[q["region"] == f["region"]]
    if f["country"]:
        q = q[q["country"] == f["country"]]
    if f["mcc"]:
        q = q[q["mcc"] == f["mcc"]]
    if f["mnc"]:
        q = q[q["mnc"] == f["mnc"]]
    if f["model_like"]:
        q = q[q["model_name"].str.contains(f["model_like"], case=False, na=False)]
    if f["operator_like"]:
        q = q[q["operator"].str.contains(f["operator_like"], case=False, na=False)]
    return q

def overview(df: pd.DataFrame):
    st.subheader("오버뷰")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("행 개수", len(df))
    c2.metric("모델 수", df["model_name"].nunique())
    c3.metric("그룹 수", df["feature_group"].nunique())
    c4.metric("피처 수", df["feature_name"].nunique())

def main():
    st.title("FMW 데이터 매니저 (CSV 샘플, 단일 파일)")
    st.caption("루트의 fmw_sample_data.csv 를 읽거나, 좌측에서 CSV 업로드")

    df = load_data()
    if df is None:
        st.error("CSV 데이터가 없습니다. 루트에 fmw_sample_data.csv 를 두거나 업로드하세요.")
        st.stop()

    df = ensure_columns(df)
    overview(df)

    st.divider()
    filters = sidebar_filters(df)
    st.subheader("데이터 조회")
    if filters["run"]:
        out = apply_filters(df, filters)
        st.dataframe(out, use_container_width=True)
        st.download_button("CSV 다운로드", out.to_csv(index=False).encode("utf-8"), file_name="filtered.csv", mime="text/csv")
    else:
        st.info("좌측에서 그룹/피처 선택 후 '데이터 조회'를 눌러주세요.")

if __name__ == "__main__":
    main()
