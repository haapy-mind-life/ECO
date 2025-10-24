
# streamlit_app.py — fmw (Feature Management Web) — v1.1 (2025-10-24)
# 요구: pip install streamlit pandas requests python-dateutil
import os, io, json, requests, pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

KST = timezone(timedelta(hours=9))

# ===============================
# DataManager — DRF 하루 1회 벌크 동기화 + 스냅샷
# ===============================
class DataManager:
    HEADERS = [
        "model_name","solution","feature_group","feature",
        "mcc","mnc","region","country","operator","sp_fci",
        "mode","value","sync_time"
    ]
    def __init__(self, base_url: str, cache_dir: str = ".cache", refresh_hour_kst: int = 6):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.refresh_hour_kst = refresh_hour_kst
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.join(self.cache_dir, "daily"), exist_ok=True)

    def _today_path(self, d=None):
        d = d or datetime.now(KST).date()
        return os.path.join(self.cache_dir, "daily", f"{d:%Y-%m-%d}.csv")

    def _cache_all_path(self):
        return os.path.join(self.cache_dir, "fmw_all.csv")

    def _should_refresh(self) -> bool:
        p = self._cache_all_path()
        if not os.path.exists(p):
            return True
        now = datetime.now(KST)
        cut = now.replace(hour=self.refresh_hour_kst, minute=0, second=0, microsecond=0)
        mtime = datetime.fromtimestamp(os.path.getmtime(p), KST)
        return (now >= cut) and (mtime < cut)

    def _fetch_all_csv(self, params=None) -> pd.DataFrame:
        url = f"{self.base_url}/api/v1/all"
        r = requests.get(url, params=params or {}, headers={"Accept": "text/csv"}, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content))
        keep = [c for c in self.HEADERS if c in df.columns]
        return df[keep]

    def refresh(self, params=None) -> pd.DataFrame:
        df = self._fetch_all_csv(params=params)
        df.to_csv(self._cache_all_path(), index=False, encoding="utf-8-sig")
        # 데일리 스냅샷(한 번만)
        day_path = self._today_path()
        if not os.path.exists(day_path):
            df.to_csv(day_path, index=False, encoding="utf-8-sig")
        return df

    def load_all(self, force=False, params=None) -> pd.DataFrame:
        if force or self._should_refresh():
            try: return self.refresh(params=params)
            except Exception as e: st.warning(f"동기화 실패 → 캐시 사용: {e}")
        p = self._cache_all_path()
        if os.path.exists(p):
            return pd.read_csv(p)
        return self.refresh(params=params)

    def list_snapshots(self, days: int = 14):
        out = []
        today = datetime.now(KST).date()
        for i in range(days):
            d = today - timedelta(days=i)
            p = self._today_path(d)
            if os.path.exists(p):
                out.append((d, p))
        return sorted(out)

    def load_snapshot(self, d) -> pd.DataFrame | None:
        p = self._today_path(d)
        if os.path.exists(p):
            return pd.read_csv(p)
        return None

    def runs_summary(self, days=7):
        try:
            r = requests.get(f"{self.base_url}/api/dev/runs/summary", params={"days": days}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def dev_sync(self, feature_group: str | None = None, source_tag="manual-streamlit"):
        try:
            if feature_group:
                url = f"{self.base_url}/api/dev/sync/{feature_group}"
            else:
                url = f"{self.base_url}/api/dev/sync"
            r = requests.post(url, json={"source_tag": source_tag}, timeout=15)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)


# ===============================
# 유틸 — 필터/변화 탐지
# ===============================
KEY_COLS = ["model_name","solution","feature_group","feature","mcc","mnc","region","country","operator","sp_fci","mode"]

def apply_filters(df: pd.DataFrame, model: str | None, group: str | None):
    if df is None or df.empty: return df
    out = df.copy()
    if model and model != "(전체)":
        out = out[out["model_name"] == model]
    if group and group != "(전체)":
        out = out[out["feature_group"] == group]
    return out

def build_key(df: pd.DataFrame) -> pd.Series:
    return df[KEY_COLS].astype(str).agg("|".join, axis=1)

