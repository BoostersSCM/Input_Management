# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from utils.db_functions import get_source_data, insert_receiving_data
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="입고 등록 관리 시스템")
st.title("📦 입고 등록 관리 시스템")

# --- 데이터 로딩 ---
@st.cache_data
def load_data():
    """ERP DB에서 입고 예정 데이터를 불러옵니다."""
    return get_source_data()

source_df = load_data()

# --- UI 섹션 ---
st.header("📝 입고 예정 리스트")

# 1. 발주번호 선택 UI
if not source_df.empty:
    po_numbers = sorted(source_df['발주번호'].unique())
    selected_po = st.selectbox(
        "**1. 등록할 발주번호를 선택하세요.**", 
        options=po_numbers, 
        index=None, 
        placeholder="발주번호 검색..."
    )
else:
    st.warning("조회할 입고 예정 데이터가 없습니다.")
    selected_po = None

# 2. 선택된 발주 데이터로 그리드 표시 및 입력
if selected_po:
    st.markdown(f"**2. 선택된 발주번호 `{selected_po}`의 품목 리스트입니다. 입고 정보를 직접 입력하세요.**")
    
    # 그리드에 표시할 데이터 준비
    grid_df = source_df[source_df['발주번호'] == selected_po].copy()
    
    # 사용자가 입력할 컬럼 추가 (기본값 설정)
    grid_df['입고일자'] = date.today().strftime("%Y-%m-%d")
    grid_df['LOT'] = ''
    grid_df['유통기한'] = ''
    grid_df['확정수량'] = grid_df['예정수량']
    
    # 3. AG Grid 설정
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    
    # 입력 가능한 컬럼 설정
    gb.configure_column("입고일자", editable=True, cellEditor='agDateCellEditor')
    gb.configure_column("LOT", editable=True)
    gb.configure_column("유통기한", editable=True, cellEditor='agDateCellEditor')
    gb.configure_column("확정수량", editable=True, cellEditor='agNumberCellEditor')
    
    # 수정 불필요한 컬럼은 읽기 전용으로 설정
    for col in ['입고예정일', '발주번호', '품번', '품명', '버전', '예정수량']:
        gb.configure_column(col, editable=False)
        
    gridOptions = gb.build()

    # AG Grid 표시
    grid_response = AgGrid(
        grid_df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        height=400,
        allow_unsafe_jscode=True, # Date picker 사용을 위해 필요
        enable_enterprise_modules=False
    )
    
    # 4. 최종 DB 전송 버튼 및 로직
    if st.button(f"'{selected_po}' 전체 등록 및 DB 전송", type="primary"):
        edited_df = grid_response['data']
        
        # 필수 입력값(LOT) 확인
        if edited_df['LOT'].str.strip().eq('').any():
            st.error("⚠️ LOT 번호는 모든 품목에 대해 필수 입력 항목입니다.")
        else:
            # 중복 검사 로직 (발주번호+품번+LOT+버전)
            key_cols = ['발주번호', '품번', 'LOT', '버전']
            is_duplicate = edited_df.duplicated(subset=key_cols).any()
            
            if is_duplicate:
                st.error("⚠️ 그리드 내에 [발주번호+품번+LOT+버전]이 동일한 중복 데이터가 존재합니다.")
            else:
                with st.spinner('데이터를 DB에 저장하는 중입니다...'):
                    data_to_submit = edited_df.to_dict('records')
                    success, message = insert_receiving_data(data_to_submit)
                    
                    if success:
