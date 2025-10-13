import streamlit as st
import pandas as pd
import hashlib
import streamlit.components.v1 as components
import json
from utils.db_functions import get_history_data

# --- 페이지 설정 ---
st.set_page_config(page_title="📅 입고 예정 캘린더", layout="wide")
st.title("📦 입고 예정 품목 캘린더")
st.caption("ERP에서 조회한 입고 예정 데이터를 다양한 시각으로 확인하세요.")

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
    st.warning("입고 예정 데이터가 없습니다.")
    st.stop()

# --- 사이드바 필터 ---
with st.sidebar:
    st.header("🔍 필터")
    brands = sorted(df["브랜드"].dropna().unique())
    selected_brands = st.multiselect("📦 브랜드 선택", brands, default=brands)

    search_term = st.text_input("🔍 품명 또는 브랜드 검색", "")

# --- 보기 모드 선택 (월간 / 리스트 뷰) ---
view_mode = st.radio("📅 보기 모드 선택", ["월간 보기", "리스트 보기"], horizontal=True)

# --- 데이터 필터링 ---
filtered_df = df[df["브랜드"].isin(selected_brands)]
if search_term:
    filtered_df = filtered_df[
        filtered_df["브랜드"].str.contains(search_term, case=False, na=False) |
        filtered_df["품명"].str.contains(search_term, case=False, na=False)
    ]

# --- 브랜드별 색상 지정 ---
def get_color(brand):
    hex_code = hashlib.md5(brand.encode()).hexdigest()
    return f"#{hex_code[:6]}"

# --- FullCalendar 이벤트 리스트 생성 ---
events = []
for _, row in filtered_df.iterrows():
    version = row.get("버전", "")
    quantity = f"{row['예정수량']:,}개"
    title = f"{row['품명']} ({version}) - {quantity}" if version else f"{row['품명']} - {quantity}"

    events.append({
        "title": title,
        "start": row["입고예정일"].strftime("%Y-%m-%d"),
        "color": get_color(row["브랜드"]),
        "extendedProps": {
            "브랜드": row["브랜드"],
            "품번": row["품번"],
            "버전": version,
            "발주번호": row.get("발주번호", "")
        }
    })

# --- FullCalendar HTML 생성 ---
initial_view = "dayGridMonth" if view_mode == "월간 보기" else "listMonth"

calendar_html = f"""
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/main.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/main.min.js"></script>
<div id="calendar"></div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {{
        initialView: '{initial_view}',
        locale: 'ko',
        height: 750,
        headerToolbar: {{
            left: 'prev,next today',
            center: 'title',
            right: ''
        }},
        nowIndicator: true,
        eventDisplay: 'block',
        events: {json.dumps(events)},
        eventClick: function(info) {{
            var d = info.event.extendedProps;
            alert(`📌 ${info.event.title}\\n📦 브랜드: ${d.브랜드}\\n🔢 품번: ${d.품번}\\n📄 발주번호: ${d.발주번호}\\n🌀 버전: ${d.버전}`);
        }},
        dayCellDidMount: function(info) {{
            const day = info.date.getDay();
            if (day === 0) {{
                info.el.style.backgroundColor = '#ffe6e6';  // 일요일
            }} else if (day === 6) {{
                info.el.style.backgroundColor = '#e6f0ff';  // 토요일
            }}
        }},
        eventDidMount: function(info) {{
            info.el.style.whiteSpace = 'normal';
            info.el.style.wordBreak = 'break-word';
            info.el.style.fontSize = '13px';
        }}
    }});
    calendar.render();
}});
</script>
"""

# --- 캘린더 출력 ---
st.subheader(f"📅 {'월간 캘린더' if view_mode == '월간 보기' else '입고 리스트'}")
components.html(calendar_html, height=800, scrolling=True)

# --- 원본 데이터 테이블 ---
with st.expander("📋 원본 데이터 보기 (필터 적용됨)"):
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("이 자동화 캘린더는 [GPT온라인](https://gptonline.ai/ko/)의 예제를 기반으로 개발되었습니다.")
