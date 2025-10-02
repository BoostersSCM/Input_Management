# utils/db_functions.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

@st.cache_resource
def init_connection_erp():
    """ERP DB(MySQL)에 연결하는 SQLAlchemy 엔진을 생성합니다."""
    try:
        db_uri = (
            f"mysql+pymysql://{st.secrets['db_user_erp']}:{st.secrets['db_password_erp']}"
            f"@{st.secrets['db_server_erp']}:{st.secrets.get('db_port_erp', 3306)}"
            f"/{st.secrets['db_name_erp']}"
        )
        return create_engine(db_uri)
    except Exception as e:
        st.error(f"ERP DB 연결 오류: {e}")
        return None

@st.cache_resource
def init_connection_scm():
    """SCM DB(MySQL)에 연결하는 SQLAlchemy 엔진을 생성합니다."""
    try:
        db_uri = (
            f"mysql+pymysql://{st.secrets['db_user_scm']}:{st.secrets['db_password_scm']}"
            f"@{st.secrets['db_server_scm']}:{st.secrets.get('db_port_scm', 3306)}"
            f"/{st.secrets['db_name_scm']}"
        )
        return create_engine(db_uri)
    except Exception as e:
        st.error(f"SCM DB 연결 오류: {e}")
        return None

def get_source_data():
    """ERP DB에서 소스 데이터를 조회합니다."""
    engine_erp = init_connection_erp()
    if engine_erp is not None:
        try:
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
                    nii.intended_push_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) 
                    AND nii.is_delete = 0
                GROUP BY 
                    브랜드,
                    nii.intended_push_date,
                    nii.po_no,
                    niid.product_code, 
                    niid.product_name, 
                    niid.lot
                ORDER BY 
                    nii.intended_push_date, niid.product_name
            """
            return pd.read_sql(query, engine_erp)
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def insert_receiving_data(data_list):
    """입고 데이터를 SCM DB 테이블에 삽입합니다."""
    engine_scm = init_connection_scm()
    if engine_scm is not None and data_list:
        try:
            df_to_insert = pd.DataFrame(data_list)
            
            df_to_insert['확정일'] = pd.to_datetime('today').normalize()
            
            # ▼▼▼ [수정된 부분] ▼▼▼
            # DB에 전송하기 직전, DataFrame의 '예정수량' 컬럼명을 DB 테이블에 맞게 '입고예정수량'으로 변경
            df_to_insert.rename(columns={'예정수량': '입고예정수량'}, inplace=True)
            
            # DB 테이블 스키마와 정확히 일치하도록 전송할 컬럼 리스트를 수정
            final_columns = [
                '입고일자', '발주번호', '품번', '품명', '버전', 
                'LOT', '유통기한', '확정수량', '확정일', '입고예정수량'
            ]
            # ▲▲▲ [수정된 부분] ▲▲▲

            for col in final_columns:
                if col not in df_to_insert.columns:
                    df_to_insert[col] = None

            df_final = df_to_insert[final_columns]
            
            df_final.to_sql('input_manage_master', con=engine_scm, schema='scm', if_exists='append', index=False)
            
            return True, "데이터 전송 성공"
        except Exception as e:
            return False, str(e)
            
    return False, "DB 연결 또는 데이터 없음"

# ▼▼▼ [새로 추가할 함수] ▼▼▼
def get_history_data():
    """ERP DB에서 전체 입고 예정 이력 데이터를 조회합니다."""
    engine_erp = init_connection_erp()
    if engine_erp is not None:
        try:
            query = """
                SELECT 
                    SUBSTRING_INDEX(niid.product_name, '-', 1) AS 브랜드,
                    nii.intended_push_date AS 입고예정일,
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
                    nii.is_delete = 0 and  nii.intended_push_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) 
                GROUP BY 
                    브랜드,
                    nii.intended_push_date,
                    niid.product_code, 
                    niid.product_name, 
                    niid.lot
                ORDER BY 
                    nii.intended_push_date DESC, niid.product_name
            """
            # 참고: 요청하신 쿼리에서 브랜드, 정렬 순서 등 일부를 최적화했습니다.
            df = pd.read_sql(query, engine_erp)
            return df
        except Exception as e:
            st.error(f"이력 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()
# ▲▲▲ [새로 추가할 함수] ▲▲▲
