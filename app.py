# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.db_functions import get_product_data, insert_receiving_data
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="입고 등록 관리 시스템")
st.title("📦 입고 등록 관리 시스템")

# --- 세션 상태 초기화 ---
if 'data_to_submit' not in st.session_state:
    st.session_state.data_to_submit = []

# --- 데이터 로딩 ---
# DB에서 품번, 품명 데이터를 가져옵니다.
# @st.cache_data를 사용해 불필요한 DB 조회를 최소화합니다.
@st.cache_data
def load_product_data():
    return get_product_data()

product_df = load_product_data()
# 품번을 key, 품명을 value로 하는 딕셔너리 생성
product_dict = pd.Series(product_df['품명'].values, index=product_df['품번']).to_dict()

# --- 입력 폼 ---
st.header("📝 신규 입고 등록")
with st.form(key="receiving_form", clear_on_submit=True):
    cols1 = st.columns(3)
    with cols1[0]:
        receiving_date = st.date_input("입고 일자", value=date.today())
    with cols1[1]:
        part_number = st.selectbox("품번 선택", options=product_dict.keys(), key="part_number")
    with cols1[2]:
        # 선택된 품번에 따라 품명을 자동으로 표시 (수정 불가)
        product_name = st.text_input("품명", value=product_dict[st.session_state.part_number], disabled=True)

    cols2 = st.columns(4)
    with cols2[0]:
        version = st.text_input("버전")
    with cols2[1]:
        lot_number = st.text_input("LOT")
    with cols2[2]:
        expiry_date = st.date_input("유통기한", value=date.today())
    
    st.subheader("입고 수량")
    cols3 = st.columns(2)
    with cols3[0]:
        b2b_qty = st.number_input("B2B운영", min_value=0, step=1)
    with cols3[1]:
        b2c_qty = st.number_input("B2C운영", min_value=0, step=1)

    # '추가' 버튼
    add_button = st.form_submit_button(label="리스트에 추가")

if add_button:
    if not part_number or not lot_number:
        st.warning("품번과 LOT는 필수 입력 항목입니다.")
    else:
        new_data = {
            "입고일자": receiving_date.strftime("%Y-%m-%d"),
            "품번": part_number,
            "품명": product_name,
            "버전": version,
            "LOT": lot_number,
            "유통기한": expiry_date.strftime("%Y-%m-%d"),
            "B2B수량": b2b_qty,
            "B2C수량": b2c_qty
        }
        st.session_state.data_to_submit.append(new_data)
        st.success("입고 리스트에 추가되었습니다. 하단 표에서 확인하세요.")

# --- AG Grid로 추가된 데이터 표시 ---
st.header("📋 전송 대기중인 입고 리스트")
if st.session_state.data_to_submit:
    df_to_submit = pd.DataFrame(st.session_state.data_to_submit)
    
    # AG Grid 옵션 설정
    gb = GridOptionsBuilder.from_dataframe(df_to_submit)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gridOptions = gb.build()

    AgGrid(
        df_to_submit,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True,
        theme='streamlit',
        enable_enterprise_modules=False,
        height=350,
        width='100%',
        reload_data=True
    )
else:
    st.info("DB로 전송할 데이터가 없습니다. 위 폼에서 입고 정보를 추가해주세요.")

# --- 최종 DB 전송 버튼 ---
if st.session_state.data_to_submit:
    if st.button("✅ 완료 및 DB 전송", type="primary"):
        with st.spinner('데이터를 DB에 저장하는 중입니다...'):
            success, message = insert_receiving_data(st.session_state.data_to_submit)
            if success:
                st.success(f"성공적으로 {len(st.session_state.data_to_submit)}개의 데이터를 DB에 전송했습니다!")
                # 성공 시 세션 상태 초기화
                st.session_state.data_to_submit = []
                st.experimental_rerun() # 화면 새로고침
            else:
                st.error(f"DB 전송 실패: {message}")
