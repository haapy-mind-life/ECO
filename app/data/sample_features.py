from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List
import pandas as pd

# Schema (DataFrame columns):
#   feature_group:str, feature_name:str, model:str, mcc:str, mnc:str,
#   region:str, country:str, operator:str, status:str, last_updated:str,
#   visualization_group:str

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
    FeatureRecord("Roaming Essentials", "Dual SIM Failover",  "XR-520", "440", "10", "APAC", "Japan", "DoCoMo", "Pilot",    "2025-04-29", "Full Suite"),
    FeatureRecord("Security Core",     "IMS Firewall",          "XR-550", "208", "01", "EMEA", "France", "Orange", "Available", "2025-02-14", "Tabular Only"),
    FeatureRecord("Security Core",     "Signalling Anomaly Detection", "XR-540", "724", "06", "LATAM", "Brazil", "Vivo", "In Progress", "2025-03-03", "Tabular Only"),
    FeatureRecord("Premium Insights",  "Traffic Heatmap",       "XR-600", "310", "260","NA", "United States", "T-Mobile", "Available", "2025-06-01", "Full Suite"),
    FeatureRecord("Premium Insights",  "KPI Correlation",       "XR-600", "234", "15", "EMEA","United Kingdom","Vodafone", "Planned",   "2025-05-05", "Full Suite"),
    FeatureRecord("Connectivity Essentials", "VoLTE Optimiser", "XR-520", "404", "45", "APAC","India", "Jio", "Pilot", "2025-01-25", "Tabular Only"),
    FeatureRecord("Connectivity Essentials", "NR Fallback Enhancer", "XR-530", "262", "02", "EMEA","Germany","Telekom", "Available", "2025-04-17", "Full Suite"),
]

# 그룹별 사용 차원 / Value 타입 / 목록 모드 지원 (UX 제어용)
FEATURE_GROUP_SCHEMA: Dict[str, Dict] = {
    "Roaming Essentials": {"dims":["region","country","operator","mcc_mnc"], "value_type":"bool",   "list_modes":["allow","block"]},
    "Security Core":      {"dims":["region","country","operator"],            "value_type":"str",    "list_modes":["allow"]},
    "Premium Insights":   {"dims":["region","country"],                         "value_type":"number", "list_modes":["allow"]},
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
            "Geo heatmap (Leaflet)",
        ],
        "Tabular Only": [
            "Feature summary table",
        ],
    }

@lru_cache(maxsize=None)
def visualization_group_titles() -> Dict[str, str]:
    return {
        "Full Suite": "그룹 1 – 전체 시각화 지원",
        "Tabular Only": "그룹 2 – 표 기반 시각화",
    }
