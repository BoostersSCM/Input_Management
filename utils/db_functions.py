# utils/db_functions.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

@st.cache_resource
def init_connection_erp():
    try:
        db_uri = (f"mysql+pymysql://{st.secrets['db_user_erp']}:{st.secrets['db_password_erp']}"
                  f"@{st.secrets['db_server_erp']}:{st.secrets.get('db_port_erp', 3306)}"
                  f"/{st.secrets['db_name_erp']}")
        return create_engine(db_uri)
    except Exception as e:
        st.error(f"ERP DB 연결 오류: {e}")
        return None

@st.cache_resource
def init_connection_scm():
    try:
        db_uri = (f"mysql+pymysql://{st.secrets['db_user_scm']}:{st.secrets['db_password_scm']}"
                  f"@{st.secrets['db_server_scm']}:{st.secrets.get('db_port_scm', 3306)}"
                  f"/{st.secrets['db_name_scm']}")
        return create_engine(db_uri)
    except Exception as e:
        st.error(f"SCM DB 연결 오류: {e}")
        return None

def get_source_data():
    engine_erp = init_connection_erp()
    if engine_erp is not None:
        try:
            # ▼▼▼ [수정된 최종 쿼리] ▼▼▼
            query = """
                SELECT 
                    SUBSTRING_INDEX(niid.product_name, '-', 1) AS 브랜드,
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
                    브랜드, -- GROUP BY에 브랜드 추가
                    nii.intended_push_date,
                    nii.po_no,
                    niid.product_code, 
                    niid.product_name, 
                    niid.lot
                ORDER BY 
                    nii.intended_push_date, niid.product_name
            """
            # ▲▲▲ [수정된 최종 쿼리] ▲▲▲
            return pd.read_sql(query, engine_erp)
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def insert_receiving_data(data_list):
    engine_scm = init_connection_scm()
    if engine_scm is not None and data_list:
        try:
            df_to_insert = pd.DataFrame(data_list)
            df_to_insert['확정일'] = pd.to_datetime('today').normalize()
            final_columns = ['입고일자', '발주번호', '품번', '품명', '버전', 'LOT', '유통기한', '확정수량', '확정일']
            df_final = df_to_insert[final_columns]
            df_final.to_sql('input_manage_master', con=engine_scm, schema='scm', if_exists='append', index=False)
            return True, "데이터 전송 성공"
        except Exception as e:
            return False, str(e)
    return False, "DB 연결 또는 데이터 없음"
