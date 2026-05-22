#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# Kill any stale processes on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# ── Backend ──────────────────────────────────────────────
echo "Starting backend (FastAPI) on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
export GDM_UPLOAD_DIR="/home/aadil/Documents/gfc_files/uploads"
export GDM_DATABASE_URL="sqlite+aiosqlite:///home/aadil/Documents/gfc_files/database/gdm_studio.db"
mkdir -p "$GDM_UPLOAD_DIR"
mkdir -p "/home/aadil/Documents/gfc_files/database"
"$SCRIPT_DIR/.venv/bin/python" -m uvicorn fgc_core.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────
echo "Starting frontend (Vite)  on http://localhost:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "GDM Studio is running:"
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers."

wait