# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
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
    # [object object] 문제 해결: 날짜/시간 타입을 문자열로 명확하게 변환
    if '입고예정일' in df.columns:
        df['입고예정일'] = pd.to_datetime(df['입고예정일']).dt.strftime('%Y-%m-%d')
    return df

source_df = load_data()

# --- UI 섹션 ---
st.header("1. 입고 예정 품목 선택")

# 1. 발주번호 선택 UI
if not source_df.empty:
    po_numbers = sorted(source_df['발주번호'].unique())
    selected_po = st.selectbox(
        "등록할 발주번호를 선택하세요.", 
        options=po_numbers, 
        index=None, 
        placeholder="발주번호 검색..."
    )
else:
    st.warning("조회할 입고 예정 데이터가 없습니다.")
    selected_po = None

# 2. (상단) 참고용 그리드
if selected_po:
    st.info(f"**'{selected_po}'** 발주 건의 품목 리스트입니다. 아래 표에 추가할 항목을 선택하세요.")
    
    source_grid_df = source_df[source_df['발주번호'] == selected_po].copy()
    
    gb_source = GridOptionsBuilder.from_dataframe(source_grid_df)
    gb_source.configure_selection('multiple', use_checkbox=True) # 체크박스로 선택
    gridOptions_source = gb_source.build()

    source_grid_response = AgGrid(
        source_grid_df,
        gridOptions=gridOptions_source,
        height=300,
        theme='streamlit',
        reload_data=True # 선택 초기화를 위해 True
    )

    selected_rows = source_grid_response["selected_rows"]

    if st.button("🔽 선택 항목을 아래 편집 리스트에 추가", disabled=not selected_rows):
        new_items_df = pd.DataFrame(selected_rows)
        # _selectedRowNodeInfo 컬럼은 불필요하므로 제거
        new_items_df = new_items_df.drop(columns=['_selectedRowNodeInfo'], errors='ignore')

        # 편집용 표에 필요한 컬럼 추가
        new_items_df['입고일자'] = date.today().strftime("%Y-%m-%d")
        new_items_df['LOT'] = ''
        new_items_df['유통기한'] = ''
        new_items_df['확정수량'] = new_items_df['예정수량']

        # 기존 편집 리스트와 합치기 (중복 제거)
        current_list = st.session_state.submission_list
        combined_list = pd.concat([current_list, new_items_df]).drop_duplicates(
            subset=['발주번호', '품번', '버전']
        ).reset_index(drop=True)
        
        st.session_state.submission_list = combined_list
        st.rerun()

# 3. (하단) 편집 및 최종 등록용 그리드
st.header("2. 입고 정보 편집 및 최종 등록")
if not st.session_state.submission_list.empty:
    submission_df = st.session_state.submission_list
    
    gb_submission = GridOptionsBuilder.from_dataframe(submission_df)
    
    # 편집 가능한 컬럼 설정
    gb_submission.configure_column("버전", editable=True)
    gb_submission.configure_column("입고일자", editable=True, cellEditor='agDateCellEditor')
    gb_submission.configure_column("LOT", editable=True)
    gb_submission.configure_column("유통기한", editable=True, cellEditor='agDateCellEditor')
    gb_submission.configure_column("확정수량", editable=True, cellEditor='agNumberCellEditor')
    
    # 선택 삭제를 위한 체크박스
    gb_submission.configure_selection('multiple', use_checkbox=True)
    
    gridOptions_submission = gb_submission.build()
    
    submission_grid_response = AgGrid(
        submission_df,
        gridOptions=gridOptions_submission,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        height=350,
        allow_unsafe_jscode=True
    )
    
    # 수정된 데이터 세션 상태에 다시 저장
    st.session_state.submission_list = submission_grid_response['data']
    selected_submission_rows = submission_grid_response["selected_rows"]
    
    # --- 버튼 섹션 ---
    col1, col2, col3 = st.columns([2, 2, 8])
    with col1:
        if st.button("선택 항목 삭제", disabled=not selected_submission_rows):
            selected_indices = [row['_selectedRowNodeInfo']['nodeRowIndex'] for row in selected_submission_rows]
            st.session_state.submission_list = st.session_state.submission_list.drop(selected_indices).reset_index(drop=True)
            st.rerun()
    with col2:
        if st.button("리스트 비우기"):
            st.session_state.submission_list = pd.DataFrame()
            st.rerun()

    # 최종 등록 버튼
    st.divider()
    if st.button("✅ 편집 리스트 전체 등록 및 DB 전송", type="primary"):
        final_df = st.session_state.submission_list
        
        if final_df['LOT'].str.strip().eq('').any():
            st.error("⚠️ LOT 번호는 모든 품목에 대해 필수 입력 항목입니다.")
        else:
            with st.spinner('데이터를 DB에 저장하는 중입니다...'):
                data_to_submit = final_df.to_dict('records')
                success, message = insert_receiving_data(data_to_submit)
                
                if success:
                    st.success(f"✅ 성공! {len(data_to_submit)}개의 데이터를 DB에 전송했습니다.")
                    st.session_state.submission_list = pd.DataFrame() # 성공 후 리스트 비우기
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"DB 전송 실패: {message}")

else:
    st.info("위에서 발주번호를 선택하고 품목을 추가하면 여기에 표시됩니다.")