def daily_changes(prev_df: pd.DataFrame, curr_df: pd.DataFrame):
    import pandas as pd
    if prev_df is None:  # 첫날
        empty_created = pd.DataFrame(columns=KEY_COLS+["value","change_type"])
        empty_updated = pd.DataFrame(columns=KEY_COLS+["old_value","new_value","change_type"])
        empty_deleted = pd.DataFrame(columns=KEY_COLS+["value","change_type"])
        return empty_created, empty_updated, empty_deleted

    p, c = prev_df.copy(), curr_df.copy()
    p["_key"] = build_key(p); c["_key"] = build_key(c)

    # 생성/삭제
    created_keys = set(c["_key"]) - set(p["_key"])
    deleted_keys = set(p["_key"]) - set(c["_key"])

    created = c[c["_key"].isin(created_keys)].copy()
    created["change_type"] = "created"

    deleted = p[p["_key"].isin(deleted_keys)].copy()
    deleted["change_type"] = "deleted"

    # 업데이트(키 동일, value 변경)
    merged = c.merge(p[["_key","value"]].rename(columns={"value":"old_value"}), on="_key", how="inner")
    updated = merged[merged["value"].astype(str) != merged["old_value"].astype(str)].copy()
    if not updated.empty:
        for col in KEY_COLS:
            if col not in updated.columns:
                updated[col] = updated["_key"].str.split("|").str[KEY_COLS.index(col)]
        updated["new_value"] = updated["value"]
        updated["change_type"] = "updated"
        updated = updated[KEY_COLS + ["old_value","new_value","change_type"]]

    created = created[KEY_COLS + ["value","change_type"]]
    deleted = deleted[KEY_COLS + ["value","change_type"]]
    created = created.sort_values(KEY_COLS, kind="stable")
    updated = updated.sort_values(KEY_COLS, kind="stable") if not updated.empty else updated
    deleted = deleted.sort_values(KEY_COLS, kind="stable")
    return created, updated, deleted


# ===============================
# UI — 앱 프레임
# ===============================
st.set_page_config(page_title="fmw — Feature Manager for Web", layout="wide")

# 앱 헤더 + 오버뷰(항상 표시)
st.markdown("<h1 style='margin-bottom:0'>fmw</h1><div style='color:#888;margin-top:-6px'>Feature Management Web — Overview</div>", unsafe_allow_html=True)

BASE_URL = st.secrets.get("BASE_URL", "https://<YOUR-NGINX-HOST>")
if "refresh_hour_kst" not in st.session_state:
    st.session_state.refresh_hour_kst = 6

dm = DataManager(BASE_URL, cache_dir=".cache", refresh_hour_kst=st.session_state.refresh_hour_kst)

# 최초 로드/갱신
df_all = dm.load_all(force=False)
models = ["(전체)"] + (sorted([x for x in df_all["model_name"].dropna().unique()]) if df_all is not None else [])
groups = ["(전체)"] + (sorted([x for x in df_all["feature_group"].dropna().unique()]) if df_all is not None else [])

# 사이드바
with st.sidebar:
    st.header("내비게이션")
    nav = st.radio("메뉴", ["히스토리 관리", "피처 상세", "데이터 탐색"], index=0)
    st.divider()
    sel_model = st.selectbox("모델 선택", options=models, index=0)
    sel_group = st.selectbox("피처 그룹 선택", options=groups, index=0)

    with st.expander("개발자 모드(임시 기능)"):
        st.caption("개발 단계에서만 사용. 운영 전 제거 예정.")
        st.session_state.refresh_hour_kst = st.number_input("일일 동기화 시각(KST, 시)", min_value=0, max_value=23, value=st.session_state.refresh_hour_kst, step=1)
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("캐시 강제 새로고침"):
                df_all = dm.load_all(force=True)
                st.success("캐시 새로고침 완료")
        with colB:
            if st.button("서버 동기화 호출(/api/dev/sync)"):
                code, msg = dm.dev_sync()
                st.info(f"응답: {code} / {msg[:120]}...")
        with colC:
            grp = st.text_input("그룹 동기화 대상(선택)", value="")
            if st.button("그룹 동기화 호출"):
                if grp.strip():
                    code, msg = dm.dev_sync(feature_group=grp.strip())
                    st.info(f"응답: {code} / {msg[:120]}...")
                else:
                    st.warning("그룹명을 입력하세요.")

# ---- 상단 오버뷰(요약) 항상 표시 ----
col1, col2, col3, col4 = st.columns(4)
snap_list = dm.list_snapshots(days=8)
today_cnt = len(df_all) if df_all is not None else 0
yest_df = dm.load_snapshot(datetime.now(KST).date() - timedelta(days=1))
yest_cnt = len(yest_df) if yest_df is not None else 0
delta_1d = today_cnt - yest_cnt

srv = dm.runs_summary(days=7)
with col1:
    st.metric("현재 레코드 수", today_cnt, delta=delta_1d)
with col2:
    st.metric("스냅샷 보유(최근 8일)", len(snap_list))
with col3:
    st.metric("오늘 변경 수(서버)", srv.get("today_changes", 0) if srv else 0)
with col4:
    st.metric("실패 run(오늘)", srv.get("today_failed_runs", 0) if srv else 0)

st.divider()

# 공통 필터 적용본 (현재표)
def apply_filters_view(df):
    return apply_filters(df, sel_model, sel_group)

