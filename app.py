import streamlit as st
import time
import random

# ==========================================
# 1. 페이지 기본 설정 (넓은 레이아웃 사용)
# ==========================================
st.set_page_config(
    page_title="Auto-Act System",
    page_icon="🕹️",
    layout="wide",  # 10개 단말을 배치하기 위해 넓은 화면 사용
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS로 카드 디자인 꾸미기 (선택 사항)
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 20px;
    }
    div.stButton > button:first-child {
        background-color: #007bff; color: white; border: none;
        padding: 10px 24px; font-size: 16px; border-radius: 8px;
    }
    div.stButton > button:hover {
        background-color: #0056b3; color: white;
    }
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
# 2. 세션 상태 초기화 (데이터 저장소)
# ==========================================
# Streamlit은 버튼 클릭 시 전체 코드가 재실행되므로,
# 데이터 유지를 위해 session_state를 사용해야 합니다.
if 'devices' not in st.session_state:
    # 10개 단말의 초기 상태 생성
    st.session_state['devices'] = [
        {"id": i+1, "status": "Ready", "progress": 0, "log": "대기 중..."} 
        for i in range(10)
    ]
if 'is_running' not in st.session_state:
    st.session_state['is_running'] = False


# ==========================================
# 3. UI 헤더 및 입력 공간 구성
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
    st.write("Start control")
    # 실행 버튼
    start_btn = st.button("▶ 자동화 시작", use_container_width=True)
    
    if start_btn:
        if not email_content.strip():
             st.error("메일 내용을 입력해주세요!")
        else:
            st.session_state['is_running'] = True
            st.toast("작업이 시작되었습니다! 하단 모니터를 확인하세요.")
            # 실제로는 여기서 Selenium 스레드를 시작하거나 로직을 호출합니다.


# ==========================================
# 4. 메인 대시보드 (10개 단말 그리드)
# ==========================================
st.subheader("🖥️ 실시간 단말 모니터링 (Real-time Monitor)")

# 화면을 동적으로 업데이트하기 위한 컨테이너박스 생성
dashboard_placeholder = st.empty()

# ---> [시뮬레이션 로직 시작] <---
# 실제 적용 시에는 이 루프가 아니라 백그라운드 작업 상태를 읽어와야 합니다.
if st.session_state['is_running']:
    logs_placeholder = st.empty() # 하단 로그창용
    
    for _ in range(30): # 30프레임 동안 애니메이션 시뮬레이션
        # (가상) 데이터 업데이트
        active_devices = 0
        for dev in st.session_state['devices']:
            if dev['progress'] < 100 and dev['status'] != "FAIL":
                active_devices += 1
                dev['progress'] += random.randint(2, 8)
                dev['status'] = "Running 🔄"
                dev['log'] = f"테스트 수행 중... ({dev['progress']}%)"

                # 랜덤 실패 시뮬레이션 (Device 3번, 7번)
                if dev['id'] in [3, 7] and dev['progress'] > 40 and random.random() > 0.85:
                    dev['status'] = "FAIL ❌"
                    dev['progress'] = 40
                    dev['log'] = "!! 오류: 테스트 타임아웃 발생"

                # 성공 완료 처리
                if dev['progress'] >= 100:
                    dev['progress'] = 100
                    dev['status'] = "PASS ✅"
                    dev['log'] = "모든 테스트 및 Act 완료."
        
        # UI 그리기 함수 호출 (아래 정의됨)
        render_dashboard(dashboard_placeholder, st.session_state['devices'])
        
        if active_devices == 0: # 모든 장비가 멈추면 종료
            break
            
        time.sleep(0.3) # 화면 갱신 속도 조절
    
    st.session_state['is_running'] = False
    st.success("모든 작업이 종료되었습니다. 결과를 확인하세요.")

else:
    # 대기 상태일 때 UI 그리기
    render_dashboard(dashboard_placeholder, st.session_state['devices'])
# ---> [시뮬레이션 로직 끝] <---


# ==========================================
# 5. (Helper Function) 대시보드 그리는 함수
# ==========================================
def render_dashboard(placeholder, devices_data):
    # placeholder 컨테이너 안에 내용을 채웁니다.
    with placeholder.container():
        # 5개씩 2줄로 나누어 표시
        for row in range(2):
            cols = st.columns(5)
            for col_idx in range(5):
                device_idx = row * 5 + col_idx
                dev = devices_data[device_idx]
                
                # 각 단말 카드 UI
                with cols[col_idx]:
                    # 상태에 따른 CSS 클래스 선택
                    status_class = "status-run"
                    if "PASS" in dev['status']: status_class = "status-pass"
                    elif "FAIL" in dev['status']: status_class = "status-fail"
                    
                    # HTML을 사용하여 커스텀 카드 디자인 적용
                    st.markdown(f"""
                        <div class="device-card">
                            <h4>Device {dev['id']}</h4>
                            <div class="{status_class}">{dev['status']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 진행률 표시바
                    st.progress(dev['progress'])
                    # 간단한 로그 표시
                    st.caption(f"Log: {dev['log']}")
            # 줄바꿈 구분선
            if row == 0:
                st.divider()

# ==========================================
# 하단: 상세 로그 영역 (예시)
# ==========================================
st.markdown("---")
with st.expander("📜 시스템 상세 로그 확인", expanded=False):
    st.code("2023-10-27 10:00:01 | 시스템 초기화 완료.\n2023-10-27 10:00:15 | 사용자 메일 입력 대기 중...", language="log")

