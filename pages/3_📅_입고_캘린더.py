import streamlit as st
import pandas as pd
import hashlib
import json
from streamlit_calendar import calendar
from utils.db_functions import get_history_data

# --- 페이지 설정 ---
st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP에서 조회한 입고 예정 데이터를 브랜드별로 시각화하고 검색할 수 있습니다.")

# --- 버전/환경 점검 (디버깅용) ---
try:
    import importlib.metadata as _ilm
    _sc_ver = _ilm.version("streamlit-calendar")
    _st_ver = _ilm.version("streamlit")
except Exception:
    _sc_ver = "unknown"
    _st_ver = "unknown"

with st.expander("🛠 디버그 정보"):
    st.write({"streamlit": _st_ver, "streamlit-calendar": _sc_ver})

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
    st.markdown("---")
    SAFE_MODE = st.toggle("🧯 안전모드(콜백 비활성화)", value=True, help="컴포넌트 오류 발생 시 켜두면 달력만 먼저 렌더링합니다.")

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

    # FullCalendar는 allDay 이벤트에서 같은 start/end면 하루만 표시됩니다.
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

# --- 공통 옵션 (콜백 제외) ---
base_options = {
    "initialView": initial_view,
    "locale": "ko",
    "height": 850,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listWeek"
    },
    "dayMaxEventRows": True,
    # 안전을 위해 초기에는 클릭/마운트 콜백을 비워둡니다.
}

# --- 콜백 스크립트 (최신 래퍼에서 허용되는 형태) ---
event_click_js = """
function(info) {
    const d = info.event.extendedProps || {};
    const lines = [
        "📌 " + info.event.title,
        "📦 브랜드: " + (d.브랜드 ?? ""),
        "🔢 품번: " + (d.품번 ?? ""),
        "📄 발주번호: " + (d.발주번호 ?? ""),
        "🌀 버전: " + (d.버전 ?? "")
    ];
    window.alert(lines.join("\\n"));
}
"""

event_did_mount_js = """
function(info) {
    try {
        info.el.style.whiteSpace = 'normal';
        info.el.style.wordBreak = 'break-word';
        info.el.style.fontSize = '0.85rem';
        info.el.style.lineHeight = '1.3';
        info.el.style.padding = '2px 4px';
        info.el.style.textOverflow = 'ellipsis';
    } catch (e) {}
}
"""

# --- 렌더링 시도: 1) 안전모드(콜백 없음) -> 2) 콜백 포함 ---
st.subheader(f"📅 {'월간 보기' if view_mode == '월간 보기' else '리스트 보기'}")

def render_calendar(options_dict, note: str):
    with st.container(border=True):
        st.caption(note)
        calendar(events=events, options=options_dict)

error_msg = None

try:
    if SAFE_MODE:
        render_calendar(base_options, "안전모드: 콜백 비활성화")
    else:
        # 콜백 포함 시도 (>=0.0.4 계열: 문자열 함수 전달)
        options_with_cb = dict(base_options)
        options_with_cb["eventClick"] = event_click_js
        options_with_cb["eventDidMount"] = event_did_mount_js
        render_calendar(options_with_cb, "콜백 활성화")
except Exception as e:
    error_msg = str(e)

# --- 예외 발생 시 최종 폴백 (완전 미니멀) ---
if error_msg:
    st.error(f"컴포넌트 렌더링 중 오류가 발생했습니다: {error_msg}")
    st.info("콜백을 제거한 최소 옵션으로 다시 시도합니다.")
    try:
        render_calendar(base_options, "최소 옵션(콜백 완전 제거) 폴백")
    except Exception as e2:
        st.exception(e2)
        st.stop()

# --- 데이터 테이블 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 입고 예정 캘린더는 FullCalendar 래퍼(streamlit-calendar)를 사용합니다.")
