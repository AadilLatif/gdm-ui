#!/usr/bin/env bash
# Launch GDM Studio — backend + frontend dev servers
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
.venv/bin/python run.py &
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
