#!/usr/bin/env python3
import os
from app.data.data_manager import DataManager

if __name__ == "__main__":
    dm = DataManager(data_dir=os.getenv("DATA_DIR", "./_cache"))
    # 백엔드 배치 트리거 → ImportRun 생성
    resp = dm.trigger_sync_now()
    print("triggered:", resp)
