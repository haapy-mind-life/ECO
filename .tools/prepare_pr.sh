#!/usr/bin/env bash
set -euo pipefail

# ===== 설정 =====
BASE_BRANCH="${BASE_BRANCH:-main}"
FEATURE_BRANCH="${FEATURE_BRANCH:-feature/streamlit-ux-$(date +%Y%m%d-%H%M)}"

echo "==> Git 점검/동기화"
git status >/dev/null
git fetch origin --prune
git checkout -B "${FEATURE_BRANCH}" "origin/${BASE_BRANCH}"

# ===== devcontainer =====
mkdir -p .devcontainer
cat > .devcontainer/devcontainer.json <<'JSON'
{
  "name": "ECO Codespace",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "forwardPorts": [8501],
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python","ms-python.vscode-pylance"]
    }
  },
  "postCreateCommand": "pip install -r requirements.txt && python - <<'PY'\nimport importlib\nfor m in ['streamlit','pandas','requests','pyarrow']:\n    importlib.import_module(m)\nprint('SMOKE_OK')\nPY"
}
JSON

# ===== 프로젝트 파일(최신 캔버스 상태 반영) =====
mkdir -p .streamlit app/core app/views app/data scripts .github/workflows

cat > requirements.txt <<'REQ'
streamlit>=1.33,<2.0
pandas>=2.0,<3.0
requests>=2.31
pyarrow>=14.0
# optional: 유사검색/추천이 필요하면 사용
# rapidfuzz>=3.9
REQ

cat > .streamlit/config.toml <<'TOML'
[server]
port = 8501
baseUrlPath = "/fmw"
enableXsrfProtection = true
enableCORS = false
TOML

cat > main.py <<'PY'
from __future__ import annotations
from typing import List, Tuple
import os, time, requests
import pandas as pd
import streamlit as st

from app.core.navigation import get_pages
from app.data.sample_features import distinct_values, load_feature_dataframe
from app.data.data_manager import DataManager
from app.views.state import FilterState

def _init_session_state() -> FilterState:
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = FilterState()
    return st.session_state.filter_state

@st.cache_data(ttl=86400)
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
    qs = st.experimental_get_query_params()
    vals = qs.get(name, [])
    if not vals:
        return []
    merged = []
    for v in vals:
        merged.extend([x.strip() for x in v.split(",") if x.strip()])
    return merged

def _sync_qs_from_state(state: FilterState) -> None:
    st.experimental_set_query_params(
        models=state.models or None,
        feature_groups=state.feature_groups or None,
    )

def _render_sidebar(filter_state: FilterState) -> str:
    pages = get_pages()
    labels = [page.label for page in pages]

    st.sidebar.title("🧭 내비게이션")
    selected_label = st.sidebar.radio("메인 기능", labels, key="main_navigation")

    selected_page = next(p for p in pages if p.label == selected_label)
    if selected_page.description:
        st.sidebar.caption(selected_page.description)

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

    filter_state.models = st.sidebar.multiselect(
        "모델",
        distinct_values("model"),
        default=filter_state.models,
        key="sidebar_models",
        placeholder="모델을 선택하세요",
    )
    filter_state.feature_groups = st.sidebar.multiselect(
        "FEATURE GROUP",
        distinct_values("feature_group"),
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

    runtime_mode = st.secrets.get("RUNTIME_MODE", os.getenv("RUNTIME_MODE", "cloud")).lower()
    api_base = st.secrets.get("API_BASE", os.getenv("API_BASE", "https://10.x.x.x"))
    verify_ssl = bool(str(st.secrets.get("VERIFY_SSL", os.getenv("VERIFY_SSL", "false"))).lower() in ("1","true","yes"))
    token = st.secrets.get("API_ACCESS_TOKEN", os.getenv("API_ACCESS_TOKEN", None))
    data_dir = os.getenv("DATA_DIR", "./_cache")

    if runtime_mode == "cloud":
        try:
            dataframe, last = _cloud_fetch_feature1(api_base, verify_ssl, token)
            st.session_state["data_manager"] = None
            st.session_state["last_sync_txt"] = time.strftime("%Y-%m-%d %H:%M:%S KST", time.gmtime(last + 9*3600))
        except Exception:
            dataframe = load_feature_dataframe()
            st.session_state["last_sync_txt"] = "샘플 데이터(Cloud API 미접속)"
    else:
        dm = DataManager(api_base=api_base, data_dir=data_dir, verify_ssl=verify_ssl)
        st.session_state["data_manager"] = dm
        dm.refresh_if_stale("feature1", max_age_hours=24)
        dataframe = dm.load("feature1")
        if dataframe.empty:
            dataframe = load_feature_dataframe()

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
PY

cat > app/core/navigation.py <<'PY'
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
import pandas as pd

from app.views.home import render_home
from app.views.state import FilterState
from app.views.visualization import render_visualization

RenderFn = Callable[[FilterState, pd.DataFrame], FilterState]

@dataclass(frozen=True)
class Page:
    label: str
    renderer: RenderFn
    description: str | None = None

_DEFAULT_PAGES: tuple[Page, ...] = (
    Page("🏠 홈", render_home, "필터 기반 홈 대시보드"),
    Page("📈 시각화", render_visualization, "선택된 FEATURE GROUP 기준 가이드"),
)

def get_pages(extra_pages: Iterable[Page] | None = None) -> Sequence[Page]:
    if not extra_pages:
        return _DEFAULT_PAGES
    return _DEFAULT_PAGES + tuple(extra_pages)
PY

cat > app/views/state.py <<'PY'
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class FilterState:
    models: List[str] = field(default_factory=list)
    feature_groups: List[str] = field(default_factory=list)
    mcc: List[str] = field(default_factory=list)
    mnc: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)

    def apply(self, dataframe):
        df = dataframe
        selectors = {
            "model": self.models,
            "feature_group": self.feature_groups,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "region": self.regions,
            "country": self.countries,
            "operator": self.operators,
            "feature_name": self.features,
        }
        for column, selected in selectors.items():
            if selected and column in df.columns:
                df = df[df[column].isin(selected)]
        return df

    def active_visualization_groups(self, dataframe) -> List[str]:
        filtered = self.apply(dataframe)
        if "visualization_group" not in filtered.columns:
            return []
        groups = filtered["visualization_group"].dropna().unique().tolist()
        groups.sort()
        return groups
