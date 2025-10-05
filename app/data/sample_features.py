"""Sample dataset used by the Streamlit prototype.

The dataset now expands to 500 records so the filtering widgets and
visualisation toggles receive enough diversity when deployed to
Streamlit Cloud.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from itertools import cycle
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


_BASE_RECORDS: List[FeatureRecord] = [
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


def _build_dataset(total: int = 500) -> List[FeatureRecord]:
    statuses = ["Available", "Pilot", "In Progress", "Planned"]
    records: List[FeatureRecord] = []
    for index, template in enumerate(cycle(_BASE_RECORDS), start=1):
        if len(records) >= total:
            break

        batch = (index - 1) // len(_BASE_RECORDS) + 1
        suffix = f"{batch:02d}"
        last_updated = (
            datetime.strptime(template.last_updated, "%Y-%m-%d")
            + timedelta(days=(index - 1) % 45)
        ).strftime("%Y-%m-%d")

        record = FeatureRecord(
            feature_group=template.feature_group,
            feature_name=f"{template.feature_name} #{suffix}",
            model=f"{template.model}-{(batch % 5) + 1}",
            mcc=f"{(int(template.mcc) + index) % 1000:03d}",
            mnc=f"{(int(template.mnc) + batch) % 1000:03d}",
            region=template.region,
            country=template.country,
            operator=f"{template.operator} {batch}",
            status=statuses[(batch - 1) % len(statuses)],
            last_updated=last_updated,
            visualization_group=template.visualization_group,
        )
        records.append(record)
    return records


_DATA: List[FeatureRecord] = _build_dataset(500)


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
