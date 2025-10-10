import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from utils.db_functions import get_history_data
import hashlib

st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")

st.title("📦 입고 예정 품목 캘린더")
st.caption("입고 예정 데이터를 브랜드별로 확인할 수 있는 월간 캘린더입니다.")

# --- 데이터 로딩 ---
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

# --- 사이드바 필터 UI ---
with st.sidebar:
    st.header("🔍 필터")
    all_brands = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("브랜드 선택", all_brands, default=all_brands)

    st.markdown("---")
    st.caption("💡 브랜드별로 색상이 다르게 표시됩니다.")

# --- 필터 적용 ---
filtered_df = df[df["브랜드"].isin(selected_brands)]

# --- 브랜드별 색상 생성 함수 ---
def get_color_for_brand(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    color = f"#{hex_code[:6]}"
    return color

# --- 캘린더 이벤트 생성 ---
events = []
for _, row in filtered_df.iterrows():
    title = f"{row['품명']} ({row['예정수량']:,})"
    event = {
        "title": title,
        "start": row["입고예정일"].strftime("%Y-%m-%d"),
        "end": row["입고예정일"].strftime("%Y-%m-%d"),
        "display": "block",
        "color": get_color_for_brand(row["브랜드"]),
    }
    events.append(event)

# --- 캘린더 옵션 ---
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ko",
    "height": 700,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
}

# --- 캘린더 출력 ---
st.subheader("📅 월간 입고 예정 캘린더")
calendar(events=events, options=calendar_options)

# --- 원본 테이블 보기 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 앱은 [GPT온라인](https://gptonline.ai/ko/)에서 제공하는 자동화 예제를 기반으로 제작되었습니다.")
