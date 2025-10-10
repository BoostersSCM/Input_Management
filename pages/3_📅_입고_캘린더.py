import streamlit as st
import pandas as pd
import hashlib
from utils.db_functions import get_history_data
from streamlit_calendar import calendar

st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP에서 불러온 입고 예정 데이터를 브랜드별로 시각화합니다.")

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

# --- 브랜드 필터 (사이드바) ---
with st.sidebar:
    st.header("🔍 브랜드 필터")
    brand_list = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("표시할 브랜드", brand_list, default=brand_list)
    st.caption("🎨 브랜드별 색상은 자동 생성됩니다.")

# --- 브랜드 필터 적용 ---
filtered_df = df[df["브랜드"].isin(selected_brands)]

# --- 브랜드별 색상 생성 ---
def get_color(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- 캘린더 이벤트 생성 ---
events = []
for _, row in filtered_df.iterrows():
    brand = row["브랜드"]
    product = row["품명"]
    quantity = row["예정수량"]
    date = row["입고예정일"].strftime("%Y-%m-%d")

    events.append({
        "title": f"{product} ({quantity:,}개)",
        "start": date,
        "end": date,
        "display": "block",
        "color": get_color(brand),
        "extendedProps": {
            "브랜드": brand,
            "품번": row["품번"],
        }
    })

# --- 캘린더 옵션 구성 ---
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ko",
    "height": 750,
    "eventMaxStack": 3,  # 하루에 최대 3개까지만 보이고 나머지는 '더보기'
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
    "dayMaxEventRows": True,
    "eventDisplay": "block"
}

# --- 캘린더 출력 ---
st.subheader("📅 월간 입고 예정")
calendar(events=events, options=calendar_options)

# --- 데이터 테이블 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 시스템은 [GPT온라인](https://gptonline.ai/ko/)의 자동화 예제를 기반으로 제작되었습니다.")
