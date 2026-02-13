#!/bin/bash
set -e

# 启动 FastAPI（后台）
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &

# 启动 Streamlit（前台）
streamlit run app/ui/main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
