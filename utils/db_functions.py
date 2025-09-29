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

engine_erp = init_connection_erp()
engine_scm = init_connection_scm()

# --- 데이터 조회 함수 (ERP DB 사용) ---
def get_source_data():
    """ERP DB에서 소스 데이터를 조회합니다."""
    if engine_erp is not None:
        try:
            # ▼▼▼ [수정된 최종 쿼리] ▼▼▼
            query = """
                SELECT 
                    BrandName AS 브랜드,
                    ItemNo AS 품번,
                    ItemName AS 품명,
                    TPONO AS 발주번호,
                    ROUND(Qty, 0) AS 입고예정수량
                FROM 
                    boosters_erp.invoice_requests
                WHERE 
                    created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            """
            # ▲▲▲ [수정된 최종 쿼리] ▲▲▲
            df = pd.read_sql(query, engine_erp)
            return df
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame() 
    return pd.DataFrame()

# --- 데이터 저장 함수 (SCM DB 사용) ---
def insert_receiving_data(data_list):
    """입고 데이터를 SCM DB 테이블에 삽입합니다."""
    if engine_scm is not None and data_list:
        try:
            df_to_insert = pd.DataFrame(data_list)
            
            df_to_insert.rename(columns={'확정수량': '확정수량'}, inplace=True)
            df_to_insert['확정일'] = pd.to_datetime('today').normalize()
            df_to_insert['입고예정수량'] = 0
            
            final_columns = ['입고일자', '발주번호', '품번', '품명', '버전', 'LOT', '유통기한', '확정수량', '확정일', '입고예정수량']
            df_final = df_to_insert[final_columns]
            
            df_final.to_sql('input_manage_master', con=engine_scm, schema='scm', if_exists='append', index=False)
            
            return True, "데이터 전송 성공"
        except Exception as e:
            return False, str(e)
            
    return False, "DB 연결 또는 데이터 없음"
