"""Shared data structures that describe the UI state across views."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class FilterState:
    """Represents the currently selected filters."""

    models: List[str] = field(default_factory=list)
    feature_groups: List[str] = field(default_factory=list)
    mcc: List[str] = field(default_factory=list)
    mnc: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)

    def apply(self, dataframe):
        """Return a filtered dataframe based on the state selections."""

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
            if selected:
                df = df[df[column].isin(selected)]
        return df

    def active_visualization_groups(self, dataframe) -> List[str]:
        """Return distinct visualization groups for the filtered dataframe."""

        filtered = self.apply(dataframe)
        if "visualization_group" not in filtered.columns:
            return []
        groups = filtered["visualization_group"].dropna().unique().tolist()
        groups.sort()
        return groups
