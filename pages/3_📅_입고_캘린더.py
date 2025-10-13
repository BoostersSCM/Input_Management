import streamlit as st
import pandas as pd
import hashlib
from streamlit_calendar import calendar
from utils.db_functions import get_history_data

# --- 페이지 설정 ---
st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP에서 조회한 입고 예정 데이터를 브랜드별로 시각화하고 검색할 수 있습니다.")

# --- 데이터 불러오기 ---
@st.cache_data
def load_data():
    """ERP DB에서 입고예정 데이터를 불러옵니다."""
    df = get_history_data()
    if df.empty:
        return df
    df["입고예정일"] = pd.to_datetime(df["입고예정일"], errors="coerce")
    df["예정수량"] = pd.to_numeric(df["예정수량"], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["입고예정일"])
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

# --- 보기 모드 선택 ---
view_mode = st.radio("📅 보기 모드 선택", ["월간 보기", "리스트 보기"], horizontal=True)
initial_view = "dayGridMonth" if view_mode == "월간 보기" else "listWeek"

# --- 데이터 필터링 ---
filtered_df = df[df["브랜드"].isin(selected_brands)]
if search_term:
    mask = (
        filtered_df["브랜드"].str.contains(search_term, case=False, na=False) |
        filtered_df["품명"].str.contains(search_term, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

# --- 브랜드별 색상 지정 ---
def get_color(brand: str) -> str:
    if pd.isna(brand):
        brand = "UNKNOWN"
    hex_code = hashlib.md5(str(brand).encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- 캘린더 이벤트 데이터 생성 ---
events = []
for _, row in filtered_df.iterrows():
    version = row.get("버전", "") or ""
    quantity = f"{row['예정수량']:,}개"
    title = f"{row['품명']} ({version}) - {quantity}" if version else f"{row['품명']} - {quantity}"

    start_str = row["입고예정일"].strftime("%Y-%m-%d")
    events.append({
        "title": title,
        "start": start_str,
        "end": start_str,
        "color": get_color(row["브랜드"]),
        "extendedProps": {
            "브랜드": row.get("브랜드", ""),
            "품번": row.get("품번", ""),
            "버전": version,
            "발주번호": row.get("발주번호", "")
        }
    })

# --- 캘린더 옵션 설정 ---
calendar_options = {
    "initialView": initial_view,
    "locale": "ko",
    "height": 850,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
    "dayMaxEventRows": True,
}

# --- 캘린더 렌더링 ---
st.subheader(f"📅 {'월간 보기' if view_mode == '월간 보기' else '리스트 보기'}")
selected = calendar(events=events, options=calendar_options)

# --- 클릭된 이벤트 상세 표시 ---
if selected and isinstance(selected, dict):
    info = selected.get("event", {})
    d = info.get("extendedProps", {})
    with st.container():
        st.markdown("### 🔍 선택한 일정 상세")
        st.info(
            f"**{info.get('title', '(제목없음)')}**\n\n"
            f"📦 **브랜드:** {d.get('브랜드', '')}\n\n"
            f"🔢 **품번:** {d.get('품번', '')}\n\n"
            f"📄 **발주번호:** {d.get('발주번호', '')}\n\n"
            f"🌀 **버전:** {d.get('버전', '')}"
        )

# --- 데이터 테이블 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 입고 예정 캘린더는 Streamlit Calendar 컴포넌트를 기반으로 구현되었습니다.")
