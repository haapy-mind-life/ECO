
"""
FMW Streamlit Sample (v3 UX Guide aligned, Expert Review Applied)
- Menus: 오버뷰 / 히스토리 관리 / 상세 탐색 / 개발 전용
- Presets: 오늘 / 어제 / 7일 / 14일 / 30일
- APIs: /api/v1/all (CSV), /api/dev/runs/summary?days=N (JSON), /api/v1/history (CSV/JSON)
- Improvements: 스파크라인/배지, 한국어 툴팁, 오류 배너 표준화, canonical 라벨, 100행 기본

Run:
    streamlit run fmw_streamlit_sample_v3_plus.py
"""
from __future__ import annotations
import json
import io
import hashlib
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import requests
except Exception:
    requests = None


# ------------------------------
# Constants
# ------------------------------
APP_TZ = "Asia/Seoul"
NOW = datetime(2025, 10, 26, 11, 15, 0)  # sample timestamp
RND = random.Random(4519)
PRESETS = ["오늘", "어제", "7일", "14일", "30일"]

CANON_MAP = {
    "sp white": "global white",
    "kddi": "KDDI",
    "eu": "EU",
    "ktf": "KTF",
    "lgu+": "LGU+",
    "volte": "VoLTE",
    "vowifi": "VoWiFi"
}
def canonicalize(x: str) -> str:
    if x is None:
        return ""
    return CANON_MAP.get(str(x).strip().lower(), x)


