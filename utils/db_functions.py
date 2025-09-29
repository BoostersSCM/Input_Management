# utils/db_functions.py
import streamlit as st
import pyodbc
import pandas as pd

# --- DB 연결 초기화 ---
# @st.cache_resource를 사용해 한 번만 연결 객체를 생성합니다.
@st.cache_resource
def init_connection():
    try:
        connection = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={st.secrets['db_server']};"
            f"DATABASE={st.secrets['db_name']};"
            f"UID={st.secrets['db_user']};"
            f"PWD={st.secrets['db_password']}"
        )
        return connection
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        return None

conn = init_connection()

# --- 품번/품명 데이터 조회 함수 ---
def get_product_data():
    if conn:
        try:
            query = "SELECT 품번, 품명 FROM YourProductTable" # 실제 테이블명으로 변경
            df = pd.read_sql(query, conn)
            return df
        except Exception as e:
            st.error(f"제품 데이터 조회 오류: {e}")
            return pd.DataFrame() # 오류 발생 시 빈 데이터프레임 반환
    return pd.DataFrame()

def insert_receiving_data(data_list):
    """입고 데이터를 DB 테이블에 삽입합니다."""
    if conn and data_list:
        cursor = conn.cursor()
        try:
            # ▼▼▼ [수정된 부분] ▼▼▼
            # 테이블 경로를 [스키마].[테이블명]으로 정확히 지정합니다.
            query = """
                INSERT INTO [scm].[input_manage_master] 
                (입고일자, 발주번호, 품번, 품명, 버전, LOT, 유통기한, 확정수량, 확정일, 입고예정수량)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 0) 
            """
            # ▲▲▲ [수정된 부분] ▲▲▲
            
            rows_to_insert = [
                (d['입고일자'], d['발주번호'], d['품번'], d['품명'], d['버전'], d['LOT'], d['유통기한'], d['확정수량'])
                for d in data_list
            ]
            
            cursor.executemany(query, rows_to_insert)
            conn.commit()
            return True, "데이터 전송 성공"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cursor.close()
    return False, "DB 연결 또는 데이터 없음"
