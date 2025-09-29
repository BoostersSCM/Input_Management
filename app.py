# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
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
    return df

source_df = load_data()

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
    st.info(f"**'{selected_po}'** 발주 건의 품목 리스트입니다. 아래 표에 추가할 항목을 선택하세요.")
    source_grid_df = source_df[source_df['발주번호'] == selected_po].copy()
    gb_source = GridOptionsBuilder.from_dataframe(source_grid_df)
    gb_source.configure_selection('multiple', use_checkbox=True)
    gridOptions_source = gb_source.build()
    source_grid_response = AgGrid(
        source_grid_df, gridOptions=gridOptions_source, height=300, theme='streamlit', reload_data=True, key='source_grid'
    )
    
    selected_rows = pd.DataFrame(source_grid_response["selected_rows"])

    if st.button("🔽 선택 항목을 아래 편집 리스트에 추가", disabled=selected_rows.empty):
        new_items_df = selected_rows.drop(columns=['_selectedRowNodeInfo'], errors='ignore')
        new_items_df['입고일자'] = date.today().strftime("%Y-%m-%d")
        new_items_df['LOT'] = ''
        new_items_df['유통기한'] = ''
        new_items_df['확정수량'] = new_items_df['예정수량']
        current_list = st.session_state.submission_list
        combined_list = pd.concat([current_list, new_items_df]).reset_index(drop=True)
        st.session_state.submission_list = combined_list
        st.rerun()
else:
    st.info("조회 조건을 모두 선택하면 입고 예정 품목이 여기에 표시됩니다.")

# 3. (하단) 편집 및 최종 등록용 그리드
st.header("3. 입고 정보 편집 및 최종 등록")
if not st.session_state.submission_list.empty:
    submission_df = st.session_state.submission_list
    
    display_columns = [
        '발주번호', '품번', '품명', '예정수량', '버전', 
        '입고일자', 'LOT', '유통기한', '확정수량'
    ]
    submission_df_display = submission_df[[col for col in display_columns if col in submission_df.columns]]

    # ▼▼▼ [수정된 부분] ▼▼▼
    # 생략되었던 JsCode를 다시 채워 넣었습니다.
    date_parser = JsCode("""
        function(params) {
            var dateValue = params.newValue;
            if (typeof dateValue === 'string' && dateValue.length === 8 && !isNaN(dateValue)) {
                return dateValue.slice(0, 4) + '-' + dateValue.slice(4, 6) + '-' + dateValue.slice(6, 8);
            }
            return dateValue;
        }
    """)
    uppercase_parser = JsCode("""
        function(params) {
            if (params.newValue && typeof params.newValue === 'string') {
                return params.newValue.toUpperCase();
            }
            return params.newValue;
        }
    """)
    # ▲▲▲ [수정된 부분] ▲▲▲

    gb_submission = GridOptionsBuilder.from_dataframe(submission_df_display)
    
    # 엑셀처럼 여러 셀을 드래그하고 복사/붙여넣기 할 수 있도록 활성화
    gb_submission.configure_grid_options(enableRangeSelection=True)
    
    gb_submission.configure_column("버전", editable=True, valueParser=uppercase_parser)
    gb_submission.configure_column("입고일자", editable=True, valueParser=date_parser)
    gb_submission.configure_column("유통기한", editable=True, valueParser=date_parser)
    gb_submission.configure_column("LOT", editable=True, valueParser=uppercase_parser)
    gb_submission.configure_column("확정수량", editable=True, type=["numericColumn"], precision=0)
    
    gb_submission.configure_selection('multiple', use_checkbox=True)
    gridOptions_submission = gb_submission.build()
    
    submission_grid_response = AgGrid(
        submission_df_display,
        gridOptions=gridOptions_submission,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        height=350,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True, # 클립보드 기능은 엔터프라이즈 모듈 필요
        debounce_ms=500,
        key='submission_grid'
    )
    
    st.session_state.submission_list = pd.DataFrame(submission_grid_response['data'])
    selected_submission_rows = pd.DataFrame(submission_grid_response["selected_rows"])
    
    col1, col2, col3 = st.columns([2, 2, 8])
    with col1:
        if st.button("선택 항목 삭제", disabled=selected_submission_rows.empty):
            indices_to_drop = selected_submission_rows.index
            st.session_state.submission_list = st.session_state.submission_list.drop(indices_to_drop).reset_index(drop=True)
            st.rerun()
    with col2:
        if st.button("리스트 비우기"):
            st.session_state.submission_list = pd.DataFrame()
            st.rerun()
            
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
                    st.session_state.submission_list = pd.DataFrame()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"DB 전송 실패: {message}")
else:
    st.info("위에서 품목을 추가하면 여기에 표시됩니다.")
