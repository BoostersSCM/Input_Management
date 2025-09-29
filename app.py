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
if 'data_to_submit' not in st.session_state:
    st.session_state.data_to_submit = []

# --- 데이터 로딩 ---
@st.cache_data
def load_data():
    """ERP DB에서 소스 데이터를 불러옵니다."""
    # 'OrderQty' 컬럼이 있다는 가정하에 쿼리 수정이 필요할 수 있습니다.
    # 우선 임의의 수량을 '입고예정수량'으로 추가합니다. 실제 컬럼명으로 변경해주세요.
    source_df = get_source_data()
    if '입고예정수량' not in source_df.columns:
        # 실제 발주 수량 컬럼이 있다면 그 컬럼을 사용해야 합니다.
        # 예: source_df.rename(columns={'OrderQty': '입고예정수량'}, inplace=True)
        # 지금은 임시로 값을 채웁니다.
        source_df['입고예정수량'] = 100 # 임시 데이터
    return source_df

source_df = load_data()

# --- UI 섹션 ---
st.header("📝 신규 입고 등록")

# 1. 필터 섹션
if not source_df.empty:
    brands = sorted(source_df['브랜드'].unique())
    selected_brand = st.selectbox(
        "**1. 브랜드 선택**", options=brands, index=None, placeholder="먼저 브랜드를 선택하세요."
    )

    # 브랜드 선택 시 하위 필터 표시
    if selected_brand:
        brand_df = source_df[source_df['브랜드'] == selected_brand]
        order_numbers = sorted(brand_df['발주번호'].unique())
        selected_order = st.selectbox(
            "**2. 발주번호 선택**", options=order_numbers, index=None, placeholder="다음으로 발주번호를 선택하세요."
        )

        # 발주번호 선택 시 하위 필터 표시 (연쇄 드롭다운)
        if selected_order:
            order_df = brand_df[brand_df['발주번호'] == selected_order]
            product_dict = order_df.set_index('품번')['품명'].to_dict()
            part_numbers = list(product_dict.keys())
            
            selected_part_number = st.selectbox(
                "**3. 품번 선택**", options=part_numbers, key="part_number", index=None, placeholder="마지막으로 품번을 선택하세요."
            )
            
            # 품번 선택 시, 예정 수량 표시
            if selected_part_number:
                try:
                    # 실제 발주수량 컬럼명으로 변경해야 합니다.
                    scheduled_qty = order_df.loc[order_df['품번'] == selected_part_number, '입고예정수량'].iloc[0]
                    st.info(f"💡 **입고 예정 수량:** {scheduled_qty} 개")
                except IndexError:
                    st.warning("해당 품번의 예정 수량 정보를 찾을 수 없습니다.")

# 2. 입력 폼 섹션
# 모든 필터가 선택되었을 때만 입력 폼을 활성화합니다.
if selected_brand and selected_order and selected_part_number:
    with st.form(key="receiving_form", clear_on_submit=True):
        st.write(f"**4. 입고 정보 입력**")
        
        # 선택된 값들을 hidden 필드처럼 form 내부에 두어 제출 시 함께 처리
        st.text(f"**선택된 발주번호:** {selected_order} | **선택된 품번:** {selected_part_number}")
        
        product_name = product_dict.get(st.session_state.part_number, "")
        
        cols1 = st.columns(4)
        with cols1[0]:
            receiving_date = st.date_input("입고 일자", value=date.today())
        with cols1[1]:
            version = st.text_input("버전")
        with cols1[2]:
            lot_number = st.text_input("LOT")
        with cols1[3]:
            final_qty = st.number_input("확정 수량", min_value=0, step=1, key="final_qty")
        
        cols2 = st.columns(1)
        with cols2[0]:
            expiry_date = st.date_input("유통기한")

        add_button = st.form_submit_button(label="리스트에 추가")

    if add_button:
        # 중복 추가 방지 로직
        is_duplicate = any(
            d['발주번호'] == selected_order and d['품번'] == selected_part_number and d['LOT'] == lot_number
            for d in st.session_state.data_to_submit
        )
        if is_duplicate:
            st.warning("이미 리스트에 동일한 [발주번호+품번+LOT] 조합이 존재합니다.")
        elif not lot_number:
            st.warning("LOT 번호는 필수 입력 항목입니다.")
        else:
            new_data = {
                "입고일자": receiving_date.strftime("%Y-%m-%d"), "발주번호": selected_order,
                "품번": selected_part_number, "품명": product_name, "버전": version, "LOT": lot_number,
                "유통기한": expiry_date.strftime("%Y-%m-%d"), "확정수량": final_qty
            }
            st.session_state.data_to_submit.append(new_data)
            st.success("입고 리스트에 추가되었습니다.")

# --- AG Grid 및 DB 전송 로직 ---
st.header("📋 전송 대기중인 입고 리스트")
if st.session_state.data_to_submit:
    df_to_submit = pd.DataFrame(st.session_state.data_to_submit)
    column_order = ["입고일자", "발주번호", "품번", "품명", "버전", "LOT", "유통기한", "확정수량"]
    
    gb = GridOptionsBuilder.from_dataframe(df_to_submit[column_order])
    # 그리드 내 수정 기능 활성화
    gb.configure_column("확정수량", editable=True)
    gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=True)
    gridOptions = gb.build()

    grid_response = AgGrid(
        df_to_submit,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        height=350,
        reload_data=False # 수정한 데이터를 유지하기 위해 False로 설정
    )
    
    # 수정된 데이터 세션 상태에 반영
    st.session_state.data_to_submit = grid_response['data'].to_dict('records')
    selected_rows = grid_response["selected_rows"]

    # 리스트 관리 버튼
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 5])
    with col_btn1:
        if st.button("선택 항목 삭제", disabled=not selected_rows):
            selected_indices = [row['_selectedRowNodeInfo']['nodeRowIndex'] for row in selected_rows]
            st.session_state.data_to_submit = [
                row for i, row in enumerate(st.session_state.data_to_submit) if i not in selected_indices
            ]
            st.rerun()
    with col_btn2:
        if st.button("리스트 비우기", type="secondary"):
            st.session_state.data_to_submit = []
            st.rerun()
else:
    st.info("DB로 전송할 데이터가 없습니다.")

# 최종 DB 전송 버튼
if st.session_state.data_to_submit:
    if st.button("✅ 완료 및 DB 전송", type="primary"):
        with st.spinner('데이터를 DB에 저장하는 중입니다...'):
            success, message = insert_receiving_data(st.session_state.data_to_submit)
            if success:
                st.success(f"성공! {len(st.session_state.data_to_submit)}개의 데이터를 DB에 전송했습니다.")
                st.session_state.data_to_submit = []
                st.rerun()
            else:
                st.error(f"DB 전송 실패: {message}")
