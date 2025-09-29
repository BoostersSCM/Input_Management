# utils/db_functions.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- DB 커넥션 생성 (SQLAlchemy 엔진 사용) ---
@st.cache_resource
def init_connection_erp():
    """ERP DB(MySQL)에 연결하는 SQLAlchemy 엔진을 생성합니다."""
    try:
        db_uri = (
            f"mysql+pymysql://{st.secrets['db_user_erp']}:{st.secrets['db_password_erp']}"
            f"@{st.secrets['db_server_erp']}:{st.secrets.get('db_port_erp', 3306)}"
            f"/{st.secrets['db_name_erp']}"
        )
        engine = create_engine(db_uri)
        return engine
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
        engine = create_engine(db_uri)
        return engine
    except Exception as e:
        st.error(f"SCM DB 연결 오류: {e}")
        return None

# --- 데이터 조회 함수 (ERP DB 사용) ---
def get_source_data():
    """ERP DB에서 입고 예정 데이터를 새로운 쿼리로 조회합니다."""
    engine_erp = init_connection_erp()
    if engine_erp is not None:
        try:
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
            df = pd.read_sql(query, engine_erp)
            return df
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 데이터 저장 함수 (SCM DB 사용) ---
def insert_receiving_data(data_list):
    """입고 데이터를 SCM DB 테이블에 삽입합니다."""
    engine_scm = init_connection_scm()
    if engine_scm is not None and data_list:
        try:
            df_to_insert = pd.DataFrame(data_list)
            
            # 테이블 스키마에 맞게 컬럼 추가 및 정리
            df_to_insert['확정일'] = pd.to_datetime('today').normalize()
            # '입고예정수량' 컬럼이 이미 있으므로 INSERT 시에는 이 값을 사용하지 않음
            # 만약 DB 테이블에 이 값도 넣어야 한다면 로직 수정 필요
            
            # 최종적으로 DB 테이블에 들어갈 컬럼만 선택
            final_columns = ['입고일자', '발주번호', '품번', '품명', '버전', 'LOT', '유통기한', '확정수량', '확정일']
            df_final = df_to_insert[final_columns]
            
            # DataFrame을 SQL 테이블에 바로 삽입 (스키마 'scm', 테이블 'input_manage_master')
            df_final.to_sql('input_manage_master', con=engine_scm, schema='scm', if_exists='append', index=False)
            
            return True, "데이터 전송 성공"
        except Exception as e:
            return False, str(e)
            
    return False, "DB 연결 또는 데이터 없음"
