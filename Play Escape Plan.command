#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

game_hostname=$(/usr/sbin/scutil --get LocalHostName)
export ESCAPE_LAN_HOST="${game_hostname}.local"
game_url="http://${game_hostname}.local:8000"
printf '\nEscape Plan\nShare this address on the same network:\n  %s\n\nKeep this Mac awake while playing.\n\n' "$game_url"

if /usr/bin/curl --noproxy '*' --silent --max-time 2 http://127.0.0.1:8000/ | /usr/bin/grep -q '<title>Escape Plan'; then
  printf 'The game server is already running. Opening the game.\n'
  /usr/bin/open "$game_url"
  exit 0
fi

if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
  printf 'First-time setup is needed. Run ./scripts/start.sh in this folder, then use this launcher.\n'
  read -r -p 'Press Return to close.'
  exit 1
fi

printf 'Starting the server. Keep this window open; press Control-C to stop it.\n'
# The existing build uses the browser hostname for API and WebSocket traffic.
.venv/bin/python -m uvicorn escapeplan.server:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 16384 &
game_pid=$!
trap 'kill "$game_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT TERM
for attempt in {1..30}; do
  if ! kill -0 "$game_pid" 2>/dev/null; then
    printf 'The server could not start. See the error above.\n'
    read -r -p 'Press Return to close.'
    exit 1
  fi
  if /usr/bin/curl --noproxy '*' --silent --max-time 1 http://127.0.0.1:8000/ | /usr/bin/grep -q '<title>Escape Plan'; then
    /usr/bin/open "$game_url"
    break
  fi
  sleep 1
done
wait "$game_pid"
