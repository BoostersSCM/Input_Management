# app.py (홈 또는 리디렉션용)
import streamlit as st

st.set_page_config(page_title="📦 입고 관리 시스템", layout="wide")

st.title("🚀 입고 관리 시스템 홈")
st.markdown("""
이 시스템은 다음 기능을 제공합니다:

1. 📥 **입고 등록 관리**: 입고 예정 품목을 등록 및 편집하고 DB에 전송  
2. 📜 **입고 예정 이력**: ERP에서 입고 예정 이력을 조회  
3. 📅 **입고 캘린더**: 월별 입고 예정 품목을 시각화  

👉 왼쪽 사이드바에서 원하는 기능을 선택하세요.
""")

st.markdown("---")
st.caption("이 시스템은 [GPT온라인](https://gptonline.ai/ko/) 예제를 기반으로 만들어졌습니다.")
