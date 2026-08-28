#!/usr/bin/env bash
#
# Starts the whole SevaSetu app: model service (port 8000), backend
# (port 4000), frontend (port 5173). Sets up each piece's virtual env /
# node_modules on first run, then starts them in order (model service must
# answer /health before the backend starts, since RemoteClassifier has no
# fallback). Ctrl+C stops all three.
#
# Usage: ./run.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/app"
MODEL_SERVICE_DIR="$APP_DIR/model_service"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

MODEL_SERVICE_PORT="${MODEL_SERVICE_PORT:-8000}"
BACKEND_PORT="${PORT:-4000}"

PIDS=()

cleanup() {
  echo ""
  echo "Stopping..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "== SevaSetu: model service, backend, frontend =="

# --- model service -----------------------------------------------------
if [ ! -d "$MODEL_SERVICE_DIR/.venv" ]; then
  echo "[model_service] first run: creating venv and installing dependencies"
  echo "[model_service] (this includes TensorFlow, can take a few minutes)"
  python3.11 -m venv "$MODEL_SERVICE_DIR/.venv"
  "$MODEL_SERVICE_DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$MODEL_SERVICE_DIR/.venv/bin/pip" install --quiet -r "$MODEL_SERVICE_DIR/requirements.txt"
fi

echo "[model_service] starting on :$MODEL_SERVICE_PORT (first import of TensorFlow can take a couple minutes)"
(
  cd "$MODEL_SERVICE_DIR"
  export PYTHONUNBUFFERED=1
  exec .venv/bin/uvicorn app:app --port "$MODEL_SERVICE_PORT"
) &
MODEL_SERVICE_PID="$!"
PIDS+=("$MODEL_SERVICE_PID")

echo "[model_service] waiting for it to come up..."
UP=""
for i in $(seq 1 180); do
  if curl -s -o /dev/null "http://localhost:$MODEL_SERVICE_PORT/health"; then
    UP=1
    break
  fi
  if ! kill -0 "$MODEL_SERVICE_PID" 2>/dev/null; then
    echo "[model_service] process exited early, check its output above"
    exit 1
  fi
  if [ $((i % 15)) -eq 0 ]; then
    echo "[model_service] still waiting (${i}s)..."
  fi
  sleep 1
done
if [ -z "$UP" ]; then
  echo "[model_service] did not come up after 180s, check its output above"
  exit 1
fi
echo "[model_service] up"

# --- backend -------------------------------------------------------------
if [ ! -d "$BACKEND_DIR/node_modules" ]; then
  echo "[backend] first run: npm install"
  (cd "$BACKEND_DIR" && npm install)
fi

echo "[backend] starting on :$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  export CLASSIFIER_URL="http://localhost:$MODEL_SERVICE_PORT"
  export PORT="$BACKEND_PORT"
  exec npm run dev
) &
PIDS+=("$!")

# --- frontend --------------------------------------------------------------
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "[frontend] first run: npm install"
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "[frontend] starting on :5173"
(
  cd "$FRONTEND_DIR"
  exec npm run dev
) &
PIDS+=("$!")

echo ""
echo "Officer dashboard: http://localhost:5173"
echo "Citizen tracker:   http://localhost:5173/track"
echo "Backend API:       http://localhost:$BACKEND_PORT"
echo "Model service:     http://localhost:$MODEL_SERVICE_PORT"
echo ""
echo "Ctrl+C to stop everything."

wait
