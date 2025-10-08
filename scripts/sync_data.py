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
