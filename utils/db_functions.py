# utils/db_functions.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- DB 커넥션 생성 (이전과 동일) ---
@st.cache_resource
def init_connection_erp():
    # ... (이전 코드와 동일)
@st.cache_resource
def init_connection_scm():
    # ... (이전 코드와 동일)

# --- 데이터 조회 함수 (새로운 쿼리로 전체 교체) ---
def get_source_data():
    """ERP DB에서 입고 예정 데이터를 새로운 쿼리로 조회합니다."""
    engine_erp = init_connection_erp()
    if engine_erp is not None:
        try:
            # ▼▼▼ [새로운 쿼리로 교체] ▼▼▼
            query = """
                SELECT 
                    nii.intended_push_date AS 입고예정일,
                    nii.po_no AS 발주번호,
                    niid.product_code AS 품번,
                    niid.product_name AS 품명,
                    niid.lot AS 버전,
                    SUM(niid.quantity) AS 예정수량
                FROM 
                    boosters.nansoft_intended_inventory_details AS niid
                LEFT JOIN
                    boosters.nansoft_intended_inventorys AS nii 
                ON
                    nii.id = niid.nansoft_intended_inventory_id
                LEFT JOIN
                    boosters_erp.erp_items AS ei
                ON
                    ei.itemno = niid.product_code
                WHERE
                    nii.intended_push_date >= CURDATE() AND nii.is_delete = 0
                GROUP BY 
                    nii.intended_push_date,
                    nii.po_no,
                    niid.product_code, 
                    niid.product_name, 
                    niid.lot
                ORDER BY 
                    nii.intended_push_date, niid.product_name
            """
            # ▲▲▲ [새로운 쿼리로 교체] ▲▲▲
            df = pd.read_sql(query, engine_erp)
            return df
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 데이터 저장 함수 (이전과 동일) ---
def insert_receiving_data(data_list):
    # ... (이전 코드와 동일)
