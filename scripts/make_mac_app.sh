#!/bin/bash
# Make a double-click Mac app that starts the live dashboard (if it isn't running) and opens it in the browser.
# Usage:  bash scripts/make_mac_app.sh            -> creates "Hormuz Dashboard.app" on the Desktop
#         bash scripts/make_mac_app.sh /Applications
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$HOME/Desktop}"
APP="$DEST/Hormuz Dashboard.app"
PORT=8771
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/launcher.applescript" <<EOF
set root to "$ROOT"
do shell script "cd " & quoted form of root & " && mkdir -p logs && if ! /usr/sbin/lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then nohup .venv/bin/streamlit run app/dashboard.py --server.port $PORT --server.headless true --theme.base light > logs/dashboard.log 2>&1 & fi; i=0; while [ \$i -lt 60 ]; do /usr/bin/curl -s -o /dev/null http://localhost:$PORT/_stcore/health && break; sleep 0.5; i=\$((i+1)); done"
open location "http://localhost:$PORT"
EOF

rm -rf "$APP"
osacompile -o "$APP" "$TMP/launcher.applescript"
echo "Created: $APP"
