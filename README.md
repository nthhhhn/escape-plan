# Escape Plan

Escape Plan is a server-authoritative, browser-based pursuit game built for the Netcentric Architecture term project.

The implementation includes the required two-player Classic mode, a FastAPI WebSocket server, a visible server dashboard, rematches, score reset, 10-second turns, persistent records, illustrated role-aware play, Ready and countdown flow, named AI opponents and Field Guide, Stage mode, power-ups, all original special modifiers plus optional tunnel relocation, Q-learning training, opt-in rollout coaching, reaction memes, and cloud deployment files.

For the offline 30,000-map dataset, actual Python generation/solver code, algorithm explanation, database restore instructions and animated showcase, see the [Map generation reference](map_lab/README.md). This dataset is separate from live multiplayer map selection.

## Stack

- React, TypeScript, Vite, Tailwind CSS, and shadcn-style UI components
- FastAPI, native WebSockets, and one authoritative Uvicorn worker
- SQLite for player scores, match history, map candidates, and training records
- Python process pools for AI search, simulations, and Q-learning
- Docker Compose and Caddy for a one-VM HTTPS/WSS deployment

## Run locally

Prerequisites: Python 3.12+, Node.js 22+, and npm.

```bash
./scripts/start.sh
```

Open `http://127.0.0.1:8000` on the server computer.

For everyday play on this Mac, double-click **Play Escape Plan.command**. It reuses an existing game server or starts the installed build, opens the game, and prints the address to share. Keep its Terminal window open when it starts the server; Control-C stops it. Run `./scripts/start.sh` after code/dependency updates to rebuild.

For two computers on the same network, open **http://escape-plan15.local:8000/** on both. This Mac publishes that hostname through macOS Bonjour/mDNS; no backend discovery service or IP lookup is required. Keep `PROFILE` as `local`: API and WebSocket connections follow the browser's hostname automatically.

The backend defaults to `escape-plan15.local` and reports its sharing address as `lan_url` in `/api/health`. The launcher supplies the Mac's current hostname through `ESCAPE_LAN_HOST`. This setting describes the address; Bonjour on the hosting Mac performs discovery. A different hosting computer must separately publish its own hostname.

The launcher reads the Mac's current LocalHostName, so it also works if the computer is renamed. The address stays the same across IP changes as long as that hostname stays the same. Keep the host awake and allow local network connections if macOS asks. Guest/campus Wi-Fi can block mDNS or communication between devices; the address is local to the network, not a public website.

The server dashboard and training controls require the token generated at `data/admin-token`. Do not share that token with players or commit it to source control.

## Demo flow

1. Open the Server page and unlock it with `data/admin-token` to show the concurrent client count and list.
2. Open the game from two computers and enter different nicknames.
3. Create a Classic room on one computer and join with the six-character room code on the second.
4. Demonstrate join messages, the Ready check, synchronized 3-second start countdown, randomized 5x5 board, warder-first 10-second turns, clickable legal destinations, Win/Lost result, scores, and two-player rematch agreement.
5. Show that the prior winner becomes warder in the rematch.
6. Use the Server page to reset games and scores.
7. Demonstrate Stage or Special mode with an AI policy, power-ups, all five modifiers, the rollout estimate, and the move coach.
8. Open AI Lab to show the measured Q-learning curve and saved policy details.
9. Open Field Guide to explain the named bot styles and the algorithms behind them.

## Test

```bash
./scripts/test.sh
```

The tests cover core movement, capture and escape, map connectivity, all supported board sizes, powers, hidden information, special-rule combinations, all five AI policies, Q-learning output, persistence, two-client WebSocket play, rematches, reset, reconnection, request deduplication, and cross-origin rejection.

## Q-learning

AI Lab can start a bounded training run after you enter the server admin token. A reproducible command is also available:

```bash
PYTHONPATH=backend .venv/bin/python -m escapeplan.train \
  --episodes 1000 \
  --size 5 \
  --powers off \
  --output data
```

This writes `data/q-model.json` and `data/training.json`. The graph displays actual held-out evaluations. It does not fabricate an improvement curve.

## Cloud deployment

The project is prepared for one AWS EC2 or GCP Compute Engine VM. The VM needs Docker, Docker Compose, a public IP, and a DNS record pointing to it.

```bash
cp .env.example .env
# Edit DOMAIN in .env to your real DNS name.
docker compose up --build -d
```

Caddy obtains HTTPS certificates and proxies HTTP and WebSocket traffic to the single game-server worker. Docker volumes preserve SQLite data, map candidates, the admin token, and trained policies.

Do not increase the Uvicorn worker count while live matches are stored in process memory. Horizontal scaling would require shared match state and coordinated timers.

Cloud resources are not provisioned automatically because an AWS or GCP account, billing configuration, DNS name, and provider choice are required.

## Important files

- `backend/escapeplan/engine.py`: shared deterministic rules engine
- `backend/escapeplan/server.py`: FastAPI app, rooms, WebSockets, timers, reconnect, and administration
- `backend/escapeplan/ai.py`: pathfinding, minimax, rollout analysis, and Q-learning
- `backend/escapeplan/storage.py`: SQLite persistence and 100-map candidate pools
- `frontend/src/App.tsx`: complete browser UI
- `frontend/src/experience.tsx`: illustrated characters, named bots, reactions, move targeting, and Field Guide
- `frontend/src/revision.css`: board-first visual redesign and responsive layouts
- `PROJECT_PLAN.md`: architecture, feature interactions, and requirement mapping
- `deploy/`: Docker and HTTPS reverse-proxy configuration

## Design boundaries

- Classic mode preserves the assignment rules and excludes rule-changing extras.
- Stage and Special modes reuse the same authoritative rules engine.
- Smoke and fake tunnels are filtered on the server. Hidden values never appear in an unauthorized player's payload.
- The displayed escape percentage is a bounded simulation estimate under random legal play, not a calibrated prediction of human behavior.
- Map validation and distance checks are balance heuristics. They ensure reachability but do not mathematically prove equal winning chances.
- Interrupted active matches are aborted after the reconnection window; completed records and trained policies persist.
