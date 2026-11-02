# Extra Features and Demonstration Plan

The instructor awards **2 points for an AI feature** and **1 point for a non-AI feature**. Our selected package uses only one AI feature and totals **10 points**.

## Selected Features (10 Points)

| # | Feature | Type | Points | What we will demonstrate |
|---:|---|---|---:|---|
| 1 | Q-learning opponent | AI | 2 | Open **AI Lab**, show the real training graph and saved policy, then play against the Q-learning bot. |
| 2 | Balanced random maps | Non-AI | 1 | Start two matches and show different valid maps with reachable exits and safe starting positions. |
| 3 | Role-specific power-ups | Non-AI | 1 | Use a Prisoner power and a Warder power, showing charges, effects, and server validation. |
| 4 | Stage progression | Non-AI | 1 | Show the nine-stage screen, increasing difficulty, saved progress, and stage skipping. |
| 5 | Multiple board sizes | Non-AI | 1 | Start stages using 5×5, 7×7, and 9×9 boards. |
| 6 | Obstacle shifting | Non-AI | 1 | Push an obstacle and show that an invalid shift is rejected if it blocks a required route. |
| 7 | Key and locked tunnel | Non-AI | 1 | Show that the Prisoner must collect the key before entering the real tunnel. |
| 8 | Fake tunnels | Non-AI | 1 | Show three tunnels while only the Prisoner knows which tunnel is real. |
| 9 | Decreasing turn timer | Non-AI | 1 | Show the turn limit decreasing from 10 seconds toward 5 seconds as rounds pass. |
|  | **Total** |  | **10** | |

## Recommended Demonstration Order

1. **Classic multiplayer:** connect two computers with a room code and show Ready, countdown, warder-first turns, capture or escape, score, and rematch.
2. **Q-learning:** open AI Lab, explain the training graph briefly, and start a match against the saved Q-learning policy.
3. **Stage mode:** show stage progression and the three board sizes.
4. **Special mode:** enable power-ups, obstacle shifting, key, fake tunnels, and the decreasing timer; demonstrate each mechanic in one match.
5. **Map balancing:** restart a match to show randomized valid terrain and explain that the server checks connectivity before accepting a map.

## More Non-AI Feature Choices

Choose any **eight accepted non-AI features** with Q-learning to reach 10 points. The first group is the easiest to demonstrate clearly.

### Strong Demonstration Choices

| Feature | What to show |
|---|---|
| Balanced random maps | Restart and compare two valid randomized maps. |
| Role-specific power-ups | Use Dig, Sprint, Smoke, Radar, or Roadblock. |
| Nine-stage progression | Show increasing difficulty and saved completion. |
| Three board sizes | Open 5×5, 7×7, and 9×9 stages. |
| Obstacle shifting | Push a wall; also show an unsafe push being rejected. |
| Key and locked tunnel | Try the tunnel before and after collecting the key. |
| Fake tunnels | Compare the Prisoner and Warder views of three tunnels. |
| Decreasing turn timer | Show the timer changing from 10 toward 5 seconds. |
| Shifting escape tunnel | Stay near an exit until it relocates. |
| Power-up pickups | Collect a pickup and show the new charge. |
| Special-mode presets | Open the five prepared rule configurations. |
| Custom special mode | Enable several compatible modifiers together. |

### Multiplayer and User Experience

| Feature | What to show |
|---|---|
| Room-code multiplayer | Create a room on one computer and join from another. |
| Ready system | Show that the match waits for both players. |
| Synchronized countdown | Show the shared `3 → 2 → 1 → GO!` start. |
| Online-client list | Connect or disconnect a browser and show the live update. |
| Activity messages | Show join, ready, action, and result messages. |
| Click and keyboard controls | Perform moves with both input methods. |
| Rematch agreement | Show that both human players must accept. |
| Automatic role switching | Show that the previous winner becomes Warder. |
| Reconnection support | Refresh or briefly disconnect, then resume the match. |
| Stage skipping | Skip a stage without awarding a false win. |
| Solo role selection | Choose whether the human plays Prisoner or Warder. |
| Reaction images | Trigger different reactions during gameplay. |
| Sound controls | Demonstrate game sounds and mute control. |
| Field Guide | Open the rules, roles, powers, and algorithm explanations. |
| Responsive interface | Open the game at phone or tablet width. |

### Server, Data, and Administration

| Feature | What to show |
|---|---|
| Server-authoritative rules | Attempt an illegal action and show server rejection. |
| Hidden-information protection | Show that the Warder payload does not reveal the real tunnel or hidden Prisoner. |
| Server-owned timer | Let a turn expire and show the server advancing it. |
| Persistent match history | Finish a match, restart the app, and show the stored result. |
| Persistent stage progress | Complete a stage and show that it remains unlocked. |
| Score tracking | Finish a match and show the winner receiving one point. |
| Admin dashboard | Show live clients, rooms, and recent match results. |
| Room reset | Reset one room while leaving other rooms active. |
| Global reset | Return all players to the lobby and clear session scores. |
| Admin disconnect control | Disconnect a selected client from the dashboard. |
| Duplicate-action protection | Submit the same action twice and show it is applied once. |
| Stale-action protection | Show that an action from an old turn is rejected. |

### Networking and Deployment

| Feature | What to show |
|---|---|
| Two-computer LAN play | Run the server on one computer and play from a second. |
| Local hostname connection | Join through the `.local` address without entering an IP. |
| Cloud deployment | Open the same game from the public GCP address. |
| Secure HTTPS/WSS | Show encrypted web and WebSocket connections. |
| Docker deployment | Explain that the client, server, proxy, and data run from containers. |
| Automated deployment | Show that a push to `main` runs tests and updates GCP. |
| Deployment security | Explain the pinned host key and restricted deployment key. |
| Health monitoring | Open `/api/health` and show the running service status. |

### Optional Technical Showcase

These are useful backups if the professor accepts engineering or research work as extra features:

| Feature | What to show |
|---|---|
| Automated test suite | Run the backend tests and frontend production build. |
| Map candidate database | Explain how validated maps are stored and selected. |
| Map analysis database | Show the separately generated 30,000 analyzed maps. |
| Animated map showcase | Filter maps and replay their proven demonstrations. |
| Map symmetry removal | Show that rotated or reflected duplicates are removed. |
| Reproducible map generation | Regenerate results using documented seeds and commands. |

## Suggested Sets

### Easiest 10-Point Set

Q-learning, balanced maps, power-ups, stage progression, board sizes, obstacle shifting, key, fake tunnels, and decreasing timer.

### Most Visual 10-Point Set

Q-learning, power-ups, stage progression, board sizes, obstacle shifting, key, fake tunnels, shifting tunnel, and reaction images.

### Most Technical 10-Point Set

Q-learning, server-authoritative rules, hidden-information protection, reconnection, persistent history, admin dashboard, LAN play, cloud deployment, and automated deployment.

## Short Explanation for the Professor

The browser client sends player actions through a WebSocket connection. The FastAPI server owns the game state, validates every move and special action, updates the timer and score, and sends the approved state back to both clients. This prevents either browser from changing the rules or accessing hidden information such as the real tunnel. Q-learning runs on the server as the single claimed AI feature; the other selected features are game modes and rule mechanics.
