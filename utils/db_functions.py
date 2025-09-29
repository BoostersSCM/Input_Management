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

# --- 입고 데이터 삽입 함수 ---
def insert_receiving_data(data_list):
    if conn and data_list:
        cursor = conn.cursor()
        try:
            # SQL Injection 방지를 위해 파라미터화된 쿼리 사용
            query = """
                INSERT INTO YourReceivingTable (입고일자, 품번, 품명, 버전, LOT, 유통기한, B2B수량, B2C수량)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
            """ # 실제 테이블명과 컬럼명으로 변경
            
            # 딕셔너리 리스트를 튜플 리스트로 변환
            rows_to_insert = [tuple(d.values()) for d in data_list]
            
            cursor.executemany(query, rows_to_insert)
            conn.commit()
            return True, "데이터 전송 성공"
        except Exception as e:
            conn.rollback() # 오류 발생 시 롤백
            return False, str(e)
        finally:
            cursor.close()
    return False, "DB 연결 또는 데이터 없음"
