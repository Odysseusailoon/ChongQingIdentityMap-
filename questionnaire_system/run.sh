#!/bin/bash

# 启动Redis（如果未启动）
if ! pgrep -x "redis-server" > /dev/null
then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# 安装依赖
echo "Installing dependencies..."
pip install -r requirements.txt

# Function to clean up background processes on exit
cleanup() {
    echo "Shutting down servers..."
    kill $STREAMLIT_PID
    kill $FASTAPI_PID
    exit
}

# Trap script exit signals and call cleanup
trap cleanup SIGINT SIGTERM

# 启动 Streamlit 应用
echo "Starting Streamlit app on port 8501..."
streamlit run app.py --server.port 8501 &
STREAMLIT_PID=$!

# 启动 FastAPI 应用
echo "Starting FastAPI app on port 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for both processes to complete
wait $STREAMLIT_PID
wait $FASTAPI_PID 