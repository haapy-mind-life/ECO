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
    statuses: List[str] = field(default_factory=list)
    visualization_groups: List[str] = field(default_factory=list)

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
            "status": self.statuses,
            "visualization_group": self.visualization_groups,
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
