#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

FLOW_MODE=false
DEV_MODE=false
for arg in "$@"; do
  case "$arg" in
    --flow) FLOW_MODE=true ;;
    --dev) DEV_MODE=true ;;
  esac
done

RELOAD_FLAG=""
[ "$DEV_MODE" = true ] && RELOAD_FLAG="--reload"

cleanup() {
  echo ""
  echo "Shutting down servers..."
  pids=()
  [ -n "$BACKEND_PID" ] && pids+=("$BACKEND_PID")
  [ -n "$FLOW_PID" ] && pids+=("$FLOW_PID")
  [ -n "$FRONTEND_PID" ] && pids+=("$FRONTEND_PID")
  [ -n "$WORKER_PID" ] && pids+=("$WORKER_PID")
  if [ "${#pids[@]}" -gt 0 ]; then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
  echo "Done."
}
trap cleanup EXIT INT TERM

# Kill any stale processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Shared JWT secret so core and flow backends can verify the same tokens
export GDM_SECRET_KEY="fgc-studio-dev-secret-key-change-in-production"

# ── Core Backend ─────────────────────────────────────────
echo "Starting core backend (FastAPI) on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
export GDM_UPLOAD_DIR="/home/aadil/Documents/gfc_files/uploads"
export GDM_DATABASE_URL="sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db"
mkdir -p "$GDM_UPLOAD_DIR"
mkdir -p "/home/aadil/Documents/gfc_files/database"
"$SCRIPT_DIR/.venv/bin/python" -m uvicorn fgc_core.main:app --host 0.0.0.0 --port 8000 $RELOAD_FLAG &
BACKEND_PID=$!

# ── Flow Backend (optional) ──────────────────────────────
if [ "$FLOW_MODE" = true ]; then
  echo "Starting flow backend (FGC Flow API) on http://localhost:8001 ..."
  export FGC_FLOW_UPLOAD_DIR="/home/aadil/Documents/gfc_files/uploads"
  export FGC_FLOW_DATABASE_URL="sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/fgc_flow.db"
  export FGC_FLOW_JOBS_DATABASE_URL="sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/fgc_flow_jobs.db"
  mkdir -p "$FGC_FLOW_UPLOAD_DIR"
  mkdir -p "/home/aadil/Documents/gfc_files/database"
  "$SCRIPT_DIR/.venv/bin/python" -m uvicorn fgc_flow_api.main:app --host 0.0.0.0 --port 8001 $RELOAD_FLAG &
  FLOW_PID=$!
  echo "Starting simulation job worker..."
  "$SCRIPT_DIR/.venv/bin/python" -m fgc_flow_api.worker &
  WORKER_PID=$!
fi

# ── Frontend ─────────────────────────────────────────────
echo "Starting frontend (Vite)  on http://0.0.0.0:5173 ..."
cd "$SCRIPT_DIR/frontend"
export VITE_API_URL=""
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "GDM Studio is running:"
echo "  Core Backend → http://localhost:8000"
if [ "$FLOW_MODE" = true ]; then
  echo "  Flow Backend → http://localhost:8001"
fi
echo "  Frontend     → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers."

wait
