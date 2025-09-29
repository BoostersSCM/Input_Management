# utils/db_functions.py
import streamlit as st
import pyodbc
import pandas as pd

# --- DB 커넥션 생성 (2개) ---

@st.cache_resource
def init_connection_erp():
    """ERP DB(데이터 조회용)에 연결합니다."""
    try:
        connection = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={st.secrets['db_server_erp']};"
            f"DATABASE={st.secrets['db_name_erp']};"
            f"UID={st.secrets['db_user_erp']};"
            f"PWD={st.secrets['db_password_erp']}"
        )
        return connection
    except Exception as e:
        st.error(f"ERP DB 연결 오류: {e}")
        return None

@st.cache_resource
def init_connection_scm():
    """SCM DB(데이터 저장용)에 연결합니다."""
    try:
        connection = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={st.secrets['db_server_scm']};"
            f"DATABASE={st.secrets['db_name_scm']};"
            f"UID={st.secrets['db_user_scm']};"
            f"PWD={st.secrets['db_password_scm']}"
        )
        return connection
    except Exception as e:
        st.error(f"SCM DB 연결 오류: {e}")
        return None

conn_erp = init_connection_erp()
conn_scm = init_connection_scm()


# --- 데이터 조회 함수 (ERP DB 사용) ---
def get_source_data():
    """ERP DB에서 브랜드, 발주번호, 품번, 품명 데이터를 조회합니다."""
    if conn_erp:
        try:
            # ▼▼▼ [수정된 부분] ▼▼▼
            # BrandName AS 브랜드 컬럼을 추가합니다.
            query = """
                SELECT 
                    BrandName AS 브랜드,
                    ItemNo AS 품번,
                    ItemName AS 품명,
                    TPONO AS 발주번호
                FROM 
                    boosters_erp.invoice_requests
                WHERE 
                    created_at >= DATEADD(month, -12, GETDATE())
            """
            # ▲▲▲ [수정된 부분] ▲▲▲
            df = pd.read_sql(query, conn_erp)
            return df
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 데이터 저장 함수 (SCM DB 사용) ---
def insert_receiving_data(data_list):
    """입고 데이터를 SCM DB 테이블에 삽입합니다."""
    # 이 함수는 conn_scm을 사용합니다.
    if conn_scm and data_list:
        cursor = conn_scm.cursor()
        try:
            query = """
                INSERT INTO [scm].[input_manage_master] 
                (입고일자, 발주번호, 품번, 품명, 버전, LOT, 유통기한, 확정수량, 확정일, 입고예정수량)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 0) 
            """
            rows_to_insert = [
                (d['입고일자'], d['발주번호'], d['품번'], d['품명'], d['버전'], d['LOT'], d['유통기한'], d['확정수량'])
                for d in data_list
            ]
            cursor.executemany(query, rows_to_insert)
            conn_scm.commit()
            return True, "데이터 전송 성공"
        except Exception as e:
            conn_scm.rollback()
            return False, str(e)
        finally:
            cursor.close()
    return False, "DB 연결 또는 데이터 없음"
