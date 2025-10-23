# fmw_dm_single_with_data.py
# 단일 파일: Streamlit 데이터 매니저 + 샘플 데이터(내장)
# - API v1(GET-only) 지원 + 샘플 모드 지원
# - 매일 06:00 KST 자동 동기화(캐시 pull), 수동 버튼 없음
# - 사이드바: 그룹→피처→상세 필터 → 조회/다운로드
#
# 실행:
#   pip install streamlit pandas requests apscheduler pytz python-dotenv
#   # 샘플 데이터로 실행(백엔드 없이):
#   USE_SAMPLE=1 streamlit run fmw_dm_single_with_data.py
#   # 실 API(v1)로 실행:
#   USE_SAMPLE=0 API_BASE="http://backend.example.com/v1" API_KEY="..." streamlit run fmw_dm_single_with_data.py

import os, io, json, pathlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import pandas as pd
import requests
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone as tz

# ===================== 설정 =====================
KST = timezone(timedelta(hours=9))
DATA_DIR = pathlib.Path("./_cache_v1")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 환경 변수
USE_SAMPLE = os.getenv("USE_SAMPLE", "1")  # 기본: 샘플 ON
API_BASE = os.getenv("API_BASE", "http://localhost:8000/v1").rstrip("/")
API_KEY  = os.getenv("API_KEY")
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() in ("1", "true", "yes")

# v1 엔드포인트 경로(실 API 사용 시 조정 가능)
PATH_GROUPS   = "/feature-groups/"
PATH_FEATURES = "/features/"
PATH_RECORDS  = "/feature-records/"

