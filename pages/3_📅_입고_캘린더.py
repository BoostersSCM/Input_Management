import streamlit as st
import pandas as pd
import hashlib
from streamlit_calendar import calendar
from utils.db_functions import get_history_data

# --- 페이지 설정 ---
st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("브랜드별 입고 예정 품목을 달력과 리스트로 확인할 수 있습니다.")

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

# --- 사이드바 필터 ---
with st.sidebar:
    st.header("🔍 필터")
    brands = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("📦 브랜드 선택", brands, default=brands)
    search_term = st.text_input("🔎 품명 또는 브랜드 검색", "")

# --- 보기 모드 전환 ---
view_mode = st.radio("📅 보기 모드", ["월간 보기", "리스트 보기"], horizontal=True)
initial_view = "dayGridMonth" if view_mode == "월간 보기" else "listWeek"

# --- 데이터 필터링 ---
filtered_df = df[df["브랜드"].isin(selected_brands)]
if search_term:
    filtered_df = filtered_df[
        filtered_df["브랜드"].str.contains(search_term, case=False, na=False) |
        filtered_df["품명"].str.contains(search_term, case=False, na=False)
    ]

# --- 브랜드별 색상 지정 함수 ---
def get_color(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- 이벤트 데이터 생성 ---
events = []
for _, row in filtered_df.iterrows():
    version = row.get("버전", "")
    quantity = f"{row['예정수량']:,}개"
    title = f"{row['품명']} ({version}) - {quantity}" if version else f"{row['품명']} - {quantity}"

    events.append({
        "title": title,
        "start": row["입고예정일"].strftime("%Y-%m-%d"),
        "end": row["입고예정일"].strftime("%Y-%m-%d"),
        "color": get_color(row["브랜드"]),
        "extendedProps": {
            "브랜드": row["브랜드"],
            "품번": row["품번"],
            "버전": version,
            "발주번호": row.get("발주번호", "")
        }
    })

# --- 캘린더 옵션 설정 ---
calendar_options = {
    "initialView": initial_view,
    "locale": "ko",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
    "eventClick": {
        "callback": "function(info) { " +
                    "var d = info.event.extendedProps;" +
                    "alert('📌 ' + info.event.title + '\\n' +" +
                          "'📦 브랜드: ' + d.브랜드 + '\\n' +" +
                          "'🔢 품번: ' + d.품번 + '\\n' +" +
                          "'📄 발주번호: ' + d.발주번호 + '\\n' +" +
                          "'🌀 버전: ' + d.버전);" +
                  "}"
    },
    "dayMaxEventRows": True
}

# --- 캘린더 출력 ---
st.subheader("📅 입고 예정 캘린더")
calendar(events=events, options=calendar_options)

# --- 데이터 테이블 ---
with st.expander("📋 원본 데이터 보기"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 캘린더는 [GPT온라인](https://gptonline.ai/ko/)의 자동화 예제를 기반으로 구성되었습니다.")
