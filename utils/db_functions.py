# utils/db_functions.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine # SQLAlchemy로 변경

# --- DB 커넥션 생성 (SQLAlchemy 엔진 사용) ---

@st.cache_resource
def init_connection_erp():
    """ERP DB(MySQL)에 연결하는 SQLAlchemy 엔진을 생성합니다."""
    try:
        # pymysql을 사용하는 연결 문자열
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
            # MySQL 문법에 맞게 DATE_SUB() 사용
            query = """
                SELECT 
                    BrandName AS 브랜드,
                    ItemNo AS 품번,
                    ItemName AS 품명,
                    TPONO AS 발주번호,
                    ROUND(Qty, 0) AS 입고예정수량
                FROM 
                    invoice_requests
                WHERE 
                    created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            """
            # SQLAlchemy 엔진을 사용하여 데이터프레임으로 바로 로드
            df = pd.read_sql(query, engine_erp)
            return df
        except Exception as e:
            st.error(f"소스 데이터 조회 오류: {e}")
            # 에러 발생 시 빈 데이터프레임을 반환하도록 수정
            return pd.DataFrame() 
    # 엔진 생성 실패 시 빈 데이터프레임 반환
    return pd.DataFrame()


# --- 데이터 저장 함수 (SCM DB 사용) ---
def insert_receiving_data(data_list):
    """입고 데이터를 SCM DB 테이블에 삽입합니다."""
    if engine_scm is not None and data_list:
        try:
            df_to_insert = pd.DataFrame(data_list)
            
            # 컬럼명 매핑 및 추가 (테이블 스키마에 맞게)
            df_to_insert.rename(columns={'확정수량': '확정수량'}, inplace=True)
            df_to_insert['확정일'] = pd.to_datetime('today').normalize()
            df_to_insert['입고예정수량'] = 0 # INSERT 시 기본값
            
            # 최종적으로 테이블에 들어갈 컬럼만 선택
            final_columns = ['입고일자', '발주번호', '품번', '품명', '버전', 'LOT', '유통기한', '확정수량', '확정일', '입고예정수량']
            df_final = df_to_insert[final_columns]
            
            # DataFrame을 SQL 테이블에 바로 삽입
            df_final.to_sql('input_manage_master', con=engine_scm, schema='scm', if_exists='append', index=False)
            
            return True, "데이터 전송 성공"
        except Exception as e:
            return False, str(e)
            
    return False, "DB 연결 또는 데이터 없음"
