# fmw_dm_single_ux3.py
# 단일 파일: Streamlit 데이터 매니저 (UX 리뉴얼 v3, 모바일 친화)
# - PRD v1.1 & ERD 반영: GET-only API(v1), 06:00 자동 동기화, 오버뷰 4카드(+7일 추이), 탐색, 변경 이력
# - APScheduler 없을 때 Fallback: "앱 열릴 때 하루 1회" 자동 동기화
# - 샘플 데이터(내장) 포함: 10개 모델 × 4개 그룹(allow list / block list / rel features / ue capa)
# - 차원(dims): mcc, mnc, region, country, operator, sp_type, model_name, mode
# - 다운로드: CSV(+가능하면 Excel)
#
# 실행 예시
#   pip install streamlit pandas requests pytz python-dotenv   # apscheduler/xlsxwriter는 선택
#   USE_SAMPLE=1 streamlit run fmw_dm_single_ux3.py
#   USE_SAMPLE=0 API_BASE="http://localhost:8000/api" API_KEY="..." streamlit run fmw_dm_single_ux3.py

import os, io, json, pathlib, base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import pandas as pd
import requests
import streamlit as st
from pytz import timezone as tz

# ============== 선택 의존성: APScheduler / xlsxwriter ==============
try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
except Exception:
    BackgroundScheduler = None  # 패키지 없으면 Fallback 사용

try:
    import xlsxwriter  # noqa: F401  # 존재 여부만 확인
    XLSX_AVAILABLE = True
except Exception:
    XLSX_AVAILABLE = False

# ============== 설정 ==============
KST = tz("Asia/Seoul")
DATA_DIR = pathlib.Path("./_cache_v1")
DATA_DIR.mkdir(parents=True, exist_ok=True)

USE_SAMPLE = os.getenv("USE_SAMPLE", "1")  # 기본 샘플 ON
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api").rstrip("/")
API_KEY  = os.getenv("API_KEY")
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() in ("1", "true", "yes")

# API 경로 (PRD v1.1 반영: GET 전용)
PATH_GROUPS   = "/feature-groups/"
PATH_FEATURES = "/features/"
PATH_RECORDS  = "/feature-records/"
PATH_LONG     = "/long-records/"  # 선택