# ===================== 샘플 데이터(내장 CSV) =====================
SAMPLE_CSV = """feature_group,feature_name,model_name,mcc,mnc,region,country,operator,sp_fci,mode,value,status,updated_at
allow list,device_allowed,M100,450,5,APAC,KR,KT,SP-001,allow,true,active,2025-10-23T06:00:00+09:00
block list,blocked_reason,M100,450,5,APAC,KR,KT,SP-001,block,,active,2025-10-23T06:00:00+09:00
rel features,nr_release,M100,450,5,APAC,KR,KT,SP-001,allow,Rel-15,active,2025-10-23T06:00:00+09:00
ue capa,ue_max_bw_mhz,M100,450,5,APAC,KR,KT,SP-001,allow,100,active,2025-10-23T06:00:00+09:00
allow list,device_allowed,M101,440,8,EMEA,JP,SKT,SP-002,allow,false,active,2025-10-23T06:01:00+09:00
block list,blocked_reason,M101,440,8,EMEA,JP,SKT,SP-002,block,fraud,active,2025-10-23T06:01:00+09:00
rel features,nr_release,M101,440,8,EMEA,JP,SKT,SP-002,allow,Rel-16,active,2025-10-23T06:01:00+09:00
ue capa,ue_max_bw_mhz,M101,440,8,EMEA,JP,SKT,SP-002,allow,120,active,2025-10-23T06:01:00+09:00
allow list,device_allowed,M102,262,1,APAC,DE,LGU+,SP-003,allow,true,active,2025-10-23T06:02:00+09:00
block list,blocked_reason,M102,262,1,APAC,DE,LGU+,SP-003,block,roaming,active,2025-10-23T06:02:00+09:00
rel features,nr_release,M102,262,1,APAC,DE,LGU+,SP-003,allow,Rel-17,active,2025-10-23T06:02:00+09:00
ue capa,ue_max_bw_mhz,M102,262,1,APAC,DE,LGU+,SP-003,allow,140,active,2025-10-23T06:02:00+09:00
allow list,device_allowed,M103,208,6,EMEA,FR,NTT,SP-004,allow,false,active,2025-10-23T06:03:00+09:00
block list,blocked_reason,M103,208,6,EMEA,FR,NTT,SP-004,block,policy,active,2025-10-23T06:03:00+09:00
rel features,nr_release,M103,208,6,EMEA,FR,NTT,SP-004,allow,Rel-18,active,2025-10-23T06:03:00+09:00
ue capa,ue_max_bw_mhz,M103,208,6,EMEA,FR,NTT,SP-004,allow,160,active,2025-10-23T06:03:00+09:00
allow list,device_allowed,M104,450,3,APAC,KR,DOCOMO,SP-005,allow,true,active,2025-10-23T06:04:00+09:00
block list,blocked_reason,M104,450,3,APAC,KR,DOCOMO,SP-005,block,legacy,active,2025-10-23T06:04:00+09:00
rel features,nr_release,M104,450,3,APAC,KR,DOCOMO,SP-005,allow,Rel-15,active,2025-10-23T06:04:00+09:00
ue capa,ue_max_bw_mhz,M104,450,3,APAC,KR,DOCOMO,SP-005,allow,180,active,2025-10-23T06:04:00+09:00
allow list,device_allowed,M105,440,2,EMEA,JP,KDDI,SP-006,allow,false,active,2025-10-23T06:05:00+09:00
block list,blocked_reason,M105,440,2,EMEA,JP,KDDI,SP-006,block,,active,2025-10-23T06:05:00+09:00
rel features,nr_release,M105,440,2,EMEA,JP,KDDI,SP-006,allow,Rel-16,active,2025-10-23T06:05:00+09:00
ue capa,ue_max_bw_mhz,M105,440,2,EMEA,JP,KDDI,SP-006,allow,200,active,2025-10-23T06:05:00+09:00
allow list,device_allowed,M106,262,5,APAC,DE,Vodafone,SP-007,allow,true,active,2025-10-23T06:06:00+09:00
block list,blocked_reason,M106,262,5,APAC,DE,Vodafone,SP-007,block,fraud,active,2025-10-23T06:06:00+09:00
rel features,nr_release,M106,262,5,APAC,DE,Vodafone,SP-007,allow,Rel-17,active,2025-10-23T06:06:00+09:00
ue capa,ue_max_bw_mhz,M106,262,5,APAC,DE,Vodafone,SP-007,allow,100,active,2025-10-23T06:06:00+09:00
allow list,device_allowed,M107,208,8,EMEA,FR,Orange,SP-008,allow,false,active,2025-10-23T06:07:00+09:00
block list,blocked_reason,M107,208,8,EMEA,FR,Orange,SP-008,block,roaming,active,2025-10-23T06:07:00+09:00
rel features,nr_release,M107,208,8,EMEA,FR,Orange,SP-008,allow,Rel-18,active,2025-10-23T06:07:00+09:00
ue capa,ue_max_bw_mhz,M107,208,8,EMEA,FR,Orange,SP-008,allow,120,active,2025-10-23T06:07:00+09:00
allow list,device_allowed,M108,450,5,APAC,KR,DT,SP-009,allow,true,active,2025-10-23T06:08:00+09:00
block list,blocked_reason,M108,450,5,APAC,KR,DT,SP-009,block,policy,active,2025-10-23T06:08:00+09:00
rel features,nr_release,M108,450,5,APAC,KR,DT,SP-009,allow,Rel-15,active,2025-10-23T06:08:00+09:00
ue capa,ue_max_bw_mhz,M108,450,5,APAC,KR,DT,SP-009,allow,140,active,2025-10-23T06:08:00+09:00
allow list,device_allowed,M109,440,8,EMEA,JP,Free,SP-010,allow,false,active,2025-10-23T06:09:00+09:00
block list,blocked_reason,M109,440,8,EMEA,JP,Free,SP-010,block,legacy,active,2025-10-23T06:09:00+09:00
rel features,nr_release,M109,440,8,EMEA,JP,Free,SP-010,allow,Rel-16,active,2025-10-23T06:09:00+09:00
ue capa,ue_max_bw_mhz,M109,440,8,EMEA,JP,Free,SP-010,allow,160,active,2025-10-23T06:09:00+09:00
"""

# 동일 폴더에 샘플 CSV 저장(편의)
DEFAULT_CSV = pathlib.Path(__file__).with_name("fmw_sample_data.csv")
try:
    if not DEFAULT_CSV.exists():
        DEFAULT_CSV.write_text(SAMPLE_CSV, encoding="utf-8")
except Exception:
    pass

# ===================== 공통 유틸/캐시 =====================
def _p(name: str, suffix: str) -> pathlib.Path:
    return DATA_DIR / f"{name}{suffix}"

def _meta_path(name: str) -> pathlib.Path:
    return _p(name, "._meta.json")

def _save_meta(name: str, **extra):
    meta = {"last_sync_kst": datetime.now(tz=KST).isoformat(timespec="seconds")}
    meta.update(extra)
    _meta_path(name).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def read_meta(name: str) -> dict:
    p = _meta_path(name)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _load_df(name: str) -> pd.DataFrame:
    p = _p(name, ".parquet")
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()