PY

cat > app/views/home.py <<'PY'
from __future__ import annotations
import pandas as pd
import streamlit as st
from app.data.data_manager import DataManager
from app.data.sample_features import distinct_values, FEATURE_GROUP_SCHEMA
from app.views.state import FilterState
import re

def _mccmnc_ok(s: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{2}", s.strip()))

def _multiselect(label: str, options, default, key: str):
    return st.multiselect(label, options, default=default, key=key, placeholder="검색하거나 값을 입력하세요")

def render_home(filter_state: FilterState, dataframe: pd.DataFrame):
    st.title("📊 Feature Monitoring Home")

    last_sync_txt = "-"
    dm: DataManager | None = st.session_state.get("data_manager")
    if dm:
        last = dm.last_sync_at("feature1")
        last_sync_txt = dm.format_last_sync(last)
    else:
        last_sync_txt = st.session_state.get("last_sync_txt", "-")
    st.caption(f"마지막 DB 싱크: **{last_sync_txt}** · 싱크 주기: **매일 1회** · 조회 전용")

    dims = {"region","country","operator","mcc_mnc"}
    if filter_state.feature_groups and len(filter_state.feature_groups) == 1:
        g = filter_state.feature_groups[0]
        dims = set(FEATURE_GROUP_SCHEMA.get(g, {}).get("dims", list(dims)))

    st.subheader("상세 필터")
    col1, col2, col3 = st.columns(3)

    with col1:
        if "mcc_mnc" in dims:
            mccmnc = st.text_input("MCC-MNC(정확히: NNN-NN)", key="home_mccmnc", placeholder="예: 450-05")
            if mccmnc and not _mccmnc_ok(mccmnc):
                st.error("MCC-MNC 형식은 NNN-NN (예: 450-05)")
                st.stop()
            if mccmnc:
                try:
                    mcc, mnc = mccmnc.split("-")
                    filter_state.mcc = [mcc]
                    filter_state.mnc = [mnc]
                except Exception:
                    pass
        else:
            filter_state.mcc, filter_state.mnc = [], []

    with col2:
        if "region" in dims:
            filter_state.regions = _multiselect("지역", distinct_values("region"), filter_state.regions, "home_region")
        else:
            filter_state.regions = []
        if "country" in dims:
            filter_state.countries = _multiselect("국가", distinct_values("country"), filter_state.countries, "home_country")
        else:
            filter_state.countries = []

    with col3:
        if "operator" in dims:
            filter_state.operators = _multiselect("사업자", distinct_values("operator"), filter_state.operators, "home_operator")
        else:
            filter_state.operators = []
        filter_state.features = _multiselect("FEATURE", distinct_values("feature_name"), filter_state.features, "home_feature")

    filtered_df = filter_state.apply(dataframe).copy()

    st.divider()
    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("행 수", len(filtered_df))
    with k2: st.metric("모델 수", int(filtered_df["model"].nunique()) if not filtered_df.empty and "model" in filtered_df else 0)
    with k3: st.metric("FEATURE 수", int(filtered_df["feature_name"].nunique()) if not filtered_df.empty and "feature_name" in filtered_df else 0)
    with k4: st.metric("사업자 수", int(filtered_df["operator"].nunique()) if not filtered_df.empty and "operator" in filtered_df else 0)

    if filtered_df.empty:
        st.warning("조건에 맞는 결과가 없습니다.")
        with st.expander("추천 검색 보기"):
            st.write("• 인기 FEATURE:", ", ".join(distinct_values("feature_name")[:5]))
            st.write("• 인기 사업자:", ", ".join(distinct_values("operator")[:5]))
            st.write("• 인기 MCC:", ", ".join(distinct_values("mcc")[:5]))
        return filter_state

    if "status" in filtered_df.columns:
        def _badge(x: str) -> str:
            x = (x or "").lower()
            if "avail" in x: return "🟢 Available"
            if "pilot" in x: return "🟡 Pilot"
            if "plan" in x or "progress" in x: return "🔵 Planned"
            return x or "-"
        filtered_df["status"] = filtered_df["status"].map(_badge)

    preferred = ["feature_group","feature_name","model","region","country","operator","mcc","mnc","status","last_updated"]
    cols = [c for c in preferred if c in filtered_df.columns] + [c for c in filtered_df.columns if c not in preferred]

    st.subheader("검색 결과")
    st.dataframe(filtered_df[cols], hide_index=True, use_container_width=True)

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
PY

cat > app/views/visualization.py <<'PY'
from __future__ import annotations
import pandas as pd
import streamlit as st
from app.data.sample_features import visualization_capabilities, visualization_group_titles
from app.views.state import FilterState

def render_visualization(filter_state: FilterState, dataframe: pd.DataFrame):
    st.title("📈 시각화 작업 공간")
    st.info("이 영역은 **작업 중(WIP)** 입니다. 차트/지도 템플릿은 단계적으로 연결됩니다.")
    st.caption("선택한 FEATURE GROUP에 따라 사용 가능한 시각화가 달라집니다.")

    groups = filter_state.active_visualization_groups(dataframe)
    titles = visualization_group_titles()
    capabilities = visualization_capabilities()

    if not groups:
        st.info("사이드바와 홈 화면에서 FEATURE GROUP을 선택하면 여기에서 사용할 수 있는 시각화 유형이 노출됩니다.")
        return filter_state

    readable = [titles.get(group, group) for group in groups]
    selected_label = st.selectbox("시각화 그룹", readable, key="viz_group_selector")
    inverse_titles = {v: k for k, v in titles.items()}
    selected_group = inverse_titles.get(selected_label, selected_label)

    st.markdown("### 지원되는 시각화")
    for item in capabilities.get(selected_group, []):
        st.markdown(f"- {item}")

    st.divider()
    st.markdown("### 미리보기(샘플)")
    base = filter_state.apply(dataframe)
    if base.empty:
        st.info("선택된 데이터가 없습니다. 홈에서 필터를 확장해 보세요.")
        return filter_state

    c1, c2 = st.columns(2)
    with c1:
        st.caption("모델별 FEATURE 개수")
        g = base.groupby("model")["feature_name"].nunique().reset_index(name="count").sort_values("count", ascending=False)
        st.bar_chart(g, x="model", y="count", use_container_width=True)
    with c2:
        st.caption("사업자별 FEATURE 개수")
        g2 = base.groupby("operator")["feature_name"].nunique().reset_index(name="count").sort_values("count", ascending=False)
        g2["operator"] = g2["operator"].fillna("(N/A)")
        st.bar_chart(g2, x="operator", y="count", use_container_width=True)

    return filter_state
PY

cat > app/data/sample_features.py <<'PY'
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List
import pandas as pd

@dataclass(frozen=True)
class FeatureRecord:
    feature_group: str
    feature_name: str
    model: str
    mcc: str
    mnc: str
    region: str
    country: str
    operator: str
    status: str
    last_updated: str
    visualization_group: str

_DATA: List[FeatureRecord] = [
    FeatureRecord("Roaming Essentials", "Automatic APN Switch", "XR-550", "450", "05", "APAC", "Korea", "SKT", "Available", "2025-05-12", "Full Suite"),
    FeatureRecord("Roaming Essentials", "Dual SIM Failover", "XR-520", "440", "10", "APAC", "Japan", "DoCoMo", "Pilot", "2025-04-29", "Full Suite"),
    FeatureRecord("Security Core", "IMS Firewall", "XR-550", "208", "01", "EMEA", "France", "Orange", "Available", "2025-02-14", "Tabular Only"),
    FeatureRecord("Security Core", "Signalling Anomaly Detection", "XR-540", "724", "06", "LATAM", "Brazil", "Vivo", "In Progress", "2025-03-03", "Tabular Only"),
    FeatureRecord("Premium Insights", "Traffic Heatmap", "XR-600", "310", "260", "NA", "United States", "T-Mobile", "Available", "2025-06-01", "Full Suite"),
    FeatureRecord("Premium Insights", "KPI Correlation", "XR-600", "234", "15", "EMEA", "United Kingdom", "Vodafone", "Planned", "2025-05-05", "Full Suite"),
    FeatureRecord("Connectivity Essentials", "VoLTE Optimiser", "XR-520", "404", "45", "APAC", "India", "Jio", "Pilot", "2025-01-25", "Tabular Only"),
    FeatureRecord("Connectivity Essentials", "NR Fallback Enhancer", "XR-530", "262", "02", "EMEA", "Germany", "Telekom", "Available", "2025-04-17", "Full Suite"),
]

FEATURE_GROUP_SCHEMA: Dict[str, Dict] = {
    "Roaming Essentials": {"dims":["region","country","operator","mcc_mnc"], "value_type":"bool", "list_modes":["allow","block"]},
    "Security Core": {"dims":["region","country","operator"], "value_type":"str", "list_modes":["allow"]},
    "Premium Insights": {"dims":["region","country"], "value_type":"number", "list_modes":["allow"]},
}

@lru_cache(maxsize=1)
def load_feature_dataframe() -> pd.DataFrame:
    frame = pd.DataFrame([r.__dict__ for r in _DATA])
    frame.sort_values(["feature_group", "feature_name"], inplace=True)
    frame.reset_index(drop=True, inplace=True)
    return frame

def distinct_values(column: str) -> List[str]:
    df = load_feature_dataframe()
    return sorted(df[column].dropna().unique().tolist())

@lru_cache(maxsize=None)
def visualization_capabilities() -> Dict[str, List[str]]:
    return {
        "Full Suite": [
            "Feature summary table",
            "Time series / KPI charts",
            "Traffic density heatmap",
            "Geo heatmap (Leaflet)"
        ],
        "Tabular Only": ["Feature summary table"]
    }

@lru_cache(maxsize=None)
def visualization_group_titles() -> Dict[str, str]:
    return {
        "Full Suite": "그룹 1 – 전체 시각화 지원",
        "Tabular Only": "그룹 2 – 표 기반 시각화"
    }
PY

cat > app/data/data_manager.py <<'PY'
from __future__ import annotations
import json, time, pathlib, threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import pandas as pd
import requests

KST = timezone(timedelta(hours=9))

class DataManager:
    """DRF에서 하루 1회 동기화→로컬 캐시(Parquet)를 제공하고, 앱은 캐시만 조회."""
    def __init__(self, api_base: str, data_dir: str = "./_cache", verify_ssl: bool = False, timeout: int = 20):
        self.api_base = api_base.rstrip("/")
        self.data_dir = pathlib.Path(data_dir)
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.data_dir / "_meta.json"
        self.lock = threading.Lock()
        self._meta = self._load_meta()

    def _load_meta(self) -> Dict:
        if self.meta_path.exists():
            try:
                return json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_meta(self):
        tmp = json.dumps(self._meta, ensure_ascii=False, indent=2)
        self.meta_path.write_text(tmp, encoding="utf-8")

    def _dataset_paths(self, name: str):
        return (self.data_dir / f"{name}.parquet",)

    def last_sync_at(self, name: str) -> Optional[datetime]:
        ts = self._meta.get(name, {}).get("last_sync_epoch")
        if not ts:
            return None
        return datetime.fromtimestamp(int(ts), tz=KST)

    def _set_sync_meta(self, name: str, etag: Optional[str] = None):
        entry = self._meta.get(name, {})
        entry["last_sync_epoch"] = int(time.time())
        if etag:
            entry["etag"] = etag
        self._meta[name] = entry
        self._save_meta()

    def _drf_get(self, path: str, params: Optional[dict] = None, etag: Optional[str] = None):
        url = f"{self.api_base}/{path.lstrip('/')}"
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        r = requests.get(url, params=params or {}, headers=headers, timeout=self.timeout, verify=self.verify_ssl)
        if r.status_code == 304:
            return None, etag
        r.raise_for_status()
        return r.json(), r.headers.get("ETag")

    def _save_parquet(self, name: str, data):
        df = pd.DataFrame(data["results"] if isinstance(data, dict) and "results" in data else data)
        path, = self._dataset_paths(name)
        df.to_parquet(path, index=False)
        return df

    def sync_feature(self, name: str = "feature1", path: str = "/api/feature1/", params=None) -> pd.DataFrame:
        with self.lock:
            meta = self._meta.get(name, {})
            etag = meta.get("etag")
            res, new_etag = self._drf_get(path, params=params, etag=etag)
            if res is None:
                return self.load(name, stale_ok=True)
            df = self._save_parquet(name, res)
            self._set_sync_meta(name, etag=new_etag or etag)
            return df

    def load(self, name: str, stale_ok=True) -> pd.DataFrame:
        path, = self._dataset_paths(name)
        if not path.exists():
            try:
                return self.sync_feature(name=name)
            except Exception:
                return pd.DataFrame()
        return pd.read_parquet(path)

    def refresh_if_stale(self, name: str, max_age_hours: int = 24) -> None:
        last = self.last_sync_at(name)
        if last and (datetime.now(tz=KST) - last) < timedelta(hours=max_age_hours):
            return

        def _bg():
            try:
                self.sync_feature(name=name)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()

    @staticmethod
    def format_last_sync(dt: Optional[datetime]) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S KST") if dt else "-"
PY

cat > scripts/sync_data.py <<'PY'
#!/usr/bin/env python3
import os
from app.data.data_manager import DataManager

API_BASE = os.getenv("API_BASE", "https://10.x.x.x")
DATA_DIR = os.getenv("DATA_DIR", "/srv/fmw/_cache")
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() in ("1","true","yes")

if __name__ == "__main__":
    dm = DataManager(api_base=API_BASE, data_dir=DATA_DIR, verify_ssl=VERIFY_SSL)
    df = dm.sync_feature(name="feature1", path="/api/feature1/", params={"limit": 500000})
    print(f"synced rows={len(df)} last_sync={dm.last_sync_at('feature1')}")
PY
chmod +x scripts/sync_data.py

for d in app app/core app/views app/data scripts; do
  [ -f "$d/__init__.py" ] || : > "$d/__init__.py"
done

cat > .github/pull_request_template.md <<'MD'
# ECO: Streamlit UX 개선 적용

## 변경 요약
- URL 딥링크(쿼리 파라미터) 반영
- 그룹 인지형 상세 필터(차원 토글)
- 빈 결과 가이드 및 KPI 카드
- CSV 다운로드 가드(보안 동의 + 행 제한)
- (On-prem) DRF→Parquet 일일 동기화 / 캐시 로더

## 체크리스트
- [ ] `streamlit run main.py` 로컬 구동 확인
- [ ] DRF API 접근성(사내/Cloud) 확인
- [ ] 데이터 스키마 컬럼 확인
- [ ] Nginx `/fmw` 경로 점검
- [ ] 보안 가이드 복기(내부 반출 금지)
MD

cat > .github/workflows/ci.yml <<'YML'
name: CI
on:
  pull_request:
    branches: [ main, develop ]
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Import smoke
        run: |
          python - << 'PY'
          import importlib
          for m in ["streamlit","pandas","requests","pyarrow"]:
              importlib.import_module(m)
          print("OK")
          PY
YML

cat > .gitignore <<'GIT'
_cache/
**/__pycache__/
*.pyc
.DS_Store
.streamlit/secrets.toml
GIT

python -m pip install --upgrade pip
pip install -r requirements.txt
python - <<'PY'
import importlib
for m in ["streamlit","pandas","requests","pyarrow"]:
    importlib.import_module(m)
print("SMOKE_OK")
PY

git add -A
if git diff --cached --quiet; then
  echo "==> 변경 사항이 없어 커밋을 생략합니다."
else
  git commit -m "feat(streamlit): 홈 UX/일일 동기화/URL 딥링크 적용 (Codespaces 원키)"
  git push -u origin "${FEATURE_BRANCH}"

  if command -v gh >/dev/null 2>&1; then
    gh pr create --base "${BASE_BRANCH}" --head "${FEATURE_BRANCH}" \
      --title "feat(streamlit): 홈 UX + 일일 동기화 + URL 딥링크" \
      --body-file .github/pull_request_template.md || true
    echo "PR 링크 열기..."
    gh pr view --web || true
  else
    echo "⚠️ GitHub CLI(gh)가 없어 웹에서 PR을 생성하세요."
  fi
fi

echo "==> 완료"
