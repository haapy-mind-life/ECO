from __future__ import annotations
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from app.data.data_manager import DataManager

@st.cache_resource
def get_scheduler():
    sched = BackgroundScheduler(timezone=timezone("Asia/Seoul"))
    sched.start()
    return sched

st.title("데이터 매니저 - 스케줄러(보조)")
st.caption("*참고: 프로덕션에서는 서버 cron(06:00)과 병행 권장*")

dm = DataManager()
sched = get_scheduler()

# 06:00 스케줄 등록(중복 방지)
exists = any(j.id == "nightly6" for j in sched.get_jobs())
if not exists:
    sched.add_job(dm.trigger_sync_now, "cron", hour=6, minute=0, id="nightly6")
    st.success("매일 06:00 동기화 스케줄 등록 완료 (보조)")
else:
    st.info("스케줄이 이미 등록되어 있습니다.")

if st.button("지금 동기화 실행"):
    try:
        resp = dm.trigger_sync_now()
        st.success("동기화 요청 완료")
        st.json(resp)
    except Exception as e:
        st.error(f"실패: {e}")