# ------------------------------
# Helpers / Sample Generators
# ------------------------------
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
    df["operator"] = df["operator"].map(canonicalize)
    df["sp_fci"] = df["sp_fci"].map(canonicalize)
    df["feature"] = df["feature"].map(canonicalize)
    df["sync_time"] = pd.to_datetime(df["sync_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def build_audit_log() -> pd.DataFrame:
    rows = [
        ("created","S21","slsi","IMS","VoWiFi", {"country":"KR","operator":"KT"}, None, "allow", None, "true", NOW - timedelta(hours=2), "sync-20251026-01"),
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


def aggregate_summary(audit: pd.DataFrame, days: int, yesterday: bool=False) -> Dict:
    audit = audit.copy()
    audit["d"] = pd.to_datetime(audit["changed_at"]).dt.date
    end = date.today() - timedelta(days=1 if yesterday else 0)
    start = end - timedelta(days=days-1)
    mask = (audit["d"] >= start) & (audit["d"] <= end)
    df = audit.loc[mask].copy()

    # full date range
    days_list = [start + timedelta(days=i) for i in range(days)]
    base = pd.DataFrame({"date": days_list})
    base["date"] = base["date"].astype(str)

    if df.empty:
        merged = base.copy()
        merged["created"] = 0; merged["updated"] = 0; merged["deleted"] = 0
    else:
        piv = df.pivot_table(index="d", columns="action", values="run_id", aggfunc="count").fillna(0)
        piv = piv.rename_axis(None, axis=1).reset_index().rename(columns={"d":"date"})
        merged = base.merge(piv, on="date", how="left").fillna(0)

    merged["errors"] = [RND.randint(0, 2) for _ in range(len(merged))]
    series = merged[["date","created","updated","deleted","errors"]].to_dict(orient="records")
    return {
        "window": days, "tz": APP_TZ,
        "version": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "min_date": series[0]["date"], "max_date": series[-1]["date"],
        "series": series
    }


@st.cache_data(ttl=86400, show_spinner=False)
def sample_all() -> pd.DataFrame:
    return build_feature_records()

@st.cache_data(ttl=300, show_spinner=False)
def sample_summary_bundle() -> Dict[str, Dict]:
    audit = build_audit_log()
    return {
        "오늘": aggregate_summary(audit, 1, yesterday=False),
        "어제": aggregate_summary(audit, 1, yesterday=True),
        "7일": aggregate_summary(audit, 7),
        "14일": aggregate_summary(audit, 14),
        "30일": aggregate_summary(audit, 30),
    }

@st.cache_data(ttl=60, show_spinner=False)
def api_get_all(host: str, params: Dict[str,str]) -> pd.DataFrame:
    if not requests:
        raise RuntimeError("requests 가용하지 않음")
    url = f"{host.rstrip('/')}/api/v1/all"
    r = requests.get(url, params=params, timeout=10, headers={"Accept":"text/csv"})
    if r.status_code >= 400:
        st.session_state["last_api_error"] = {"error":{"code":r.status_code,"message":r.text}}
        r.raise_for_status()
    if r.headers.get("Content-Type","").startswith("text/csv"):
        return pd.read_csv(io.StringIO(r.text))
    return pd.DataFrame(r.json())

@st.cache_data(ttl=60, show_spinner=False)
def api_get_summary(host: str, days: int) -> Dict:
    if not requests:
        raise RuntimeError("requests 가용하지 않음")
    url = f"{host.rstrip('/')}/api/dev/runs/summary?days={days}"
    r = requests.get(url, timeout=10, headers={"Accept":"application/json"})
    if r.status_code >= 400:
        st.session_state["last_api_error"] = {"error":{"code":r.status_code,"message":r.text}}
        r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60, show_spinner=False)
def api_get_history(host: str, params: Dict[str,str]) -> pd.DataFrame:
    if not requests:
        raise RuntimeError("requests 가용하지 않음")
    url = f"{host.rstrip('/')}/api/v1/history"
    r = requests.get(url, params=params, timeout=10, headers={"Accept":"text/csv"})
    if r.status_code >= 400:
        st.session_state["last_api_error"] = {"error":{"code":r.status_code,"message":r.text}}
        r.raise_for_status()
    if r.headers.get("Content-Type","").startswith("text/csv"):
        return pd.read_csv(io.StringIO(r.text))
    return pd.DataFrame(r.json())


def sidebar_filters() -> Dict[str,str]:
    st.subheader("공통 필터")
    model = st.selectbox("모델(model_name)", ["", "S20","S21","S22","S23","A52","A54","G5","X10","Z1"], index=0, help="모델명 일부 입력 가능. 대소문자 무시.")
    fgroup = st.selectbox("기능 그룹(feature_group)", ["","IMS","RCS","allow-list","block-list","ue-ca"], index=0, help="표준 라벨 우선 노출(별칭은 자동 정규화).")
    col1,col2,col3 = st.columns(3)
    with col1:
        country = st.text_input("국가(country)", help="예: KR/JP/EU. 비워두면 전체.")
        region = st.text_input("지역(region)", help="예: EU, APAC 등 자유 텍스트.")
    with col2:
        operator = st.text_input("사업자(operator)", help="예: KDDI, KT, SKT. 별칭은 자동 표준화.")
        sp_fci = st.text_input("SP_FCI", help="예: global white")
    with col3:
        mcc = st.text_input("MCC", help="예: 450 (숫자 3자리)")
        mnc = st.text_input("MNC", help="예: 05/010 (앞 0 유지)")
    mode = st.selectbox("모드(mode)", ["", "allow","block","none"], index=0, help="허용/차단/해제 상태")
    fast = st.radio("빠른 기간", ["오늘","어제","7일","14일","30일"], index=2, horizontal=True,
                    help="홈과 히스토리에서 동일하게 사용됩니다.")
    return {
        "model_name": model, "feature_group": fgroup,
        "country": country, "region": region, "operator": operator, "sp_fci": sp_fci,
        "mcc": mcc, "mnc": mnc, "mode": mode, "fast": fast
    }


class DataManager:
    def __init__(self, use_api: bool=False, host: str=""):
        self.use_api = use_api
        self.host = host
        self._all = sample_all()
        self._bundle = sample_summary_bundle()
        self.version = self._bundle["14일"]["version"]

    def reload_source(self, use_api: bool, host: str):
        self.use_api = use_api
        self.host = host

    def get_all(self, **filters) -> pd.DataFrame:
        if self.use_api and self.host:
            try:
                df = api_get_all(self.host, filters)
                return df
            except Exception as e:
                st.warning(f"/api/v1/all 호출 실패 → 샘플 사용: {e}")
        df = self._all.copy()
        for k,v in filters.items():
            if k == "fast":
                continue
            if v and k in df.columns:
                df = df[df[k].astype(str).str.contains(str(v), case=False, na=False)]
        # Canonical labels
        for col in ("operator","sp_fci","feature"):
            if col in df.columns:
                df[col] = df[col].map(canonicalize)
        return df

    def get_summary(self, preset: str) -> Dict:
        mapping = {"오늘": 1, "어제": 1, "7일": 7, "14일": 14, "30일": 30}
        days = mapping.get(preset, 14)
        if self.use_api and self.host and preset not in ("오늘","어제"):
            try:
                return api_get_summary(self.host, days)
            except Exception as e:
                st.warning(f"/api/dev/runs/summary?days={days} 호출 실패 → 샘플 사용: {e}")
        return self._bundle[preset]

    def get_history(self, window_preset: str, **filters) -> pd.DataFrame:
        mapping = {"오늘": 1, "어제": 1, "7일": 7, "14일": 14, "30일": 30}
        days = mapping.get(window_preset, 14)
        params = {k:v for k,v in filters.items() if v}
        # API path
        if self.use_api and self.host:
            try:
                params.update({"limit":"1000"})
                # date_from/date_to는 서버에 맡기거나 별도 제공 가능
                return api_get_history(self.host, params)
            except Exception as e:
                st.warning(f"/api/v1/history 호출 실패 → 샘플 사용: {e}")
        # Sample path
        df = build_audit_log()
        df["date"] = pd.to_datetime(df["changed_at"]).dt.date
        end = date.today() - timedelta(days=1 if window_preset=="어제" else 0)
        start = end - timedelta(days=days-1)
        df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
        for k,v in filters.items():
            if not v:
                continue
            if k in ("model_name","feature_group","feature","solution"):
                df = df[df[k].str.contains(str(v), case=False, na=False)]
            elif k in ("operator","country","mcc","mnc"):
                df = df[df["dims_json"].str.contains(str(v), case=False, na=False)]
            elif k == "action":
                v2 = {"create":"created","update":"updated","delete":"deleted"}.get(str(v).lower(), str(v).lower())
                df = df[df["action"].str.lower() == v2]
        return df.sort_values("changed_at", ascending=False).reset_index(drop=True)


# ------------------------------
# App Layout
# ------------------------------
st.set_page_config(page_title="FMW — Streamlit v3 Sample (Plus)", layout="wide")

colL, colR = st.columns([3, 2])
with colL:
    st.title("FMW")
    st.caption("Feature Management Workspace")
with colR:
    st.markdown("""
<div style="text-align:right">
  <span style="padding:6px 10px;border-radius:8px;background:#e6f4ea">스냅샷: OK</span><br/>
  <span>마지막 동기화: 2025-10-26 11:15 KST</span>
</div>
""", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.header("메뉴")
    section = st.radio("이동", ["오버뷰","히스토리 관리","상세 탐색","개발 전용"], index=0)
    st.subheader("데이터 소스")
    use_api = st.toggle("API 사용", value=False, help="실 서버 API 호출. 실패 시 샘플로 폴백")
    host = st.text_input("API Host", value="http://localhost", help="예: http://127.0.0.1:8000")
    st.caption("필수 API: /api/v1/all, /api/dev/runs/summary?days=N, /api/v1/history")
    filters = sidebar_filters()

# Data manager
if "dm_v3p" not in st.session_state:
    st.session_state.dm_v3p = DataManager()
if st.session_state.get("_prev_src2") != (use_api, host):
    st.session_state.dm_v3p.reload_source(use_api, host)
    st.session_state["_prev_src2"] = (use_api, host)

dm = st.session_state.dm_v3p

# Unified error banner
if "last_api_error" in st.session_state:
    err = st.session_state.pop("last_api_error")
    st.error(f"{err['error']['code']}: {err['error']['message']}")

# --------- Section: Overview ---------
if section == "오버뷰":
    st.subheader("요약 카드")
    preset = filters["fast"]
    summary = dm.get_summary(preset)
    series_df = pd.DataFrame(summary["series"])

    cols = st.columns([1,1,1,2])
    with cols[0]:
        st.metric("Last Sync", summary["version"])
    with cols[1]:
        all_df = dm.get_all(**filters)
        st.metric("총 레코드 수", f"{len(all_df):,}")
    with cols[2]:
        y_df = dm.get_summary("어제")
        yd = pd.DataFrame(y_df["series"]).iloc[-1]
        st.metric("어제 CRUD", f"C{int(yd['created'])}/U{int(yd['updated'])}/D{int(yd['deleted'])}")
    with cols[3]:
        st.caption(f"기간: {summary['min_date']} ~ {summary['max_date']} · {preset}")

    # Sparkline block
    st.markdown("**최근 7일 스파크라인**")
    mini = series_df.tail(7)[["date","created","updated","deleted"]].copy()
    st.line_chart(mini.set_index("date"))

    st.subheader("N일 추세")
    st.line_chart(series_df.set_index("date")[["created","updated","deleted","errors"]])

    st.subheader("변화량 TOP5")
    top_df = all_df.copy()
    top_df["changes"] = [RND.randint(0, 10) for _ in range(len(top_df))]
    top = (top_df.groupby("feature_group")["changes"].sum()
           .sort_values(ascending=False).head(5)).reset_index()
    st.dataframe(top.head(100), use_container_width=True, hide_index=True)

    st.subheader("CSV 내보내기")
    csv_bytes = all_df.to_csv(index=False).encode("utf-8")
    st.download_button("CSV 다운로드 (/api/v1/all, 필터 적용 결과)", data=csv_bytes,
                       file_name="api_v1_all_filtered.csv", mime="text/csv")

# --------- Section: History ---------
elif section == "히스토리 관리":
    st.subheader("검색 / 필터")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        h_action = st.selectbox("CRUD", ["","created","updated","deleted"], index=0, help="변경 유형으로 필터")
    with c2:
        h_preset = st.radio("기간", PRESETS, index=2, horizontal=True, help="빠른 기간 프리셋")
    with c3:
        h_feature = st.text_input("feature", help="예: VoLTE / VoWiFi")
    with c4:
        h_model = st.text_input("model_name", help="예: S21 / A54")

    hist_df = dm.get_history(h_preset,
                             action=h_action,
                             feature=h_feature,
                             model_name=h_model,
                             operator=filters["operator"],
                             country=filters["country"],
                             mcc=filters["mcc"], mnc=filters["mnc"])

    st.caption(f"결과: {len(hist_df)} 건 (최대 1000)")
    view_cols = ["changed_at","action","model_name","feature_group","feature","solution",
                 "dims_json","mode_before","mode_after","value_before","value_after"]
    st.dataframe(hist_df[view_cols].head(100), use_container_width=True, hide_index=True)

    # Diff chips
    if len(hist_df) > 0:
        idx = st.number_input("상세 보기 (행 index)", min_value=0, max_value=len(hist_df)-1, value=0, step=1)
        row = hist_df.iloc[int(idx)]
        st.markdown("**변경 요약(Diff)**")
        diffs = []
        if row["mode_before"] != row["mode_after"]:
            diffs.append(f"🟢 mode: {row['mode_before'] or '∅'} → {row['mode_after'] or '∅'}")
        if row["value_before"] != row["value_after"]:
            diffs.append(f"🔵 value: {row['value_before'] or '∅'} → {row['value_after'] or '∅'}")
        st.write(", ".join(diffs) or "(변경 없음)")
        st.markdown("**Dims**")
        st.code(row["dims_json"], language="json")

    csv_bytes = hist_df.to_csv(index=False).encode("utf-8")
    st.download_button("CSV 다운로드 (/api/v1/history, 샘플/또는 API)", data=csv_bytes,
                       file_name="api_v1_history.csv", mime="text/csv")

# --------- Section: Detail Explore ---------
elif section == "상세 탐색":
    st.subheader("필터된 레코드 (상위 100행)")
    all_df = dm.get_all(**filters)
    st.dataframe(all_df.head(100), use_container_width=True, hide_index=True)

    st.subheader("추세 차트 (CRUD)")
    preset = filters["fast"]
    summary = dm.get_summary(preset)
    series_df = pd.DataFrame(summary["series"]).set_index("date")[["created","updated","deleted"]]
    st.line_chart(series_df)

    st.subheader("Feature 분포 (Top10)")
    feat = (all_df.groupby("feature")["model_name"].count()
            .sort_values(ascending=False).head(10)).reset_index().rename(columns={"model_name":"count"})
    st.bar_chart(feat.set_index("feature"))

    st.caption("※ dims 필터 토글은 실제 데이터에 맞춰 확장")

# --------- Section: DEV ---------
else:
    st.subheader("동기화 (DEV)")
    st.write("개발 단계에서만 사용. 운영 환경에서는 숨김 권장.")
    colA, colB = st.columns([1,2])
    with colA:
        interval = st.number_input("스케줄(분)", min_value=0, max_value=1440, value=0, step=5, help="0=비활성")
    with colB:
        if st.button("수동 동기화"):
            st.success("동기화 요청 전송(샘플). 스냅샷은 다음 실행에서 갱신됩니다.")
    st.subheader("최근 동기화 로그 (샘플)")
    st.code(json.dumps([
        {"run_id":"sync-20251026-01","status":"ok","finished_at":"2025-10-26 11:15:00 KST"},
        {"run_id":"sync-20251025-02","status":"ok","finished_at":"2025-10-25 02:05:00 KST"}
    ], ensure_ascii=False, indent=2), language="json")
