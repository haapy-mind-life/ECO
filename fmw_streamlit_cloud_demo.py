# fmw_streamlit_cloud_demo.py
# Streamlit Cloud UX Check — Single-file demo (v1.0, 2025-10-24)
# 요구 패키지: streamlit, pandas, requests, python-dateutil
# 실행: streamlit run fmw_streamlit_cloud_demo.py

import io, os, time, json, random, requests, pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

KST = timezone(timedelta(hours=9))

# =========================================
# 0) DEMO 데이터 생성기 (내장 샘플, 500 rows)
# =========================================
RNG = random.Random(20251024)

MODELS = [f"S{20+i}" for i in range(10)]  # 10 models
SOLUTIONS = ["slsi", "mtk"]
GROUPS = {
    "Connectivity": ["VoLTE", "VoWiFi", "5G_SA", "5G_NSA"],
    "Messaging": ["SMS", "MMS", "RCS"],
    "Data": ["APN", "Throttle", "Hotspot", "DualSIM"],
    "Roaming": ["Roaming", "RoamVoLTE", "DataCap"],
}
COUNTRIES = ["KR","US","JP","TW","DE","GB","FR","SG","VN","IN"]
OPERATORS = ["KT","SKT","LGU+","KDDI","DOCOMO","SOFTBANK","VERIZON","ATT","TMOBILE","VODAFONE"]
REGIONS = ["APAC","NA","EU","LATAM","MEA"]
SP_FCI = ["postpaid","prepaid","mvno","corp","vip"]

def _pick_or_none(options, p_none=0.25):
    if RNG.random() < p_none:
        return None
    return RNG.choice(options)

def _random_value(feature):
    # value는 feature 성격에 맞춰 bool/num/str 혼용
    r = RNG.random()
    if "5G" in feature or feature in ("Hotspot","DataCap","Throttle"):
        if r < 0.5: return bool(RNG.getrandbits(1))
        elif r < 0.8: return RNG.randint(1, 100)  # 예: 제한 숫자
        else: return f"level-{RNG.randint(1,5)}"
    else:
        return bool(RNG.getrandbits(1))

def make_demo_df(seed_offset=0, size=500):
    rng = random.Random(20251024 + seed_offset)
    rows = []
    seen = set()
    while len(rows) < size:
        model = rng.choice(MODELS)
        sol = rng.choice(SOLUTIONS)
        group = rng.choice(list(GROUPS.keys()))
        feat = rng.choice(GROUPS[group])
        mcc = _pick_or_none([str(rng.randint(200, 999))], p_none=0.6)  # 자주 없음
        mnc = _pick_or_none([str(rng.randint(0, 99)).zfill(2)], p_none=0.6)
        region = _pick_or_none(REGIONS, p_none=0.5)
        country = _pick_or_none(COUNTRIES, p_none=0.4)
        operator = _pick_or_none(OPERATORS, p_none=0.5)
        sp_fci = _pick_or_none(SP_FCI, p_none=0.5)
        mode = rng.choice(["allow","block","none"])
        value = _random_value(feat)
        sync_time = datetime.now(KST).isoformat(timespec="seconds")

        key = (model, sol, group, feat, mcc, mnc, region, country, operator, sp_fci, mode)
        if key in seen: 
            continue
        seen.add(key)
        rows.append({
            "model_name": model,
            "solution": sol,
            "feature_group": group,
            "feature": feat,
            "mcc": mcc,
            "mnc": mnc,
            "region": region,
            "country": country,
            "operator": operator,
            "sp_fci": sp_fci,
            "mode": mode,
            "value": value,
            "sync_time": sync_time,
        })
    return pd.DataFrame(rows)