# ============== 샘플 데이터(내장 CSV) ==============
# PRD: dims = [region,country,operator,sp_type,mcc,mnc]; 필드 통일: sp_type 사용
SAMPLE_CSV = """feature_group,feature_name,model_name,mcc,mnc,region,country,operator,sp_type,mode,value,status,updated_at
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

# ============== 공통 유틸/캐시 ==============
def _p(name: str, suffix: str) -> pathlib.Path:
    return DATA_DIR / f"{name}{suffix}"

def _meta_path(name: str) -> pathlib.Path:
    return _p(name, "._meta.json")

def _save_meta(name: str, **extra):
    meta = {"last_sync_kst": datetime.now(KST).isoformat(timespec="seconds")}
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
    "region","country","operator","sp_type","mode"
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
    old_k = df_keyed(old_df); new_k = df_keyed(new_df)
    old_keys = set(old_k["_key"]); new_keys = set(new_k["_key"])
    added = len(new_keys - old_keys)
    removed = len(old_keys - new_keys)
    merged = new_k.merge(old_k[["_key","value","status"]], on="_key", how="left", suffixes=("", "_old"))
    updated = (merged["value"] != merged["value_old"]) | (merged["status"] != merged["status_old"])
    return {"added": added, "updated": int(updated.sum()), "removed": removed}

# ============== 최근 변경 스냅샷/추이 ==============
RECENT_CHANGES_FILE = DATA_DIR / "recent_changes.csv"

def _append_recent_changes(df_new: pd.DataFrame) -> None:
    cols_order = [
        "ts_kst","group","feature","action",
        "model_name","operator","region","country","mcc","mnc","sp_type","mode",
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
    now_kst = datetime.now(KST).isoformat(timespec="seconds")
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
            "model_name","operator","region","country","mcc","mnc","sp_type","mode",
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
            "model_name","operator","region","country","mcc","mnc","sp_type","mode",
            "before_value","after_value","before_status","after_status","_key"
        ])
    df = pd.read_csv(RECENT_CHANGES_FILE, dtype=str, keep_default_na=False)
    return df.sort_values("ts_kst", ascending=False).head(limit)

def today_change_counts(df_rc: pd.DataFrame) -> int:
    if df_rc.empty: return 0
    # 날짜 비교는 Asia/Seoul 기준 문자열 date 비교
    today = datetime.now(KST).date().isoformat()
    return int((pd.to_datetime(df_rc["ts_kst"]).dt.tz_localize("Asia/Seoul", nonexistent="shift_forward", ambiguous="NaT", errors="coerce").dt.date.astype(str) == today).sum())

def trend7(df_rc: pd.DataFrame) -> pd.DataFrame:
    if df_rc.empty:
        return pd.DataFrame({"date": [], "ADD": [], "UPD": [], "REM": []})
    df = df_rc.copy()
    df["date"] = pd.to_datetime(df["ts_kst"]).dt.tz_localize("Asia/Seoul", nonexistent="shift_forward", ambiguous="NaT", errors="coerce").dt.date
    pv = df.pivot_table(index="date", columns="action", values="_key", aggfunc="count", fill_value=0).reset_index()
    # 7일만
    pv = pv.sort_values("date", ascending=True).tail(7)
    for c in ("ADD","UPD","REM"):
        if c not in pv.columns: pv[c] = 0
    return pv[["date","ADD","UPD","REM"]]

# ============== 데이터 소스: 샘플 vs API ==============
def _get(path: str, params: Optional[Dict[str, Any]] = None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    headers = {"X-API-KEY": API_KEY} if API_KEY else {}
    r = requests.get(url, params=params or {}, headers=headers, verify=VERIFY_SSL, timeout=120)
    r.raise_for_status()
    return r.json()

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
    # 정확 매칭 필터
    for k in ("region","country","mcc","mnc","mode","sp_type"):
        v = filters.get(k)
        if v:
            q = q[q[k].astype(str) == str(v)]
    # 포함검색
    for k in ("model","operator"):
        v = filters.get(k)
        if v:
            col = "model_name" if k == "model" else "operator"
            q = q[q[col].str.contains(str(v), case=False, na=False)]
    return q.to_dict(orient="records")

def list_feature_groups_api() -> List[Dict[str, Any]]:
    return _get(PATH_GROUPS)

def list_features_api(group_name: str) -> List[Dict[str, Any]]:
    return _get(PATH_FEATURES, {"group": group_name})

def list_feature_records_api(group_name: str, feature_name: str, **filters) -> List[Dict[str, Any]]:
    # PRD: GET-only, params 기반 필터
    params = {"group": group_name, "feature": feature_name}
    for k in ("model","operator","region","country","mcc","mnc","mode","sp_type","page","page_size"):
        v = filters.get(k)
        if v not in (None, "", []):
            params[k] = v
    # /feature-records/ 또는 /long-records/ 중 선택
    use_long = bool(filters.get("_use_long", False))
    path = PATH_LONG if use_long else PATH_RECORDS
    data = _get(path, params)
    # DRF 페이징 대응
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data

if USE_SAMPLE == "1":
    list_feature_groups = list_feature_groups_sample
    list_features = list_features_sample
    list_feature_records = list_feature_records_sample
else:
    list_feature_groups = list_feature_groups_api
    list_features = list_features_api
    list_feature_records = list_feature_records_api

# ============== 동기화(06:00 자동) ==============
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
            # long 뷰 사용 시 파라미터로 활성화 가능(현재는 기본 off)
            new_rows = list_feature_records(gname, fname, _use_long=False)
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

def maybe_daily_sync(sync_fn):
    now = datetime.now(KST)
    today6 = now.replace(hour=6, minute=0, second=0, microsecond=0)
    last_str = read_meta("index").get("last_sync_kst")
    last_dt = None
    if last_str:
        try:
            last_dt = datetime.fromisoformat(last_str)
        except Exception:
            last_dt = None
    need = (not last_dt) or (now >= today6 and last_dt.date() != now.date())
    if need:
        try:
            sync_fn()
        except Exception as e:
            st.warning(f"자동 동기화 실패: {e}")

def start_scheduler():
    if BackgroundScheduler:
        sched = BackgroundScheduler()
        sched.add_job(sync_all, "cron", hour=6, minute=0, timezone="Asia/Seoul", id="daily_sync", replace_existing=True)
        sched.start()
        return "APScheduler(06:00)"
    else:
        maybe_daily_sync(sync_all)
        return "Fallback(앱 열릴 때 하루 1회)"

# ============== 도우미: 다운로드 버튼 ==============
def df_to_excel_bytes(df: pd.DataFrame) -> Optional[bytes]:
    if df.empty: return None
    if not XLSX_AVAILABLE: return None
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    return buf.getvalue()

# ============== UI (모바일 최적화) ==============
st.set_page_config(page_title="FMW 데이터 매니저", layout="wide", page_icon="🗂️")
st.markdown("""
    <style>
    .big-btn button {padding: 0.6rem 1rem; font-size: 1.05rem; border-radius: 12px;}
    .metric-small .stMetric {padding: .2rem .6rem;}
    .chip {display:inline-block;padding:.2rem .5rem;margin-right:.3rem;border-radius:999px;background:#eee;}
    @media (max-width: 640px){
      .stTabs [data-baseweb="tab-list"] {gap:.25rem;}
    }
    </style>
""", unsafe_allow_html=True)

st.title("FMW 데이터 매니저 · UX v3")
st.caption("GET-only API · 06:00 자동 동기화 · 오버뷰/탐색/변경 이력 · CSV/Excel 다운로드")

status_msg = start_scheduler()
st.info(f"동기화 상태: {status_msg} | 모드: {'샘플' if USE_SAMPLE=='1' else '실API'}")

# 초기 캐시 없으면 1회 동기화
if not _meta_path("index").exists():
    try:
        sync_all()
    except Exception as e:
        st.warning(f"초기 동기화 실패: {e}")

# --- 사이드바: 그룹/피처/필터 ---
st.sidebar.header("탐색 & 필터")
try:
    g_list = list_feature_groups() or []
    group_names = [g.get("name") for g in g_list]
except Exception as e:
    group_names = []
    st.sidebar.error(f"그룹 목록 로드 실패: {e}")

sel_group = st.sidebar.selectbox("Feature Group", [""] + group_names, index=1 if group_names else 0)
feat_names: List[str] = []
if sel_group:
    try:
        f_list = list_features(sel_group) or []
        feat_names = [f.get("name") for f in f_list]
    except Exception as e:
        st.sidebar.error(f"피처 목록 로드 실패: {e}")
sel_feature = st.sidebar.selectbox("Feature", [""] + feat_names, index=1 if feat_names else 0)

st.sidebar.subheader("상세 필터")
col_a, col_b = st.sidebar.columns(2)
with col_a:
    mode_eq     = st.selectbox("Mode", ["", "allow", "block"], index=0)
    region_eq   = st.text_input("Region =")
    mcc_eq      = st.text_input("MCC =")
with col_b:
    country_eq  = st.text_input("Country =")
    mnc_eq      = st.text_input("MNC =")
    sp_eq       = st.text_input("SP Type =")

model_like    = st.sidebar.text_input("Model 포함검색")
operator_like = st.sidebar.text_input("Operator 포함검색")

c1, c2, c3 = st.sidebar.columns(3)
with c1:
    run_query = st.button("데이터 조회", type="primary", use_container_width=True)
with c2:
    reset = st.button("필터 초기화", use_container_width=True)
with c3:
    use_long = st.checkbox("Long 뷰 사용", value=False, help="/long-records/ 사용(가능 시)")
if reset:
    mode_eq = region_eq = mcc_eq = country_eq = mnc_eq = sp_eq = model_like = operator_like = ""
    st.experimental_rerun()

# --- 탭 구성 ---
tab_ov, tab_explore, tab_changes = st.tabs(["📊 오버뷰", "🧭 탐색", "🕒 변경 이력"])

# ===== 오버뷰 =====
with tab_ov:
    meta = read_meta("index")
    idx_last = meta.get("last_sync_kst", "-")
    added = int(meta.get("records_added", 0) or 0)
    updated = int(meta.get("records_updated", 0) or 0)
    removed = int(meta.get("records_removed", 0) or 0)

    rc_base = load_recent_changes(limit=1000)
    today_cnt = today_change_counts(rc_base)

    # 총 레코드(간단 산출): 캐시에 저장된 모든 parquet 합
    # 실제 총계는 백엔드 집계 API가 이상적이지만, 여기서는 캐시 합으로 대체
    total_records = 0
    for p in DATA_DIR.glob("records__*__.parquet"):
        try:
            total_records += len(pd.read_parquet(p))
        except Exception:
            pass

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 레코드(캐시)", total_records)
    col2.metric("금일 변경(건)", today_cnt)
    col3.metric("실패 런(오늘)", "N/A")  # GET-only 환경에서는 추적 곤란 → 백엔드 run API 필요
    col4.metric("마지막 동기화(KST)", idx_last)

    st.markdown("#### 최근 7일 변경 추이")
    tr = trend7(rc_base)
    if tr.empty:
        st.info("추이 데이터가 없습니다. 동기화 후 다시 확인하세요.")
    else:
        st.line_chart(tr.set_index("date")[["ADD","UPD","REM"]])

    # 선택 항목 현황
    st.markdown("#### 선택 항목 현황")
    if sel_group and sel_feature:
        df = _load_df(f"records__{sel_group}__{sel_feature}")
        if not df.empty:
            df = ensure_cols(df)
            total = len(df)
            allow_cnt = int((df.get("mode","").astype(str)=="allow").sum())
            block_cnt = int((df.get("mode","").astype(str)=="block").sum())
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("총 레코드", total)
            cc2.metric("allow", allow_cnt)
            cc3.metric("block", block_cnt)
            st.caption(f"<span class='chip'>group: {sel_group}</span> <span class='chip'>feature: {sel_feature}</span>", unsafe_allow_html=True)
        else:
            st.info("선택한 그룹/피처의 캐시가 아직 없습니다.")
    else:
        st.info("좌측에서 그룹과 피처를 선택하면 해당 현황을 보여드립니다.")

# ===== 탐색 =====
def load_cached_records(g: str, f: str) -> pd.DataFrame:
    if not (g and f): return pd.DataFrame()
    return ensure_cols(_load_df(f"records__{g}__{f}"))

with tab_explore:
    st.markdown("#### 조건별 조회")
    if run_query and sel_group and sel_feature:
        df = load_cached_records(sel_group, sel_feature)
        if df.empty:
            st.info("캐시가 없습니다. 06:00 자동 동기화 이후 확인하세요.")
        else:
            q = df.copy()
            # 정확 매칭
            if mode_eq:       q = q[q["mode"] == mode_eq]
            if region_eq:     q = q[q["region"] == region_eq]
            if country_eq:    q = q[q["country"] == country_eq]
            if mcc_eq:        q = q[q["mcc"] == str(mcc_eq)]
            if mnc_eq:        q = q[q["mnc"] == str(mnc_eq)]
            if sp_eq:         q = q[q["sp_type"] == sp_eq]
            # 포함검색
            if model_like:    q = q[q["model_name"].str.contains(model_like, case=False, na=False)]
            if operator_like: q = q[q["operator"].str.contains(operator_like, case=False, na=False)]

            st.caption(f"🔎 결과 {len(q)}건")
            st.dataframe(q, use_container_width=True, height=420)

            # 다운로드
            st.download_button("CSV 다운로드", q.to_csv(index=False).encode("utf-8"),
                               file_name=f"{sel_group}_{sel_feature}_filtered.csv", mime="text/csv", type="primary")
            xbytes = df_to_excel_bytes(q)
            if xbytes:
                st.download_button("Excel(.xlsx) 다운로드", xbytes,
                                   file_name=f"{sel_group}_{sel_feature}_filtered.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.caption("💡 Excel 다운로드는 'xlsxwriter' 설치 시 활성화됩니다.")
    else:
        st.info("좌측에서 조건을 선택하고 **데이터 조회**를 눌러주세요.")

# ===== 변경 이력 =====
with tab_changes:
    st.markdown("#### 최근 변경 (스냅샷)")
    rc = load_recent_changes(limit=500)
    c1, c2, c3 = st.columns(3)
    action = c1.selectbox("액션", ["ALL","ADD","UPD","REM"], index=0)
    if sel_group:
        rc = rc[rc["group"] == sel_group] if not rc.empty else rc
    if sel_feature:
        rc = rc[rc["feature"] == sel_feature] if not rc.empty else rc
    if action != "ALL" and not rc.empty:
        rc = rc[rc["action"] == action]

    if rc.empty:
        st.info("최근 변경 기록이 없습니다. 06:00 자동 동기화 이후 확인하세요.")
    else:
        # 이모지 칩
        def emoji(a):
            return {"ADD":"🟢 ADD","UPD":"🟡 UPD","REM":"🔴 REM"}.get(a, a)
        rc = rc.copy()
        rc["action"] = rc["action"].map(emoji)
        st.dataframe(
            rc[["ts_kst","group","feature","action","model_name","operator","region","country","mcc","mnc","sp_type","mode","before_value","after_value"]],
            use_container_width=True, height=420
        )
        st.download_button("최근 변경 CSV 다운로드", rc.to_csv(index=False).encode("utf-8"),
                           file_name="recent_changes.csv", mime="text/csv", type="primary")
