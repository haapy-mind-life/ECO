from __future__ import annotations
import json
import streamlit as st
import pandas as pd
from app.data.data_manager import DataManager

dm = DataManager()

def render_history():
    st.title("🕒 변경 이력")
    st.caption("동기화 후 ImportRun 요약과 로그를 제공합니다.")

    # 상단: 스케줄/수동 실행
    with st.expander("동기화 실행/스케줄", expanded=False):
        col1, col2 = st.columns(2)
        if col1.button("지금 동기화 실행"):
            try:
                resp = dm.trigger_sync_now()
                st.success("동기화 요청 완료") ; st.json(resp)
            except Exception as e:
                st.error(f"실패: {e}")
        st.caption("프로덕션에서는 서버 cron 06:00 실행을 권장합니다.")

    # ImportRun 리스트
    runs = dm.sync_runs()
    if runs.empty:
        st.info("Run 정보가 없습니다. 백엔드 `/api/sync/` 뷰셋을 확인하세요.")
        return

    # 가벼운 컬럼 선택
    cols = [c for c in runs.columns if c in ("id","status","source_tag","stats","started_at","finished_at")]
    st.subheader("최근 Run")
    st.dataframe(runs[cols], use_container_width=True)

    # 선택한 Run 상세(stats 파싱)
    st.subheader("Run 상세")
    run_ids = runs["id"].tolist()
    if not run_ids:
        st.stop()

    sel = st.selectbox("Run ID", run_ids)
    row = runs[runs["id"] == sel].iloc[0].to_dict()
    st.write({k: row.get(k) for k in cols if k in row})
    try:
        stats = row.get("stats") or {}
        if isinstance(stats, str):
            stats = json.loads(stats)
    except Exception:
        stats = {}
    if stats:
        st.json(stats)

    st.divider()
    st.subheader("변경 로그(최대 1,000건)")
    logs = dm.sync_logs()
    if logs.empty:
        st.info("로그 API(`/api/feature-record-logs/`)가 아직 없거나 데이터가 없습니다.")
    else:
        st.dataframe(logs, use_container_width=True)
