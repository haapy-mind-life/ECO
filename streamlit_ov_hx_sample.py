
"""
FMW — Overview + History (1/7/14/30) Streamlit Sample
- Includes sample data for:
  * /api/v1/all               -> CSV-like table
  * /api/dev/runs/summary     -> JSON for days=1|7|14|30
- Overview preset UX + History search UX
- Optional "Use API" toggle to call real endpoints; falls back to sample data

Run:
    streamlit run streamlit_ov_hx_sample.py
"""
from __future__ import annotations
import json
import hashlib
import io
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

try:
    import requests  # Optional: for real API calls
except Exception:
    requests = None

# ------------------------------
# Sample Data Generation
# ------------------------------
RND = random.Random(4507)
NOW = datetime(2025, 10, 26, 11, 15, 0)  # KST context (for sample only)


def _norm(s: Optional[str]) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def make_identity(rec: Dict[str, str]) -> str:
    parts = [
        _norm(rec.get("model_name")),
        _norm(rec.get("solution")),
        _norm(rec.get("feature_group")),
        _norm(rec.get("feature")),
        _norm(rec.get("mode")),
        _norm(rec.get("mcc")),
        _norm(rec.get("mnc")),
        _norm(rec.get("region")),
        _norm(rec.get("country")),
        _norm(rec.get("operator")),
        _norm(rec.get("sp_fci")),
        _norm(rec.get("value")),
    ]
    basis = "|".join(parts)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def build_feature_records() -> pd.DataFrame:
    """Create a small but diverse FeatureRecord-like table."""
    rows = [
        ("S20","slsi","IMS","VoLTE","allow","true","450","05","",   "KR","KT","",        NOW - timedelta(days=1)),
        ("S20","mtk", "IMS","VoLTE","block","false","450","08","",  "KR","KTF","",       NOW - timedelta(days=1)),
        ("S20","slsi","ue-ca","CA_B3_B7","allow","B3+B7","", "",    "",   "",  "",       "", NOW - timedelta(days=2)),
        ("S21","slsi","IMS","VoLTE","allow","true","", "",          "",   "KR","",       "global white", NOW - timedelta(days=3)),
        ("S21","mtk", "RCS","RCS_CHAT","allow","ON","", "",         "",   "JP","KDDI","sp white", NOW - timedelta(days=3)),
        ("A52","slsi","allow-list","SMS","allow","ON","", "",       "EU", "",  "",       "global white", NOW - timedelta(days=4)),
        ("A52","mtk", "block-list","RCS_FILE","block","OFF","", "", "",   "",  "",       "global", NOW - timedelta(days=5)),
        ("S23","mtk", "IMS","VoLTE","none","NA","", "",             "",   "",  "",       "", NOW - timedelta(days=6)),
        ("X10","slsi","IMS","VoWiFi","allow","true","450","11","",  "KR","SKT","",       NOW - timedelta(days=1)),
        ("X10","slsi","IMS","VoLTE","allow","true","", "",          "",   "KR","",       "kddi", NOW - timedelta(days=1)),
        ("S22","slsi","IMS","VoLTE","allow","true","440","10","",   "JP","KDDI","",      NOW - timedelta(days=2)),
        ("S22","slsi","IMS","VoLTE","allow","true","", "",          "EU", "",  "",       "global white", NOW - timedelta(days=2)),
        ("A54","mtk", "RCS","RCS_CHAT","allow","ON","", "",         "",   "KR","KT","",  NOW - timedelta(days=2)),
        ("A54","mtk", "IMS","VoLTE","block","false","", "",         "",   "KR","KT","",  NOW - timedelta(days=7)),
        ("G5","slsi", "ue-ca","CA_B1_B3","allow","B1+B3","", "",    "",   "",  "",       "", NOW - timedelta(days=3)),
        ("G5","slsi", "allow-list","MMS","allow","ON","450","06","", "KR","LGU+","",     NOW - timedelta(days=2)),
        ("Z1","mtk",  "IMS","VoNR","allow","true","", "",           "",   "KR","KT","",  NOW - timedelta(days=1)),
        ("Z1","mtk",  "IMS","VoNR","block","false","", "",          "",   "JP","KDDI","",NOW - timedelta(days=4)),
        ("S21","slsi","IMS","VoWiFi","allow","true","", "",         "",   "KR","KT","",  NOW - timedelta(days=0)),
        ("S21","slsi","IMS","VoWiFi","block","false","", "",        "",   "JP","KDDI","",NOW - timedelta(days=10)),
    ]
    cols = ["model_name","solution","feature_group","feature","mode","value",
            "mcc","mnc","region","country","operator","sp_fci","sync_time"]
    fr = []
    for r in rows:
        rec = dict(zip(cols, r))
        rec["identity_hash"] = make_identity(rec)
        fr.append(rec)
    df = pd.DataFrame(fr)[
        ["model_name","solution","feature_group","feature","mode","value",
         "mcc","mnc","region","country","operator","sp_fci","identity_hash","sync_time"]
    ]
    df["sync_time"] = pd.to_datetime(df["sync_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def build_audit_log() -> pd.DataFrame:
    """Events to power summary and history."""
    rows = [
        ("created","S21","slsi","IMS","VoWiFi", {"country":"KR","operator":"KT"}, None, "allow", None, "true", NOW - timedelta(days=0, hours=2), "sync-20251026-01"),
        ("updated","S20","slsi","IMS","VoLTE", {"mcc":"450","mnc":"05","operator":"KT"}, "block", "allow", "false", "true", NOW - timedelta(days=1, hours=1), "sync-20251025-01"),
        ("deleted","A52","mtk","block-list","RCS_FILE", {}, "block", None, "OFF", None, NOW - timedelta(days=5, hours=3), "sync-20251021-01"),
        ("created","G5","slsi","ue-ca","CA_B1_B3", {}, None, "allow", None, "B1+B3", NOW - timedelta(days=3, hours=5), "sync-20251023-01"),
        ("updated","S21","mtk","RCS","RCS_CHAT", {"country":"JP","operator":"KDDI"}, "none", "allow", "NA", "ON", NOW - timedelta(days=3, hours=2), "sync-20251023-02"),
        ("created","X10","slsi","IMS","VoWiFi", {"mcc":"450","mnc":"11","operator":"SKT"}, None, "allow", None, "true", NOW - timedelta(days=1, hours=4), "sync-20251025-02"),
        ("created","Z1","mtk","IMS","VoNR", {"country":"KR","operator":"KT"}, None, "allow", None, "true", NOW - timedelta(days=1, hours=6), "sync-20251025-02"),
        ("updated","Z1","mtk","IMS","VoNR", {"country":"JP","operator":"KDDI"}, "allow", "block", "true", "false", NOW - timedelta(days=4, hours=1), "sync-20251022-01"),
        ("created","A52","slsi","allow-list","SMS", {"region":"EU"}, None, "allow", None, "ON", NOW - timedelta(days=4, hours=2), "sync-20251022-02"),
        ("created","S23","mtk","IMS","VoLTE", {}, None, "none", None, "NA", NOW - timedelta(days=6, hours=1), "sync-20251020-01"),
        ("updated","S22","slsi","IMS","VoLTE", {"mcc":"440","mnc":"10","operator":"KDDI"}, "block", "allow", "false", "true", NOW - timedelta(days=2, hours=3), "sync-20251024-01"),
        ("updated","S22","slsi","IMS","VoLTE", {"region":"EU"}, "allow", "allow", "true", "true", NOW - timedelta(days=2, hours=2), "sync-20251024-01"),
        ("deleted","A54","mtk","IMS","VoLTE", {"country":"KR","operator":"KT"}, "block", None, "false", None, NOW - timedelta(days=7, hours=1), "sync-20251019-01"),
        ("created","X10","slsi","IMS","VoLTE", {"country":"KR"}, None, "allow", None, "true", NOW - timedelta(days=1, hours=6), "sync-20251025-01"),
        ("updated","S20","mtk","IMS","VoLTE", {"mcc":"450","mnc":"08","operator":"KTF"}, "allow", "block", "true", "false", NOW - timedelta(days=1, hours=2), "sync-20251025-01"),
    ]
    cols = ["action","model_name","solution","feature_group","feature","dims_json",
            "mode_before","mode_after","value_before","value_after","changed_at","run_id"]
    df = pd.DataFrame([
        dict(zip(cols, [
            a, m, s, fg, f, json.dumps(d), mb or "", ma or "", vb or "", va or "",
            ts.strftime("%Y-%m-%d %H:%M:%S"), run
        ]))
        for (a,m,s,fg,f,d,mb,ma,vb,va,ts,run) in rows
    ])
    return df


def build_summary_from_audit(audit: pd.DataFrame, days: int) -> Dict:
    # Count by date within the last N days
    audit["d"] = pd.to_datetime(audit["changed_at"]).dt.date
    end = date.today()
    start = end - timedelta(days=days-1)
    mask = (audit["d"] >= start) & (audit["d"] <= end)
    df = audit.loc[mask].copy()
    # Initialize date range
    days_list = [start + timedelta(days=i) for i in range(days)]
    base = pd.DataFrame({"date": days_list})
    base["date"] = base["date"].astype(str)
    # Aggregate
    piv = df.pivot_table(index="d", columns="action", values="run_id", aggfunc="count").fillna(0)
    piv = piv.rename_axis(None, axis=1).reset_index().rename(columns={"d":"date"})
    merged = base.merge(piv, on="date", how="left").fillna(0)
    for col in ["created","updated","deleted"]:
        if col not in merged.columns:
            merged[col] = 0
    # errors: synthesize a small random series
    merged["errors"] = [RND.randint(0, 2) for _ in range(len(merged))]
    series = merged[["date","created","updated","deleted","errors"]].to_dict(orient="records")
    return {
        "window": days, "tz": "Asia/Seoul",
        "version": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "min_date": series[0]["date"], "max_date": series[-1]["date"],
        "series": series
    }


# ------------------------------
# Optional: Real API calls
# ------------------------------
def api_get_all(host: str, params: Dict[str,str]) -> pd.DataFrame:
    if not requests:
        raise RuntimeError("requests unavailable")
    url = f"{host.rstrip('/')}/api/v1/all"
    r = requests.get(url, params=params, timeout=10, headers={"Accept":"text/csv"})
    r.raise_for_status()
    if r.headers.get("Content-Type","").startswith("text/csv"):
        return pd.read_csv(io.StringIO(r.text))
    return pd.DataFrame(r.json())


def api_get_summary(host: str, days: int) -> Dict:
    if not requests:
        raise RuntimeError("requests unavailable")
    url = f"{host.rstrip('/')}/api/dev/runs/summary?days={days}"
    r = requests.get(url, timeout=10, headers={"Accept":"application/json"})
    r.raise_for_status()
    return r.json()


# ------------------------------
# DataManager (client-side cache)
# ------------------------------
class DataManager:
    def __init__(self):
        self.feature = build_feature_records()
        self.audit = build_audit_log()
        self.summary_cache: Dict[int, Dict] = {}
        self.history_cache: Dict[Tuple, pd.DataFrame] = {}
        self.version = None

    def load_summaries(self, use_api: bool, host: str):
        for d in (1,7,14,30):
            self.summary_cache[d] = (api_get_summary(host, d) if use_api and host
                                     else build_summary_from_audit(self.audit.copy(), d))
        self.version = self.summary_cache[14]["version"]

    def get_summary(self, days: int) -> Dict:
        return self.summary_cache.get(days) or build_summary_from_audit(self.audit.copy(), days)

    def get_all(self, use_api: bool, host: str, **filters) -> pd.DataFrame:
        if use_api and host:
            try:
                return api_get_all(host, filters)
            except Exception as e:
                st.warning(f"API /api/v1/all 실패: {e}. 샘플로 대체합니다.")
        # simple local filter on sample
        df = self.feature.copy()
        for k,v in filters.items():
            if not v:
                continue
            if k in df.columns:
                df = df[df[k].astype(str).str.contains(str(v), case=False, na=False)]
        return df

    def search_history(self, window: int, **filters) -> pd.DataFrame:
        key = (window, tuple(sorted(filters.items())))
        if key in self.history_cache:
            return self.history_cache[key]
        df = self.audit.copy()
        df["date"] = pd.to_datetime(df["changed_at"]).dt.date
        end = date.today()
        start = end - timedelta(days=window-1)
        mask = (df["date"] >= start) & (df["date"] <= end)
        df = df.loc[mask]
        # filters
        for k,v in filters.items():
            if not v: 
                continue
            if k == "mcc" or k == "mnc" or k == "operator" or k == "model_name" or k == "feature_group" or k == "feature" or k == "solution":
                df = df[df[[k,"dims_json"]].apply(lambda r: (str(v).lower() in r[k].lower()) or (str(v).lower() in r["dims_json"].lower()), axis=1)]
            elif k == "action":
                df = df[df["action"].str.lower()==str(v).lower()]
        df = df.sort_values("changed_at", ascending=False).reset_index(drop=True)
        self.history_cache[key] = df
        return df


# ------------------------------
# UI
# ------------------------------
st.set_page_config(page_title="FMW — Overview + History", layout="wide")
st.title("FMW — Overview (OV) + History (HX) Sample")

with st.sidebar:
    st.subheader("데이터 소스")
    use_api = st.toggle("API 사용", value=False, help="체크 시 Host의 API를 호출합니다. 실패하면 샘플 데이터로 대체.")
    host = st.text_input("API Host", value="http://localhost")
    st.caption("예: GET /api/v1/all (CSV), GET /api/dev/runs/summary?days=14 (JSON)")

if "dm2" not in st.session_state:
    st.session_state.dm2 = DataManager()
    st.session_state.dm2.load_summaries(use_api=False, host="")

# reload summaries if source changed
if st.session_state.get("_prev_use_api2") != use_api or st.session_state.get("_prev_host2") != host:
    try:
        st.session_state.dm2.load_summaries(use_api=use_api, host=host)
    except Exception as e:
        st.warning(f"요약 API 로드 실패: {e}. 샘플로 대체합니다.")
        st.session_state.dm2.load_summaries(use_api=False, host="")
    st.session_state["_prev_use_api2"] = use_api
    st.session_state["_prev_host2"] = host

tab1, tab2 = st.tabs(["Overview", "History"])

# ------------------------------
# Tab 1: Overview
# ------------------------------
with tab1:
    st.subheader("Presets")
    days = st.radio("기간", [1,7,14,30], index=2, horizontal=True)
    summary = st.session_state.dm2.get_summary(days)
    df = pd.DataFrame(summary["series"])

    # Meta
    cols = st.columns([1,1,2])
    with cols[0]:
        st.metric("Window", f"{summary['window']}일")
    with cols[1]:
        st.metric("Timezone", summary.get("tz","Asia/Seoul"))
    with cols[2]:
        st.caption(f"Last sync: {summary['version']} · Range: {summary['min_date']} ~ {summary['max_date']} (snapshot)")

    # KPI
    kpi_cols = st.columns(4)
    for col, name in zip(kpi_cols, ["created","updated","deleted","errors"]):
        total = int(df[name].sum())
        delta = int(df[name].iloc[-1] - (df[name].iloc[-2] if len(df)>1 else 0))
        with col:
            st.metric(label=name.capitalize(), value=f"{total:,}", delta=f"{delta:+}")

    st.divider()
    st.subheader("Timeline")
    st.line_chart(df.set_index("date")[["created","updated","deleted","errors"]])

    st.subheader("API: /api/v1/all (샘플/필터)")
    # simple filters
    fcols = st.columns(6)
    f_model = fcols[0].text_input("model_name")
    f_feature = fcols[1].text_input("feature")
    f_operator = fcols[2].text_input("operator")
    f_country = fcols[3].text_input("country")
    f_mcc = fcols[4].text_input("mcc")
    f_mnc = fcols[5].text_input("mnc")

    all_df = st.session_state.dm2.get_all(use_api=use_api, host=host,
                                          model_name=f_model, feature=f_feature, operator=f_operator,
                                          country=f_country, mcc=f_mcc, mnc=f_mnc)
    st.dataframe(all_df, use_container_width=True, hide_index=True)
    csv_bytes = all_df.to_csv(index=False).encode("utf-8")
    st.download_button("다운로드: /api/v1/all (CSV, 샘플)", data=csv_bytes, file_name="api_v1_all_sample.csv", mime="text/csv")

    with st.expander("샘플 요약 JSON 보기 (/api/dev/runs/summary)"):
        st.code(json.dumps(summary, ensure_ascii=False, indent=2), language="json")


# ------------------------------
# Tab 2: History
# ------------------------------
with tab2:
    st.subheader("검색 (HX)")
    hcols = st.columns(6)
    q_feature = hcols[0].text_input("feature_name (예: VoLTE)")
    q_model = hcols[1].text_input("model_name (예: S21)")
    q_operator = hcols[2].text_input("operator (예: KDDI)")
    q_mcc = hcols[3].text_input("mcc (예: 450)")
    q_mnc = hcols[4].text_input("mnc (예: 05)")
    q_action = hcols[5].selectbox("action", ["", "create", "update", "delete"], index=0)

    hdays = st.radio("기간", [1,7,14,30], index=2, horizontal=True, key="hx_days")
    hist_df = st.session_state.dm2.search_history(hdays,
                                                  feature=q_feature,
                                                  model_name=q_model,
                                                  operator=q_operator,
                                                  mcc=q_mcc, mnc=q_mnc,
                                                  action=q_action)

    st.caption(f"결과: {len(hist_df)} 건")
    st.dataframe(hist_df[["changed_at","action","model_name","feature_group","feature","solution","dims_json","mode_before","mode_after","value_before","value_after"]],
                 use_container_width=True, hide_index=True)

    # Row details
    if len(hist_df) > 0:
        idx = st.number_input("상세 보기 (행 index)", min_value=0, max_value=len(hist_df)-1, value=0, step=1)
        row = hist_df.iloc[int(idx)]
        st.markdown("**Diff**")
        diff_items = []
        for k, old, new in [("mode", row["mode_before"], row["mode_after"]),
                            ("value", row["value_before"], row["value_after"])]:
            if old != new:
                diff_items.append(f"{k}: {old or '∅'} → {new or '∅'}")
        st.write(", ".join(diff_items) or "(변경 없음)")
        st.markdown("**Dims**")
        st.code(row["dims_json"], language="json")

    # export
    csv_bytes = hist_df.to_csv(index=False).encode("utf-8")
    st.download_button("다운로드: /api/v1/history (CSV, 샘플)", data=csv_bytes, file_name="api_v1_history_sample.csv", mime="text/csv")
