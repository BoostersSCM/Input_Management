# 3_📅_입고_캘린더.py

import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from utils.db_functions import get_history_data

st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.markdown("ERP DB에서 불러온 입고 예정 데이터를 **월간 캘린더**로 시각화합니다.")

# --- 데이터 불러오기 ---
@st.cache_data
def load_calendar_data():
    df = get_history_data()
    if df.empty:
        return df
    df["입고예정일"] = pd.to_datetime(df["입고예정일"])
    return df

df = load_calendar_data()

if df.empty:
    st.warning("표시할 입고 예정 데이터가 없습니다.")
    st.stop()

# --- 캘린더 이벤트 생성 ---
events = []
for _, row in df.iterrows():
    title = f"{row['품명']} ({row['예정수량']:,})"
    events.append({
        "title": title,
        "start": row["입고예정일"].strftime("%Y-%m-%d"),
        "end": row["입고예정일"].strftime("%Y-%m-%d"),
    })

# --- 캘린더 옵션 설정 ---
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ko",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listWeek"
    },
    "height": 650,
}

# --- 캘린더 출력 ---
calendar(events=events, options=calendar_options)

# --- 원본 테이블 보기 ---
with st.expander("📋 원본 입고 예정 데이터 보기"):
    st.dataframe(df)

st.markdown("---")
st.caption("자동화된 일정 시각화 시스템은 [GPT온라인](https://gptonline.ai/ko/)을 참고하여 구축되었습니다.")
