# pages/2_📜_입고_예정_이력.py
import streamlit as st
import pandas as pd
from utils.db_functions import get_history_data

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="입고 예정 이력")
st.title("📜 입고 예정 이력 조회")
st.info("전체 입고 예정 품목을 확인하고, 브랜드와 품번으로 필터링할 수 있습니다.")

# --- 데이터 로딩 ---
@st.cache_data
def load_history():
    """DB에서 이력 데이터를 불러옵니다."""
    df = get_history_data()
    if not df.empty and '입고예정일' in df.columns:
        df['입고예정일'] = pd.to_datetime(df['입고예정일']).dt.strftime('%Y-%m-%d')
    return df

history_df = load_history()

if history_df.empty:
    st.warning("조회할 입고 예정 이력이 없습니다.")
else:
    # --- 필터링 UI ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # ▼▼▼ [수정된 부분] ▼▼▼
        # 브랜드 필터 옵션을 지정된 값으로 고정
        brands = ['이퀄베리', '브랜든', '마켓올슨']
        selected_brand = st.multiselect(
            "브랜드 선택",
            options=brands,
            placeholder="필터링할 브랜드를 선택하세요 (여러 개 선택 가능)"
        )
        # ▲▲▲ [수정된 부분] ▲▲▲

    with col2:
        # 품번/품명 검색 필터
        search_term = st.text_input(
            "품번 또는 품명으로 검색",
            placeholder="검색어를 입력하세요..."
        )

    # --- 데이터 필터링 로직 ---
    filtered_df = history_df.copy()
    if selected_brand:
        # 지정된 브랜드 외 다른 브랜드가 DB에 있을 경우를 대비하여 필터링
        filtered_df = filtered_df[filtered_df['브랜드'].isin(selected_brand)]
    else:
        # 아무것도 선택하지 않으면 지정된 3개 브랜드만 보여줌
        filtered_df = filtered_df[filtered_df['브랜드'].isin(brands)]

    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['품번'].str.contains(search_term, case=False, na=False) |
            filtered_df['품명'].str.contains(search_term, case=False, na=False)
        ]

    st.divider()
    
    # --- 결과 표시 ---
    st.markdown(f"**총 {len(filtered_df)}개**의 품목이 조회되었습니다.")
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_order=('입고예정일', '브랜드', '품번', '품명', '버전', '예정수량'),
        column_config={
            "예정수량": st.column_config.NumberColumn(format="%d")
        }
    )
