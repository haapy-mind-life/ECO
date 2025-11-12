import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Regression Dashboard v7.5 — Crash Centric", layout="wide")
st.title("📊 Regression Dashboard v7.5 — Crash Centric Edition")

st.markdown("""
### 🔍 목적
- 실제 리그레션 테스트 환경 반영 (Crash 비중 80% 이상)
- RAT/국가별 분포 및 Crash 중심 KPI 자동 시각화
- 기술(선생님) ↔ 부장(검토) ↔ 임원(요약) 모두 대응 가능 구조
""")

# ==============================
# 1. CSV 업로드
# ==============================
st.sidebar.header("데이터 업로드")
uploaded = st.sidebar.file_uploader("CSV 파일 업로드", type=['csv'])
url = st.sidebar.text_input("또는 GitHub RAW CSV URL 입력")

@st.cache_data(show_spinner=False)
def load_data(uploaded_file, url_text):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        return df
    if url_text.strip():
        return pd.read_csv(url_text.strip())
    return None

df = load_data(uploaded, url)

if df is None:
    st.info("CSV 파일을 업로드하거나 URL을 입력해주세요.")
    st.stop()

# ==============================
# 2. 데이터 전처리
# ==============================
required_cols = ["id","date","rat","category","crash_flag","status","patch_secured","region","country_name","issue_type","exec_comment","exec_summary","notes"]
for c in required_cols:
    if c not in df.columns:
        df[c] = None

# 날짜 변환
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df['month'] = df['date'].dt.to_period('M').astype(str)

# bool 변환
df['crash_flag'] = df['crash_flag'].astype(str).str.lower().isin(['true','1','y','yes'])
df['patch_secured'] = df['patch_secured'].astype(str).str.lower().isin(['true','1','y','yes'])

# ==============================
# 3. KPI 계산
# ==============================
total_issues = len(df)
crash_issues = df['crash_flag'].sum()
crash_ratio = round((crash_issues / total_issues * 100) if total_issues else 0, 1)
patch_total = df['patch_secured'].sum()
patch_on_crash = df[df['crash_flag'] == True]['patch_secured'].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("총 이슈", f"{total_issues:,}")
col2.metric("Crash 발생", f"{crash_issues:,}")
col3.metric("Crash 비율", f"{crash_ratio}%")
col4.metric("패치 확보(전체)", f"{patch_total:,}")
col5.metric("패치 확보(Crash)", f"{patch_on_crash:,}")

st.caption("※ Crash 중심 KPI — 해결률·평가 항목 제외")

# ==============================
# 4. 필터링
# ==============================
st.sidebar.header("필터")
min_date, max_date = df['date'].min(), df['date'].max()
date_range = st.sidebar.slider('기간 선택', min_value=min_date.date(), max_value=max_date.date(), value=(min_date.date(), max_date.date()))
region_sel = st.sidebar.selectbox('지역 선택', ['전체'] + list(df['region'].dropna().unique()))
rat_sel = st.sidebar.multiselect('RAT 선택', df['rat'].dropna().unique().tolist(), default=df['rat'].dropna().unique().tolist())

mask = (df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])
if region_sel != '전체':
    mask &= (df['region'] == region_sel)
if rat_sel:
    mask &= df['rat'].isin(rat_sel)

filtered = df.loc[mask]

st.markdown(f"### 📅 필터링된 데이터: {len(filtered)}건")
st.dataframe(filtered, use_container_width=True)

# ==============================
# 5. 분포 시각화
# ==============================
colA, colB = st.columns(2)

with colA:
    st.subheader("RAT별 이슈 분포")
    rat_df = filtered.groupby('rat')['id'].count().reset_index(name='count').sort_values('count', ascending=False)
    st.bar_chart(rat_df.set_index('rat'))

with colB:
    st.subheader("국가별 이슈 분포")
    country_df = filtered.groupby('country_name')['id'].count().reset_index(name='count').sort_values('count', ascending=False)
    st.bar_chart(country_df.set_index('country_name'))

st.subheader("CATEGORY별 이슈 분포")
cat_df = filtered.groupby('category')['id'].count().reset_index(name='count').sort_values('count', ascending=False)
st.bar_chart(cat_df.set_index('category'))

st.subheader("월별 Crash 추이")
monthly_df = filtered.groupby('month').agg(total=('id','count'), crash=('crash_flag','sum')).reset_index()
monthly_df['crash_rate_%'] = (monthly_df['crash']/monthly_df['total']*100).round(1)
st.line_chart(monthly_df.set_index('month')[['crash','total']])

# ==============================
# 6. 다운로드
# ==============================
output = io.StringIO()
filtered.to_csv(output, index=False)
st.download_button(
    label="📥 필터링된 CSV 다운로드",
    data=output.getvalue(),
    file_name=f"filtered_v75_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime='text/csv'
)

st.success("v7.5 Crash 중심 대시보드 생성 완료 — 국가별, RAT별, CATEGORY별 분석 가능.")
