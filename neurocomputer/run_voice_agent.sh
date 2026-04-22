#!/bin/bash
# Run the Infinity Voice Agent
# This connects to LiveKit Cloud and handles voice interactions

# Resolve project root no matter where script is run from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
cd "$ROOT_DIR"

# Load env
ENV_FILE="$ROOT_DIR/infinity_mobile/.env"
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +o allexport
fi

# Check credentials
if [ -z "$LIVEKIT_URL" ] || [ -z "$LIVEKIT_API_KEY" ]; then
    echo "ERROR: Missing LiveKit credentials!"
    echo "Please edit infinity_mobile/.env with your LiveKit Cloud credentials"
    echo ""
    echo "Get credentials from: https://cloud.livekit.io"
    exit 1
fi

echo "Starting Infinity Voice Agent..."
echo "LiveKit URL: $LIVEKIT_URL"
echo ""
echo "Test with: https://agents-playground.livekit.io"
echo ""

"$ROOT_DIR/venv/bin/python" infinity_mobile/server/voice_agent.py dev
