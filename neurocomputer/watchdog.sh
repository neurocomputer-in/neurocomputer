#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# Neurocomputer Health Check Watchdog
# ────────────────────────────────────────────────────────────
# Checks the /health endpoint. If the server fails to respond
# after MAX_FAILURES consecutive checks, it kills any orphan
# process on the port and restarts the systemd service.
# ────────────────────────────────────────────────────────────

set -euo pipefail

HEALTH_URL="http://localhost:7000/health"
SERVICE_NAME="neurocomputer"
PORT=7000
STATE_FILE="/tmp/neurocomputer_watchdog_failures"
MAX_FAILURES=3          # restart after this many consecutive failures
TIMEOUT=10              # seconds to wait for health response
LOG_TAG="neurocomputer-watchdog"

log() { logger -t "$LOG_TAG" "$*"; echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Read current failure count
failures=0
[[ -f "$STATE_FILE" ]] && failures=$(cat "$STATE_FILE" 2>/dev/null || echo 0)

# Perform health check
http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null || echo "000")

if [[ "$http_code" == "200" ]]; then
    # Healthy — reset counter
    if [[ "$failures" -gt 0 ]]; then
        log "✅ Server recovered (was at $failures failures)"
    fi
    echo 0 > "$STATE_FILE"
    exit 0
fi

# Unhealthy
failures=$((failures + 1))
echo "$failures" > "$STATE_FILE"
log "⚠️  Health check failed (HTTP $http_code) — failure $failures/$MAX_FAILURES"

if [[ "$failures" -ge "$MAX_FAILURES" ]]; then
    log "🔄 Max failures reached ($MAX_FAILURES). Restarting $SERVICE_NAME..."

    # ── Kill any orphan process hogging the port ──
    orphan_pids=$(sudo lsof -ti :"$PORT" 2>/dev/null || true)
    if [[ -n "$orphan_pids" ]]; then
        log "🧹 Found orphan PIDs on port $PORT: $orphan_pids — killing..."
        echo "$orphan_pids" | xargs -r sudo kill -9 2>/dev/null || true
        sleep 1
    fi

    # ── Restart the service ──
    sudo systemctl restart "$SERVICE_NAME" 2>&1 | while read -r line; do log "  systemctl: $line"; done
    echo 0 > "$STATE_FILE"
    log "✅ Restart command issued"
fi
