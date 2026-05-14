@echo off
call venv\Scripts\activate.bat
streamlit run frontend\app.py --server.port 8501
