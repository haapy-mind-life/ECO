"""Sample dataset used by the Streamlit prototype.

The dataset is intentionally small but contains enough variety to
exercise the filtering logic that powers the main home screen and
determines which visualisations are available.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class FeatureRecord:
    """Represents a single feature record for the demo application."""

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
    FeatureRecord(
        feature_group="Roaming Essentials",
        feature_name="Automatic APN Switch",
        model="XR-550",
        mcc="450",
        mnc="05",
        region="APAC",
        country="Korea",
        operator="SKT",
        status="Available",
        last_updated="2025-05-12",
        visualization_group="Full Suite",
    ),
    FeatureRecord(
        feature_group="Roaming Essentials",
        feature_name="Dual SIM Failover",
        model="XR-520",
        mcc="440",
        mnc="10",
        region="APAC",
        country="Japan",
        operator="DoCoMo",
        status="Pilot",
        last_updated="2025-04-29",
        visualization_group="Full Suite",
    ),
    FeatureRecord(
        feature_group="Security Core",
        feature_name="IMS Firewall",
        model="XR-550",
        mcc="208",
        mnc="01",
        region="EMEA",
        country="France",
        operator="Orange",
        status="Available",
        last_updated="2025-02-14",
        visualization_group="Tabular Only",
    ),
    FeatureRecord(
        feature_group="Security Core",
        feature_name="Signalling Anomaly Detection",
        model="XR-540",
        mcc="724",
        mnc="06",
        region="LATAM",
        country="Brazil",
        operator="Vivo",
        status="In Progress",
        last_updated="2025-03-03",
        visualization_group="Tabular Only",
    ),
    FeatureRecord(
        feature_group="Premium Insights",
        feature_name="Traffic Heatmap",
        model="XR-600",
        mcc="310",
        mnc="260",
        region="NA",
        country="United States",
        operator="T-Mobile",
        status="Available",
        last_updated="2025-06-01",
        visualization_group="Full Suite",
    ),
    FeatureRecord(
        feature_group="Premium Insights",
        feature_name="KPI Correlation",
        model="XR-600",
        mcc="234",
        mnc="15",
        region="EMEA",
        country="United Kingdom",
        operator="Vodafone",
        status="Planned",
        last_updated="2025-05-05",
        visualization_group="Full Suite",
    ),
    FeatureRecord(
        feature_group="Connectivity Essentials",
        feature_name="VoLTE Optimiser",
        model="XR-520",
        mcc="404",
        mnc="45",
        region="APAC",
        country="India",
        operator="Jio",
        status="Pilot",
        last_updated="2025-01-25",
        visualization_group="Tabular Only",
    ),
    FeatureRecord(
        feature_group="Connectivity Essentials",
        feature_name="NR Fallback Enhancer",
        model="XR-530",
        mcc="262",
        mnc="02",
        region="EMEA",
        country="Germany",
        operator="Telekom",
        status="Available",
        last_updated="2025-04-17",
        visualization_group="Full Suite",
    ),
]


@lru_cache(maxsize=1)
def load_feature_dataframe() -> pd.DataFrame:
    """Return the feature dataset as a pandas DataFrame."""

    frame = pd.DataFrame([record.__dict__ for record in _DATA])
    frame.sort_values(["feature_group", "feature_name"], inplace=True)
    frame.reset_index(drop=True, inplace=True)
    return frame


def distinct_values(column: str) -> List[str]:
    """Return sorted distinct values for the requested column."""

    df = load_feature_dataframe()
    return sorted(df[column].dropna().unique().tolist())


@lru_cache(maxsize=None)
def visualization_capabilities() -> Dict[str, List[str]]:
    """Map each visualization group to the UI elements it supports."""

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
