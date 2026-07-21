#!/bin/bash
# GovernAI — Full Demo Stack Startup Script (WSL/Ubuntu)

set -e

PROJECT_ROOT="/mnt/c/Users/georg/GovernAI-/governnew"
KIJI_DIR="$HOME/kiji-proxy"            # EDIT if Kiji lives somewhere else

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "=== GovernAI Startup ==="
echo "Project root: $PROJECT_ROOT"
echo "Logs:         $LOG_DIR"
echo ""

cd "$PROJECT_ROOT"
echo "[ok] using system python3 (no venv)"

if [ -d "$KIJI_DIR" ]; then
    echo "[1/4] Starting Kiji Privacy Proxy..."
    (cd "$KIJI_DIR" && nohup kiji-proxy > "$LOG_DIR/kiji.log" 2>&1 &)
    sleep 2
    echo "      -> logs: $LOG_DIR/kiji.log"
else
    echo "[1/4] Kiji dir not found at $KIJI_DIR — skipping (PII masking unavailable)"
fi

echo "[2/4] Starting FastAPI Intake API (port 8000)..."
(cd "$PROJECT_ROOT/governai" && nohup uvicorn api.server:app --reload --port 8000 > "$LOG_DIR/fastapi.log" 2>&1 &)
sleep 2
echo "      -> http://localhost:8000"

echo "[3/4] Starting GovernAI Dashboard (port 8501)..."
(cd "$PROJECT_ROOT" && nohup streamlit run governai/Home.py --server.port 8501 > "$LOG_DIR/dashboard.log" 2>&1 &)
sleep 2
echo "      -> http://localhost:8501"

echo "[4/4] Starting HR Resume Screener (port 8502)..."
(cd "$PROJECT_ROOT" && nohup streamlit run resume_screener_app.py --server.port 8502 > "$LOG_DIR/screener.log" 2>&1 &)
sleep 2
echo "      -> http://localhost:8502"

echo ""
echo "=== All services launched ==="
echo "Dashboard:  http://localhost:8501"
echo "Screener:   http://localhost:8502"
echo "API:        http://localhost:8000/docs"
echo ""
echo "To stop: ./stop.sh"
