# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.db_functions import get_source_data, insert_receiving_data # 함수명 변경
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="입고 등록 관리 시스템")
st.title("📦 입고 등록 관리 시스템")

# --- 세션 상태 초기화 ---
if 'data_to_submit' not in st.session_state:
    st.session_state.data_to_submit = []

# --- 데이터 로딩 (수정된 부분) ---
@st.cache_data
def load_data():
    """ERP DB에서 소스 데이터를 한 번에 불러와 가공합니다."""
    source_df = get_source_data()
    if not source_df.empty:
        # 중복 제거 및 데이터 가공
        product_df = source_df[['품번', '품명']].drop_duplicates().set_index('품번')
        product_dict = product_df['품명'].to_dict()
        order_numbers = source_df['발주번호'].unique().tolist()
        return product_dict, order_numbers
    return {}, []

product_dict, order_numbers = load_data()

# --- 입력 폼 ---
st.header("📝 신규 입고 등록")
with st.form(key="receiving_form", clear_on_submit=True):
    cols1 = st.columns(4)
    with cols1[0]:
        receiving_date = st.date_input("입고 일자", value=date.today())
    with cols1[1]:
        purchase_order = st.selectbox("발주번호 선택", options=order_numbers, index=None, placeholder="발주번호를 선택하세요")
    with cols1[2]:
        part_number = st.selectbox("품번 선택", options=list(product_dict.keys()), key="part_number", index=None, placeholder="품번을 선택하세요")
    with cols1[3]:
        product_name = st.text_input("품명", value=product_dict.get(st.session_state.part_number, ""), disabled=True)

    cols2 = st.columns(4)
    with cols2[0]:
        version = st.text_input("버전")
    with cols2[1]:
        lot_number = st.text_input("LOT")
    with cols2[2]:
        expiry_date = st.date_input("유통기한")
    with cols2[3]:
        final_qty = st.number_input("확정 수량", min_value=0, step=1)

    add_button = st.form_submit_button(label="리스트에 추가")

if add_button:
    if not purchase_order or not part_number or not lot_number:
        st.warning("발주번호, 품번, LOT는 필수 입력 항목입니다.")
    else:
        new_data = {
            "입고일자": receiving_date.strftime("%Y-%m-%d"), "발주번호": purchase_order,
            "품번": part_number, "품명": product_name, "버전": version, "LOT": lot_number,
            "유통기한": expiry_date.strftime("%Y-%m-%d"), "확정수량": final_qty
        }
        st.session_state.data_to_submit.append(new_data)
        st.success("입고 리스트에 추가되었습니다.")

# --- AG Grid로 추가된 데이터 표시 ---
# (이하 코드는 이전과 동일하며, 변경할 필요 없습니다.)
st.header("📋 전송 대기중인 입고 리스트")
if st.session_state.data_to_submit:
    df_to_submit = pd.DataFrame(st.session_state.data_to_submit)
    column_order = ["입고일자", "발주번호", "품번", "품명", "버전", "LOT", "유통기한", "확정수량"]
    df_to_submit = df_to_submit[column_order]
    gb = GridOptionsBuilder.from_dataframe(df_to_submit)
    gb.configure_pagination(paginationAutoPageSize=True)
    gridOptions = gb.build()
    AgGrid(df_to_submit, gridOptions=gridOptions, fit_columns_on_grid_load=True, theme='streamlit', height=350, reload_data=True)
else:
    st.info("DB로 전송할 데이터가 없습니다.")

# --- 최종 DB 전송 버튼 ---
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
