import streamlit as st
import pandas as pd
import hashlib
from utils.db_functions import get_history_data
from streamlit_calendar import calendar

st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP 입고 예정 데이터를 영업일 기준으로 한눈에 파악하세요.")

# --- 데이터 불러오기 ---
@st.cache_data
def load_data():
    df = get_history_data()
    if df.empty:
        return df
    df["입고예정일"] = pd.to_datetime(df["입고예정일"])
    df["예정수량"] = pd.to_numeric(df["예정수량"], errors="coerce").fillna(0).astype(int)
    return df

df = load_data()
if df.empty:
    st.warning("표시할 입고 예정 데이터가 없습니다.")
    st.stop()

# --- 브랜드 필터 ---
with st.sidebar:
    st.header("🔍 브랜드 필터")
    brand_list = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("표시할 브랜드", brand_list, default=brand_list)
    st.caption("🎨 브랜드별 색상은 자동 지정됩니다.")

filtered_df = df[df["브랜드"].isin(selected_brands)]

# --- 브랜드별 색상 지정 함수 ---
def get_color(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- 이벤트 데이터 생성 ---
events = []
for _, row in filtered_df.iterrows():
    events.append({
        "title": f"{row['품명']} ({row['예정수량']:,}개)",
        "start": row["입고예정일"].strftime("%Y-%m-%d"),
        "end": row["입고예정일"].strftime("%Y-%m-%d"),
        "display": "block",
        "color": get_color(row["브랜드"]),
        "extendedProps": {
            "브랜드": row["브랜드"],
            "품번": row["품번"],
        }
    })

# --- 캘린더 옵션 설정 (토/일 색상 포함) ---
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ko",
    "height": 750,
    "dayMaxEventRows": True,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
    "dayCellDidMount": """
        function(info) {
            const date = new Date(info.date);
            const day = date.getDay();
            if (day === 0) { // Sunday
                info.el.style.backgroundColor = '#ffe6e6';  // 연한 빨강
            } else if (day === 6) { // Saturday
                info.el.style.backgroundColor = '#e6f0ff';  // 연한 파랑
            }
        }
    """
}

# --- 캘린더 출력 ---
st.subheader("📅 영업일 기준 입고 캘린더")
calendar(events=events, options=calendar_options)

# --- 원본 데이터 보기 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("입고 자동화 시스템은 [GPT온라인](https://gptonline.ai/ko/) 예제를 기반으로 개발되었습니다.")