def _save_df(name: str, df: pd.DataFrame):
    _p(name, ".parquet").parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_p(name, ".parquet"), index=False)

KEY_COLS = [
    "feature_group","feature_name","model_name","mcc","mnc",
    "region","country","operator","sp_fci","mode"
]
REQ_COLS = KEY_COLS + ["value", "status", "updated_at"]

def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in REQ_COLS:
        if c not in df.columns:
            df[c] = None
    for c in df.columns:
        df[c] = df[c].astype(str)
    return df[REQ_COLS]

def df_keyed(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_key"] = df[KEY_COLS].astype(str).agg("|".join, axis=1)
    return df

def diff_counts(old_df: pd.DataFrame, new_df: pd.DataFrame) -> Dict[str, int]:
    if old_df.empty:
        return {"added": len(new_df), "updated": 0, "removed": 0}
    old_k = df_keyed(old_df)
    new_k = df_keyed(new_df)
    old_keys = set(old_k["_key"]); new_keys = set(new_k["_key"])
    added = len(new_keys - old_keys)
    removed = len(old_keys - new_keys)
    merged = new_k.merge(old_k[["_key","value","status"]], on="_key", how="left", suffixes=("", "_old"))
    updated = (merged["value"] != merged["value_old"]) | (merged["status"] != merged["status_old"])
    return {"added": added, "updated": int(updated.sum()), "removed": removed}

# ===================== 최근 변경 스냅샷 =====================
RECENT_CHANGES_FILE = DATA_DIR / "recent_changes.csv"

def _append_recent_changes(df_new: pd.DataFrame) -> None:
    cols_order = [
        "ts_kst","group","feature","action",
        "model_name","operator","region","country","mcc","mnc","sp_fci","mode",
        "before_value","after_value","before_status","after_status","_key"
    ]
    for c in cols_order:
        if c not in df_new.columns:
            df_new[c] = ""
    if RECENT_CHANGES_FILE.exists():
        base = pd.read_csv(RECENT_CHANGES_FILE, dtype=str, keep_default_na=False)
        out = pd.concat([df_new[cols_order], base], ignore_index=True)
    else:
        out = df_new[cols_order]
    out = out.drop_duplicates(subset=["ts_kst","_key","action"], keep="first")
    out = out.sort_values("ts_kst", ascending=False).head(5000)
    out.to_csv(RECENT_CHANGES_FILE, index=False)

def snapshot_changes(cache_name: str, old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    now_kst = datetime.now(tz=KST).isoformat(timespec="seconds")
    g, f = cache_name.replace("records__", "").split("__", 1)
    oldk = df_keyed(ensure_cols(old_df))
    newk = df_keyed(ensure_cols(new_df))
    old_keys = set(oldk["_key"]); new_keys = set(newk["_key"]); both_keys = old_keys & new_keys

    added = newk[newk["_key"].isin(new_keys - old_keys)].copy()
    added["action"] = "ADD"; added["before_value"] = ""; added["before_status"] = ""
    added["after_value"] = added["value"]; added["after_status"] = added["status"]

    removed = oldk[oldk["_key"].isin(old_keys - new_keys)].copy()
    removed["action"] = "REM"; removed["before_value"] = removed["value"]; removed["before_status"] = removed["status"]
    removed["after_value"] = ""; removed["after_status"] = ""

    merged = newk[newk["_key"].isin(both_keys)].merge(
        oldk[["_key","value","status"]], on="_key", how="left", suffixes=("", "_old")
    )
    upd_mask = (merged["value"] != merged["value_old"]) | (merged["status"] != merged["status_old"])
    updated = merged.loc[upd_mask].copy()
    updated["action"] = "UPD"
    updated["before_value"] = updated["value_old"].fillna("")
    updated["before_status"] = updated["status_old"].fillna("")
    updated["after_value"] = updated["value"]
    updated["after_status"] = updated["status"]

    def _decorate(df):
        if df.empty: return df
        df["ts_kst"] = now_kst; df["group"] = g; df["feature"] = f
        return df[[
            "ts_kst","group","feature","action",
            "model_name","operator","region","country","mcc","mnc","sp_fci","mode",
            "before_value","after_value","before_status","after_status","_key"
        ]]

    out_df = pd.concat([_decorate(added), _decorate(updated), _decorate(removed)], ignore_index=True)
    if not out_df.empty:
        _append_recent_changes(out_df)

    return {"added": len(added), "updated": len(updated), "removed": len(removed)}

def load_recent_changes(limit: int = 200) -> pd.DataFrame:
    if not RECENT_CHANGES_FILE.exists():
        return pd.DataFrame(columns=[
            "ts_kst","group","feature","action",
            "model_name","operator","region","country","mcc","mnc","sp_fci","mode",
            "before_value","after_value","before_status","after_status","_key"
        ])
    df = pd.read_csv(RECENT_CHANGES_FILE, dtype=str, keep_default_na=False)
    return df.sort_values("ts_kst", ascending=False).head(limit)

# ===================== 데이터 소스: 샘플 vs API =====================
def _get(path: str, params: Optional[Dict[str, Any]] = None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    headers = {"X-API-KEY": API_KEY} if API_KEY else {}
    r = requests.get(url, params=params or {}, headers=headers, verify=VERIFY_SSL, timeout=60)
    r.raise_for_status()
    return r.json()

def list_feature_groups_api() -> List[Dict[str, Any]]:
    return _get(PATH_GROUPS)

def list_features_api(group_name: str) -> List[Dict[str, Any]]:
    return _get(PATH_FEATURES, {"group": group_name})

def list_feature_records_api(group_name: str, feature_name: str, **filters) -> List[Dict[str, Any]]:
    params = {"group": group_name, "feature": feature_name}
    params.update({k: v for k, v in filters.items() if v not in (None, "", [])})
    return _get(PATH_RECORDS, params)

@st.cache_data
def sample_df() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(SAMPLE_CSV), dtype=str, keep_default_na=False)

def list_feature_groups_sample() -> List[Dict[str, Any]]:
    df = sample_df()
    groups = sorted(df["feature_group"].dropna().unique().tolist())
    return [{"name": g} for g in groups]

def list_features_sample(group_name: str) -> List[Dict[str, Any]]:
    df = sample_df()
    feats = sorted(df.loc[df["feature_group"].eq(group_name), "feature_name"].dropna().unique().tolist())
    return [{"name": f} for f in feats]

def list_feature_records_sample(group_name: str, feature_name: str, **filters) -> List[Dict[str, Any]]:
    df = sample_df()
    q = df[(df["feature_group"] == group_name) & (df["feature_name"] == feature_name)].copy()
    for k in ("region","country","mcc","mnc","mode"):
        v = filters.get(k)
        if v:
            q = q[q[k].astype(str) == str(v)]
    for k in ("model","operator"):
        v = filters.get(k)
        if v:
            col = "model_name" if k == "model" else "operator"
            q = q[q[col].str.contains(str(v), case=False, na=False)]
    return q.to_dict(orient="records")

if USE_SAMPLE == "1":
    list_feature_groups = list_feature_groups_sample
    list_features = list_features_sample
    list_feature_records = list_feature_records_sample
else:
    list_feature_groups = list_feature_groups_api
    list_features = list_features_api
    list_feature_records = list_feature_records_api

# ===================== 동기화(06:00 자동) =====================
def sync_all() -> Dict[str, Any]:
    summary = {"groups": 0, "features": 0, "records_added": 0, "records_updated": 0, "records_removed": 0}
    groups = list_feature_groups() or []
    summary["groups"] = len(groups)

    for g in groups:
        gname = g.get("name")
        feats = list_features(gname) or []
        summary["features"] += len(feats)
        for f in feats:
            fname = f.get("name")
            new_rows = list_feature_records(gname, fname)
            new_df = ensure_cols(pd.DataFrame(new_rows))
            cache_name = f"records__{gname}__{fname}"
            old_df = _load_df(cache_name)

            dcnt = diff_counts(old_df, new_df)
            _ = snapshot_changes(cache_name, old_df, new_df)

            _save_df(cache_name, new_df)
            _save_meta(cache_name, **dcnt)

            summary["records_added"]   += dcnt["added"]
            summary["records_updated"] += dcnt["updated"]
            summary["records_removed"] += dcnt["removed"]

    _save_meta("index", **summary)
    return summary

@st.cache_resource
def get_scheduler():
    sched = BackgroundScheduler(timezone=tz("Asia/Seoul"))
    sched.start()
    if not any(j.id == "nightly6" for j in sched.get_jobs()):
        sched.add_job(sync_all, "cron", hour=6, minute=0, id="nightly6")
    return sched

# ===================== UI =====================
st.set_page_config(page_title="FMW 데이터 매니저 (단일파일, 샘플 포함)", layout="wide", page_icon="🗂️")
st.title("FMW 데이터 매니저 (단일파일)")
st.caption("샘플/실API 모드 지원 · 매일 06:00 자동 동기화 · 캐시 조회")

_ = get_scheduler()

# 초기 캐시 없으면 1회 동기화
if not _meta_path("index").exists():
    try:
        sync_all()
    except Exception as e:
        st.warning(f"초기 동기화 실패: {e}")

meta = read_meta("index")
idx_last = meta.get("last_sync_kst", "-")
added = meta.get("records_added", 0)
updated = meta.get("records_updated", 0)
removed = meta.get("records_removed", 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("마지막 전체 동기화", idx_last)
col2.metric("추가(ADD, 최근 동기화)", added)
col3.metric("수정(UPD, 최근 동기화)", updated)
col4.metric("삭제(REM, 최근 동기화)", removed)

st.divider()
st.subheader("최근 변경 (스냅샷)")
rc = load_recent_changes(limit=200)
left, right = st.columns([1,3])
action = left.selectbox("액션", ["ALL","ADD","UPD","REM"], index=0)
if not rc.empty and action != "ALL":
    rc = rc[rc["action"] == action]

if rc.empty:
    st.info("최근 변경 기록이 없습니다. 06:00 자동 동기화 이후 확인하세요.")
else:
    st.dataframe(
        rc[["ts_kst","group","feature","action","model_name","operator","region","country","mcc","mnc","sp_fci","mode","before_value","after_value"]],
        use_container_width=True, height=320
    )
    st.download_button("최근 변경 CSV 다운로드", rc.to_csv(index=False).encode("utf-8"),
                       file_name="recent_changes.csv", mime="text/csv")

st.divider()
st.subheader("데이터 조회 (캐시)")

st.sidebar.header("탐색")
try:
    g_list = list_feature_groups() or []
    group_names = [g.get("name") for g in g_list]
except Exception as e:
    group_names = []
    st.error(f"그룹 목록 로드 실패: {e}")

sel_group = st.sidebar.selectbox("Feature Group", [""] + group_names)
feat_names: List[str] = []
if sel_group:
    try:
        f_list = list_features(sel_group) or []
        feat_names = [f.get("name") for f in f_list]
    except Exception as e:
        st.error(f"피처 목록 로드 실패: {e}")
sel_feature = st.sidebar.selectbox("Feature", [""] + feat_names) if feat_names else ""

st.sidebar.subheader("상세 필터")
model_like = st.sidebar.text_input("Model 포함")
operator_like = st.sidebar.text_input("Operator 포함")
region_eq   = st.sidebar.text_input("Region =")
country_eq  = st.sidebar.text_input("Country =")
mcc_eq      = st.sidebar.text_input("MCC =")
mnc_eq      = st.sidebar.text_input("MNC =")
mode_eq     = st.sidebar.selectbox("Mode =", ["", "allow", "block"], index=0)
run_query   = st.sidebar.button("데이터 조회(캐시)")

def load_cached_records(g: str, f: str) -> pd.DataFrame:
    if not (g and f):
        return pd.DataFrame()
    return ensure_cols(_load_df(f"records__{g}__{f}"))

if run_query and sel_group and sel_feature:
    df = load_cached_records(sel_group, sel_feature)
    if df.empty:
        st.info("아직 캐시가 없습니다. 06:00 자동 동기화 이후 확인하세요.")
    else:
        q = df.copy()
        if mode_eq:       q = q[q["mode"] == mode_eq]
        if region_eq:     q = q[q["region"] == region_eq]
        if country_eq:    q = q[q["country"] == country_eq]
        if mcc_eq:        q = q[q["mcc"] == str(mcc_eq)]
        if mnc_eq:        q = q[q["mnc"] == str(mnc_eq)]
        if model_like:    q = q[q["model_name"].str.contains(model_like, case=False, na=False)]
        if operator_like: q = q[q["operator"].str.contains(operator_like, case=False, na=False)]
        st.dataframe(q, use_container_width=True)
        st.download_button("CSV 다운로드", q.to_csv(index=False).encode("utf-8"),
                           file_name=f"{sel_group}_{sel_feature}_filtered.csv", mime="text/csv")
else:
    st.info("좌측에서 그룹/피처를 선택 후 '데이터 조회(캐시)'를 누르세요. (자동 동기화: 06:00)")
