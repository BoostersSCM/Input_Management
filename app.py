# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from utils.db_functions import get_source_data, insert_receiving_data
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="입고 등록 관리 시스템")
st.title("📦 입고 등록 관리 시스템")

# --- 세션 상태 초기화 ---
if 'submission_list' not in st.session_state:
    st.session_state.submission_list = pd.DataFrame()

# --- 데이터 로딩 ---
@st.cache_data
def load_data():
    """ERP DB에서 입고 예정 데이터를 불러옵니다."""
    df = get_source_data()
    if '입고예정일' in df.columns:
        df['입고예정일'] = pd.to_datetime(df['입고예정일']).dt.strftime('%Y-%m-%d')
    if '예정수량' in df.columns:
        df['예정수량'] = pd.to_numeric(df['예정수량'], errors='coerce').fillna(0).astype(int)
    return df

source_df = load_data()

# --- 공통 함수 ---
def add_to_submission_list(items_df):
    """선택된 항목을 아래 편집 리스트에 추가하는 함수"""
    if not items_df.empty:
        new_items = items_df.copy()
        new_items['삭제'] = False
        new_items['입고일자'] = date.today().strftime("%Y-%m-%d")
        new_items['LOT'] = ''
        new_items['유통기한'] = ''
        new_items['확정수량'] = 0
        
        current_list = st.session_state.submission_list
        combined_list = pd.concat([current_list, new_items]).reset_index(drop=True)
        st.session_state.submission_list = combined_list
        st.rerun()

# --- UI 섹션 ---
st.header("1. 조회 조건 선택")

# 1. 연쇄 드롭다운 선택 UI
selected_po = None
if not source_df.empty:
    brands = sorted(source_df['브랜드'].dropna().unique())
    selected_brand = st.selectbox(
        "**브랜드**를 선택하세요.", options=brands, index=None, placeholder="브랜드 검색..."
    )
    if selected_brand:
        brand_df = source_df[source_df['브랜드'] == selected_brand]
        part_numbers = sorted(brand_df['품번'].unique())
        selected_part_number = st.selectbox(
            "**품번**을 선택하세요.", options=part_numbers, index=None, placeholder="품번 검색..."
        )
        if selected_part_number:
            part_number_df = brand_df[brand_df['품번'] == selected_part_number]
            po_numbers = sorted(part_number_df['발주번호'].unique())
            selected_po = st.selectbox(
                "**발주번호**를 선택하세요.", options=po_numbers, index=None, placeholder="발주번호 검색..."
            )
else:
    st.warning("조회할 입고 예정 데이터가 없습니다.")

# 2. (상단) 참고용 그리드
st.header("2. 입고 예정 품목 선택")
if selected_po:
    st.info(f"**'{selected_po}'** 발주 건의 품목 리스트입니다. 체크박스로 추가할 항목을 선택하세요.")
    source_grid_df = source_df[source_df['발주번호'] == selected_po].copy()
    
    gb_source = GridOptionsBuilder.from_dataframe(source_grid_df)
    gb_source.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
    gridOptions_source = gb_source.build()
    
    source_grid_response = AgGrid(
        source_grid_df, 
        gridOptions=gridOptions_source, 
        height=300, 
        theme='streamlit',
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        key='source_grid'
    )

    selected_rows = pd.DataFrame(source_grid_response["selected_rows"])
    if st.button("🔽 체크된 항목 모두 아래에 추가", disabled=selected_rows.empty):
        add_to_submission_list(selected_rows.drop(columns=['_selectedRowNodeInfo'], errors='ignore'))

else:
    st.info("조회 조건을 모두 선택하면 입고 예정 품목이 여기에 표시됩니다.")

# 3. (하단) 편집 및 최종 등록용 그리드 (st.data_editor)
st.header("3. 입고 정보 편집 및 최종 등록")
if not st.session_state.submission_list.empty:
    
    st.info("아래 표의 셀을 더블클릭하여 입고 정보를 직접 수정하세요. (엑셀처럼 복사/붙여넣기 가능)")
    
    # 표시할 컬럼 순서 및 읽기 전용 설정
    column_order = [
        '삭제', '발주번호', '품번', '품명', '버전', 
        '입고일자', 'LOT', '유통기한', '확정수량'
    ]
    
    # st.data_editor에 맞게 컬럼 설정
    column_config = {
        "발주번호": st.column_config.TextColumn(disabled=True),
        "품번": st.column_config.TextColumn(disabled=True),
        "품명": st.column_config.TextColumn(disabled=True),
        "확정수량": st.column_config.NumberColumn(min_value=0, format="%d", required=True),
        # '예정수량'은 DB 전송에 필요하지만 화면에는 보이지 않도록 숨김
        "예정수량": None,
    }

    # data_editor를 호출하고, 그 결과를 즉시 edited_df에 저장
    edited_df = st.data_editor(
        st.session_state.submission_list,
        column_order=column_order,
        column_config=column_config,
        hide_index=True,
        num_rows="dynamic",
        key='submission_editor'
    )

    # --- 버튼 및 상태 업데이트 로직 ---
    col1, col2 = st.columns(2)
    delete_button = col1.button("🗑️ 선택 항목 삭제")
    clear_button = col2.button("✨ 리스트 비우기")
    
    # ▼▼▼ [수정된 핵심 로직] ▼▼▼
    # 버튼 액션에 따라 상태 업데이트를 명확하게 분리
    if delete_button:
        # '삭제'가 체크되지 않은 행만 남김
        rows_to_keep = edited_df[edited_df['삭제'] == False]
        st.session_state.submission_list = rows_to_keep
        st.rerun()
    elif clear_button:
        st.session_state.submission_list = pd.DataFrame()
        st.rerun()
    else:
        # 다른 버튼 액션이 없을 때만 data_editor의 변경사항을 session_state에 저장
        # 이것이 값이 초기화되는 것을 막는 핵심 부분입니다.
        st.session_state.submission_list = edited_df
    # ▲▲▲ [수정된 핵심 로직] ▲▲▲
            
    st.divider()
    if st.button("✅ 편집 리스트 전체 등록 및 DB 전송", type="primary"):
        # 전송 전에는 항상 최신 session_state 사용
        final_df = st.session_state.submission_list.drop(columns=['삭제'], errors='ignore')
        
        if final_df['LOT'].str.strip().eq('').any():
            st.error("⚠️ LOT 번호는 모든 품목에 대해 필수 입력 항목입니다.")
        else:
            with st.spinner('데이터를 DB에 저장하는 중입니다...'):
                data_to_submit = final_df.to_dict('records')
                success, message = insert_receiving_data(data_to_submit)
                
                if success:
                    st.success(f"✅ 성공! {len(data_to_submit)}개의 데이터를 DB에 전송했습니다.")
                    st.session_state.submission_list = pd.DataFrame()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"DB 전송 실패: {message}")
else:
    st.info("위에서 품목을 추가하면 여기에 표시됩니다.")