def tweak_df_for_yesterday(df_today):
    """오늘 df를 기반으로 '어제' 데이터 시뮬레이션 (생성/업데이트/삭제 약간씩)"""
    df_prev = df_today.copy()
    n = len(df_prev)
    # 삭제: 5%
    del_idx = RNG.sample(range(n), k=max(1, n//20))
    df_prev = df_prev.drop(index=del_idx).reset_index(drop=True)
    # 생성: 5% 추가
    add = make_demo_df(seed_offset=1, size=max(1, n//20)).sample(n=max(1, n//20), random_state=42)
    df_prev = pd.concat([df_prev, add], ignore_index=True)
    # 업데이트: 5% value 변경
    upd_idx = RNG.sample(range(len(df_prev)), k=max(1, len(df_prev)//20))
    for i in upd_idx:
        df_prev.at[i, "value"] = _random_value(df_prev.at[i, "feature"])
    # sync_time 과거로
    ts = (datetime.now(KST) - timedelta(days=1)).isoformat(timespec="seconds")
    df_prev["sync_time"] = ts
    return df_prev

# =========================================
# 1) DRF 로더 (선택) — BASE_URL 설정 시 사용
# =========================================
def load_from_drf(base_url: str, params=None):
    t0 = time.time()
    url = f"{base_url.rstrip('/')}/api/v1/all"
    r = requests.get(url, params=params or {}, headers={"Accept":"text/csv"}, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    latency_ms = int((time.time() - t0)*1000)
    return df, latency_ms

# =========================================
# 2) 공통 유틸
# =========================================
KEY_COLS = ["model_name","solution","feature_group","feature","mcc","mnc","region","country","operator","sp_fci","mode"]
def _build_key(df: pd.DataFrame):
    return df[KEY_COLS].astype(str).agg("|".join, axis=1)

def diff_prev_curr(prev_df, curr_df):
    import pandas as pd
    if prev_df is None or prev_df.empty:
        return pd.DataFrame(columns=KEY_COLS+["value","change_type"]), \
               pd.DataFrame(columns=KEY_COLS+["old_value","new_value","change_type"]), \
               pd.DataFrame(columns=KEY_COLS+["value","change_type"])
    p, c = prev_df.copy(), curr_df.copy()
    p["_key"] = _build_key(p); c["_key"] = _build_key(c)
    created_keys = set(c["_key"]) - set(p["_key"])
    deleted_keys = set(p["_key"]) - set(c["_key"])
    created = c[c["_key"].isin(created_keys)].copy()
    created["change_type"] = "created"
    deleted = p[p["_key"].isin(deleted_keys)].copy()
    deleted["change_type"] = "deleted"
    merged = c.merge(p[["_key","value"]].rename(columns={"value":"old_value"}), on="_key", how="inner")
    updated = merged[merged["value"].astype(str) != merged["old_value"].astype(str)].copy()
    if not updated.empty:
        # 안전 장치: KEY_COLS 누락 대비
        for col in KEY_COLS:
            if col not in updated.columns:
                updated[col] = None
        updated["new_value"] = updated["value"]
        updated["change_type"] = "updated"
        updated = updated[KEY_COLS+["old_value","new_value","change_type"]]
    created = created[KEY_COLS+["value","change_type"]].sort_values(KEY_COLS, kind="stable")
    deleted = deleted[KEY_COLS+["value","change_type"]].sort_values(KEY_COLS, kind="stable")
    if not updated.empty:
        updated = updated.sort_values(KEY_COLS, kind="stable")
    return created, updated, deleted

def filter_df(df, model, group):
    if df is None or df.empty: return df
    out = df.copy()
    if model and model != "(전체)":
        out = out[out["model_name"] == model]
    if group and group != "(전체)":
        out = out[out["feature_group"] == group]
    return out

# =========================================
# 3) UI — Streamlit Cloud UX 체크
# =========================================
st.set_page_config(page_title="fmw — Cloud Demo", layout="wide")
st.markdown("<h1 style='margin-bottom:0'>fmw</h1><div style='color:#888;margin-top:-6px'>Streamlit Cloud UX 데모</div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("모드 선택")
    mode = st.radio("데이터 소스", ["데모 모드(내장 샘플)", "DRF 모드(실서버)"], index=0)
    st.divider()

    st.header("필터")
    # 미리 만들어서 모델/그룹 목록 추출
    demo_today = make_demo_df()
    demo_yesterday = tweak_df_for_yesterday(demo_today)
    model_opts = ["(전체)"] + sorted([m for m in demo_today["model_name"].dropna().unique()])
    group_opts = ["(전체)"] + sorted([g for g in demo_today["feature_group"].dropna().unique()])
    sel_model = st.selectbox("모델", model_opts, index=0)
    sel_group = st.selectbox("피처 그룹", group_opts, index=0)

    st.divider()
    st.caption("※ UX 체크용. 실제 운영에서는 dev 기능 제거.")
    dev_col1, dev_col2 = st.columns(2)
    with dev_col1:
        show_latency = st.checkbox("지연시간 표시", value=True)
    with dev_col2:
        ttl = st.number_input("데모-재생성 주기(분)", min_value=5, max_value=1440, value=60, step=5, help="데모 데이터 재생성 주기")

# 데이터 로딩
latency_ms = None
if mode.startswith("DRF"):
    default_base = st.secrets.get("BASE_URL", "")
    base_url = st.text_input("DRF BASE_URL", value=default_base, placeholder="https://your-nginx-host")
    if st.button("불러오기(실서버)") and base_url.strip():
        try:
            df_all, latency_ms = load_from_drf(base_url.strip(), params={})
            # 서버에서 받은 데이터에도 기본 열이 있다고 가정
            df_prev = tweak_df_for_yesterday(df_all)  # UX 비교용 (실서버엔 dev summary 사용 권장)
        except Exception as e:
            st.error(f"로드 실패: {e}")
            df_all, df_prev = demo_today, demo_yesterday
    else:
        # 미리보기용(입력 전) 데모 사용
        df_all, df_prev = demo_today, demo_yesterday
else:
    # 데모 모드
    df_all, df_prev = demo_today, demo_yesterday

# 공통 필터 적용
df_view = filter_df(df_all, sel_model, sel_group)
df_prev_view = filter_df(df_prev, sel_model, sel_group)

# ---- 상단 오버뷰 카드 ----
created, updated, deleted = diff_prev_curr(df_prev_view, df_view)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("현재 레코드 수", len(df_view), delta=len(df_view) - len(df_prev_view))
with col2:
    st.metric("전일 신규", len(created))
with col3:
    st.metric("전일 업데이트", len(updated))
with col4:
    st.metric("전일 삭제", len(deleted))
if latency_ms is not None and show_latency:
    st.caption(f"서버 로드 지연시간: ~{latency_ms} ms")

st.divider()

# 좌측 라디오(한글 메뉴)
nav = st.radio("메뉴", ["히스토리 관리", "피처 상세", "데이터 탐색"], horizontal=True, index=0)

# ① 히스토리 관리 — CRUD
if nav == "히스토리 관리":
    st.subheader("히스토리 관리 (전일 대비 CRUD)")
    q = st.text_input("검색(전역 LIKE)")
    def _search(df):
        if df is None or df.empty or not q: return df
        ql = q.lower()
        return df[df.astype(str).apply(lambda s: s.str.lower().str.contains(ql, na=False)).any(axis=1)]

    t1, t2, t3 = st.tabs([
        f"신규 생성 ({len(created)})",
        f"업데이트 ({len(updated)})",
        f"삭제 ({len(deleted)})"
    ])

    with t1:
        st.dataframe(_search(created), use_container_width=True, height=360)
    with t2:
        st.dataframe(_search(updated), use_container_width=True, height=360)
    with t3:
        st.dataframe(_search(deleted), use_container_width=True, height=360)

# ② 피처 상세
elif nav == "피처 상세":
    st.subheader("피처 상세")
    if df_view is None or df_view.empty:
        st.info("데이터가 없습니다.")
    else:
        feats = ["(전체)"] + sorted(df_view["feature"].dropna().unique().tolist())
        feat_sel = st.selectbox("피처", feats, index=0)
        dff = df_view if feat_sel == "(전체)" else df_view[df_view["feature"] == feat_sel]

        c1, c2 = st.columns(2)
        with c1:
            st.write("모드 분포")
            st.bar_chart(dff["mode"].value_counts())
        with c2:
            st.write("국가 Top10")
            st.bar_chart(dff["country"].value_counts().head(10))

        st.divider()
        st.dataframe(dff, use_container_width=True, height=420)

# ③ 데이터 탐색
else:
    st.subheader("데이터 탐색")
    if df_view is None or df_view.empty:
        st.info("데이터가 없습니다.")
    else:
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            mode_sel = st.multiselect("Mode", options=sorted(df_view["mode"].dropna().unique()), default=[])
        with colf2:
            country_sel = st.multiselect("Country", options=sorted(df_view["country"].dropna().unique()), default=[])
        with colf3:
            op_sel = st.multiselect("Operator", options=sorted(df_view["operator"].dropna().unique()), default=[])

        dfx = df_view.copy()
        if mode_sel:    dfx = dfx[dffx := dfx["mode"].isin(mode_sel)].index or dfx[dfx["mode"].isin(mode_sel)]
        if country_sel: dfx = dfx[dfx["country"].isin(country_sel)]
        if op_sel:      dfx = dfx[dfx["operator"].isin(op_sel)]

        st.dataframe(dfx, use_container_width=True, height=420)
        st.bar_chart(dfx["feature"].value_counts().head(10))
