from __future__ import annotations
import pandas as pd

REQUIRED_COLUMNS = [
    "feature_group","feature_name","model_name","mcc","mnc",
    "region","country","operator","mode","value","status","updated_at"
]

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in REQUIRED_COLUMNS:
        if c not in df.columns:
            df[c] = None
    return df

def distinct_values(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    vals = df[col].dropna().astype(str).unique().tolist()
    vals.sort()
    return vals
