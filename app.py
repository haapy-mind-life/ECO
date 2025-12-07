import streamlit as st
import time
import random

# ==========================================
# 1. 페이지 기본 설정
# ==========================================
st.set_page_config(
    page_title="Auto-Act System",
    page_icon="🕹️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS 스타일링
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 20px; }
    div.stButton > button:first-child {
        background-color: #007bff; color: white; border: none;
        padding: 10px 24px; font-size: 16px; border-radius: 8px;
    }
    div.stButton > button:hover { background-color: #0056b3; color: white; }
    .device-card {
        background-color: #f8f9fa; color: #333;
        padding: 15px; border-radius: 10px;
        border: 1px solid #ddd; margin-bottom: 10px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .status-pass { color: #28a745; font-weight: bold; }
    .status-fail { color: #dc3545; font-weight: bold; }
    .status-run { color: #ffc107; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 세션 상태 초기화
# ==========================================
if 'devices' not in st.session_state:
    st.session_state['devices'] = [
        {"id": i+1, "status": "Ready", "progress": 0, "log": "대기 중..."} 
        for i in range(10)
    ]
if 'is_running' not in st.session_state:
    st.session_state['is_running'] = False


# ==========================================
# [중요] 함수 정의를 실행 로직보다 먼저 선언해야 함
# ==========================================
def render_dashboard(placeholder, devices_data):
    """화면을 그리는 함수"""
    with placeholder.container():
        # 5개씩 2줄로 나누어 표시
        for row in range(2):
            cols = st.columns(5)
            for col_idx in range(5):
                device_idx = row * 5 + col_idx
                if device_idx < len(devices_data):
                    dev = devices_data[device_idx]
                    
                    with cols[col_idx]:
                        # 상태별 스타일 클래스 지정
                        status_class = "status-run"
                        if "PASS" in dev['status']: status_class = "status-pass"
                        elif "FAIL" in dev['status']: status_class = "status-fail"
                        
                        # HTML 카드 렌더링
                        st.markdown(f"""
                            <div class="device-card">
                                <h4>Device {dev['id']}</h4>
                                <div class="{status_class}">{dev['status']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.progress(dev['progress'])
                        st.caption(f"Log: {dev['log']}")
            
            if row == 0:
                st.divider()


# ==========================================
# 3. UI 헤더 및 입력부
# ==========================================
st.title("🚀 사내 자동화 시스템 (Auto-Act Controller)")
st.markdown("---")

col_input, col_control = st.columns([3, 1])

with col_input:
    email_content = st.text_area(
        "📧 작업 요청 메일 붙여넣기", 
        height=100, 
        placeholder="여기에 메일 내용을 복사+붙여넣기 하세요.\n(예: 퀵빌드 링크가 포함된 텍스트)"
    )

with col_control:
    st.write("Control Panel")
    start_btn = st.button("▶ 자동화 시작", use_container_width=True)
    
    if start_btn:
        if not email_content.strip():
             st.error("메일 내용을 입력해주세요!")
        else:
            st.session_state['is_running'] = True
            st.toast("작업이 시작되었습니다! 하단 모니터를 확인하세요.")


# ==========================================
# 4. 메인 대시보드 로직
# ==========================================
st.subheader("🖥️ 실시간 단말 모니터링 (Real-time Monitor)")

dashboard_placeholder = st.empty()

# 실행 중일 때 루프
if st.session_state['is_running']:
    
    # 30 프레임 동안 시뮬레이션
    for _ in range(30): 
        active_devices = 0
        for dev in st.session_state['devices']:
            # 완료되지 않았고 실패하지 않은 경우만 진행
            if dev['progress'] < 100 and "FAIL" not in dev['status']:
                active_devices += 1
                dev['progress'] += random.randint(2, 8)
                dev['status'] = "Running 🔄"
                dev['log'] = f"테스트 수행 중... ({dev['progress']}%)"

                # 에러 시뮬레이션 (3번, 7번 단말)
                if dev['id'] in [3, 7] and dev['progress'] > 40 and random.random() > 0.85:
                    dev['status'] = "FAIL ❌"
                    dev['progress'] = 40
                    dev['log'] = "!! 오류: 테스트 타임아웃 발생"

                # 성공 처리
                if dev['progress'] >= 100:
                    dev['progress'] = 100
                    dev['status'] = "PASS ✅"
                    dev['log'] = "모든 테스트 및 Act 완료."
        
        # 함수 호출 (이제 함수가 위에 정의되어 있어서 에러 안 남)
        render_dashboard(dashboard_placeholder, st.session_state['devices'])
        
        if active_devices == 0:
            break
            
        time.sleep(0.3)
    
    st.session_state['is_running'] = False
    st.success("모든 작업이 종료되었습니다.")

else:
    # 대기 상태일 때 한 번 그려주기
    render_dashboard(dashboard_placeholder, st.session_state['devices'])


# ==========================================
# 5. 하단 로그
# ==========================================
st.markdown("---")
with st.expander("📜 시스템 상세 로그 확인", expanded=False):
    st.code("2023-10-27 10:00:01 | 시스템 초기화 완료.\n2023-10-27 10:00:15 | 사용자 메일 입력 대기 중...", language="log")
