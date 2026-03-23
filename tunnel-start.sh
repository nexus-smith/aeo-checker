#!/bin/bash
# AEO Checker tunnel: Python HTTP server + Cloudflare Quick Tunnel
# Managed by launchd (com.nexus.aeo-tunnel)

DEPLOY_DIR="/Users/jarvis/.openclaw/workspace/projects/aeo-checker/deploy-static"
PORT=8787
TUNNEL_URL_FILE="/tmp/aeo-tunnel-url.txt"

cd "$DEPLOY_DIR" || exit 1

# Start AEO server (static files + /api/check endpoint)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
/usr/local/bin/python3 "$SCRIPT_DIR/aeo-server.py" "$PORT" &
HTTP_PID=$!

# Give server a moment to bind
sleep 2

# Start cloudflared (foreground — launchd manages lifecycle)
# Capture the URL from stderr for reference
/usr/local/bin/cloudflared tunnel --url "http://localhost:$PORT" 2>&1 | tee >(grep -o 'https://[^ ]*\.trycloudflare\.com' | head -1 > "$TUNNEL_URL_FILE")

# If cloudflared exits, also kill the HTTP server
kill "$HTTP_PID" 2>/dev/null
