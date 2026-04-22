#!/bin/bash
# =============================================================================
# Update LiveKit config with tunnel domains
# =============================================================================
# Run this AFTER setting up Playit and getting your tunnel domains

# Load .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

LIVEKIT_CONFIG="${LIVEKIT_CONFIG:-/home/ubuntu/infinity_prod/livekit.yaml}"
BACKUP_CONFIG="${LIVEKIT_CONFIG}.backup.$(date +%s)"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           Update LiveKit Config with Tunnel Domains                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Get current config
if [[ -f "$LIVEKIT_CONFIG" ]]; then
    echo "Current LiveKit config:"
    echo "─────────────────────────────────"
    cat "$LIVEKIT_CONFIG"
    echo "─────────────────────────────────"
    echo ""
fi

# Get tunnel domains
read -p "Enter your Playit TCP tunnel domain (LiveKit API, e.g., abc123.playit.gg): " PLAYIT_TCP_DOMAIN
read -p "Enter your Playit TURN domain (UDP 3478, e.g., def456.playit.gg): " PLAYIT_TURN_DOMAIN
read -p "Enter your Playit Media domain (UDP 50000-60000, e.g., ghi789.playit.gg): " PLAYIT_MEDIA_DOMAIN

# Get LiveKit keys from env or prompt
LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-}"
if [[ -z "$LIVEKIT_API_KEY" ]]; then
    read -p "Enter LiveKit API Key: " LIVEKIT_API_KEY
fi

LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET:-}"
if [[ -z "$LIVEKIT_API_SECRET" ]]; then
    read -p "Enter LiveKit API Secret: " LIVEKIT_API_SECRET
fi

# Get TURN credentials from env or use defaults
TURN_USERNAME="${LIVEKIT_TURN_USERNAME:-infinity}"
TURN_PASSWORD="${LIVEKIT_TURN_PASSWORD:-}"
if [[ -z "$TURN_PASSWORD" ]]; then
    read -p "Enter TURN password (leave empty to generate random): " TURN_PASSWORD
    if [[ -z "$TURN_PASSWORD" ]]; then
        TURN_PASSWORD=$(openssl rand -base64 24)
        echo "Generated random TURN password: $TURN_PASSWORD"
    fi
fi

if [[ -z "$PLAYIT_TCP_DOMAIN" ]]; then
    echo "ERROR: Playit TCP domain is required."
    exit 1
fi

if [[ -z "$LIVEKIT_API_KEY" ]] || [[ -z "$LIVEKIT_API_SECRET" ]]; then
    echo "ERROR: LiveKit API Key and Secret are required."
    exit 1
fi

# Backup existing config
if [[ -f "$LIVEKIT_CONFIG" ]]; then
    cp "$LIVEKIT_CONFIG" "$BACKUP_CONFIG"
    echo "Backup saved to: $BACKUP_CONFIG"
fi

# Ensure directory exists
mkdir -p "$(dirname "$LIVEKIT_CONFIG")"

# Update config
cat > "$LIVEKIT_CONFIG" << EOF
# LiveKit Server Configuration
# Updated for Playit.gg tunnel
port: 7880
rtc:
  udp_port:
    start: 50000
    end: 60000
  use_external_ip: true
  port_range_start: 50000
  port_range_end: 60000
  # Playit tunnel domain for external connections
  external_ip: "${PLAYIT_TCP_DOMAIN}"
  turn:
    enabled: true
    host: "${PLAYIT_TURN_DOMAIN}"
    port: 3478
    username: "${TURN_USERNAME}"
    password: "${TURN_PASSWORD}"
keys:
  ${LIVEKIT_API_KEY}: "${LIVEKIT_API_SECRET}"
EOF

echo ""
echo "LiveKit config updated!"
echo ""
echo "NEW CONFIG:"
echo "─────────────────────────────────"
cat "$LIVEKIT_CONFIG"
echo "─────────────────────────────────"
echo ""
echo "IMPORTANT: Restart LiveKit for changes to take effect:"
echo "  sudo systemctl restart livekit"
echo ""
echo "Or if running manually:"
echo "  pkill -f livekit-server"
echo "  livekit-server --config $LIVEKIT_CONFIG --node-ip ${PLAYIT_TCP_DOMAIN}"
echo ""
echo "Then update your .env file with:"
echo "  export LIVEKIT_URL=\"wss://${PLAYIT_TCP_DOMAIN}\""
echo ""
