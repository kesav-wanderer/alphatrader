#!/bin/bash
set -e

if [ ! -d "venv" ]; then
    echo "venv not found — run ./setup.sh first"
    exit 1
fi

source venv/bin/activate
streamlit run frontend/app.py --server.port 8501
