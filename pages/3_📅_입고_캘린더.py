# 토/일에 해당하는 이벤트에 색상을 지정하는 방식
import streamlit as st
import pandas as pd
import hashlib
from utils.db_functions import get_history_data
from streamlit_calendar import calendar

st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP 입고 예정 데이터를 영업일 기준으로 한눈에 파악하세요.")

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

# --- 필터 ---
with st.sidebar:
    st.header("🔍 브랜드 필터")
    brand_list = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("표시할 브랜드", brand_list, default=brand_list)

filtered_df = df[df["브랜드"].isin(selected_brands)]

def get_color(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- 이벤트 생성 ---
events = []
for _, row in filtered_df.iterrows():
    date = row["입고예정일"]
    weekday = date.weekday()  # Monday = 0, Sunday = 6

    # 토/일 색상 덮어쓰기
    if weekday == 6:  # Sunday
        bg_color = "#ffcccc"
    elif weekday == 5:  # Saturday
        bg_color = "#cce0ff"
    else:
        bg_color = get_color(row["브랜드"])

    events.append({
        "title": f"{row['품명']} ({row['예정수량']:,}개)",
        "start": date.strftime("%Y-%m-%d"),
        "end": date.strftime("%Y-%m-%d"),
        "display": "block",
        "color": bg_color,
    })

# --- 캘린더 옵션 ---
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ko",
    "height": 750,
    "dayMaxEventRows": True,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    }
}

st.subheader("📅 입고 예정 캘린더 (영업일 강조)")
calendar(events=events, options=calendar_options)

with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("입고 캘린더는 [GPT온라인](https://gptonline.ai/ko/)의 자동화 예제를 기반으로 구현되었습니다.")