df_filtered = apply_filters_view(df_all)

# ===============================
# 1) 히스토리 관리 — CRUD 데일리 상세
# ===============================
if nav == "히스토리 관리":
    st.subheader("히스토리 관리 (데일리 변경 CRUD)")
    target_day = st.date_input("대상 일자(오늘 기준 비교: 전일 ↔ 선택일)", value=datetime.now(KST).date())
    prev_day = target_day - timedelta(days=1)

    df_curr = dm.load_snapshot(target_day) or df_filtered
    df_prev = dm.load_snapshot(prev_day)

    # 필터 적용
    df_curr = apply_filters(df_curr, sel_model, sel_group) if df_curr is not None else None
    df_prev = apply_filters(df_prev, sel_model, sel_group) if df_prev is not None else None

    created, updated, deleted = daily_changes(df_prev, df_curr)

    q = st.text_input("검색(모든 컬럼 포함, 대소문자 무시)", value="")
    def search(df):
        if df is None or df.empty or not q: return df
        ql = q.lower()
        return df[df.astype(str).apply(lambda s: s.str.lower().str.contains(ql, na=False)).any(axis=1)]

    t1, t2, t3 = st.tabs([
        f"신규 생성 ({len(created)})", f"업데이트 ({len(updated)})", f"삭제 ({len(deleted)})"
    ])

    with t1:
        dfv = search(created)
        st.dataframe(dfv, use_container_width=True, height=360)
        st.download_button("CSV 다운로드(신규)", dfv.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"created_{target_day}.csv", mime="text/csv")

    with t2:
        dfv = search(updated)
        st.dataframe(dfv, use_container_width=True, height=360)
        st.download_button("CSV 다운로드(업데이트)", dfv.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"updated_{target_day}.csv", mime="text/csv")

    with t3:
        dfv = search(deleted)
        st.dataframe(dfv, use_container_width=True, height=360)
        st.download_button("CSV 다운로드(삭제)", dfv.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"deleted_{target_day}.csv", mime="text/csv")

# ===============================
# 2) 피처 상세 — 선택한 그룹의 피처를 직관적으로
# ===============================
elif nav == "피처 상세":
    st.subheader("피처 상세 조회")
    if df_filtered is None or df_filtered.empty:
        st.info("데이터가 없습니다. 모델/그룹을 변경하거나 동기화하세요.")
    else:
        features = ["(전체)"] + sorted(df_filtered["feature"].dropna().unique().tolist())
        feature_sel = st.selectbox("피처 선택", features, index=0, help="왼쪽에서 모델/피처 그룹 선택 후, 피처를 고르세요.")
        df_feat = df_filtered if feature_sel == "(전체)" else df_filtered[df_filtered["feature"] == feature_sel]

        c1, c2 = st.columns(2)
        with c1:
            st.write("모드 분포")
            st.bar_chart(df_feat["mode"].value_counts())
        with c2:
            st.write("운영자/국가 분포")
            st.bar_chart(df_feat["operator"].value_counts().head(10))

        st.divider()
        st.dataframe(df_feat, use_container_width=True, height=420)
        st.download_button("CSV 다운로드(피처 상세)", df_feat.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"feature_detail_{datetime.now(KST):%Y%m%d}.csv", mime="text/csv")

# ===============================
# 3) 데이터 탐색 — 현재표 자유 필터링
# ===============================
else:
    st.subheader("데이터 탐색 (현재표)")
    if df_filtered is None or df_filtered.empty:
        st.info("데이터가 없습니다. 모델/그룹을 변경하거나 동기화하세요.")
    else:
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            mode_sel = st.multiselect("Mode", options=sorted(df_filtered["mode"].dropna().unique()), default=[])
        with colf2:
            country_sel = st.multiselect("Country", options=sorted(df_filtered["country"].dropna().unique()), default=[])
        with colf3:
            op_sel = st.multiselect("Operator", options=sorted(df_filtered["operator"].dropna().unique()), default=[])

        df_view = df_filtered.copy()
        if mode_sel:    df_view = df_view[df_view["mode"].isin(mode_sel)]
        if country_sel: df_view = df_view[df_view["country"].isin(country_sel)]
        if op_sel:      df_view = df_view[df_view["operator"].isin(op_sel)]

        st.dataframe(df_view, use_container_width=True, height=420)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("피처 Top10")
            st.bar_chart(df_view["feature"].value_counts().head(10))
        with c2:
            st.write("국가 Top10")
            st.bar_chart(df_view["country"].value_counts().head(10))

        st.download_button("CSV 다운로드(현재표 뷰)", df_view.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"fmw_view_{datetime.now(KST):%Y%m%d_%H%M}.csv", mime="text/csv")
