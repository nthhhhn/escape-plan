# Escape Plan: complete feature and architecture plan

Status: implemented locally; automated verification passes. Cloud provisioning awaits a chosen provider account and DNS name.
Updated: 2026-10-06.

## Agreed direction

- Keep every idea in `Extra Features.pdf`; the order below is a build sequence, not a feature cut.
- One implementation sequence, with no team work assignments.
- Frontend: React, Vite, TypeScript, Tailwind, and shadcn/ui.
- Backend: Python, FastAPI, Uvicorn, and native WebSockets.
- Storage: live matches in server memory; SQLite on persistent disk for durable records.
- Hosting: one AWS EC2 or GCP Compute Engine VM. Provider remains undecided.
- Keep the same application runnable over LAN and in the cloud.
- Proposed rules that fill gaps in the PDFs are explicitly identified below. No time estimate is committed before implementation is measured.

## One game, three entry points

| Entry point | Experience | Rules |
| --- | --- | --- |
| Classic PvP | Two humans play the assignment game | Exactly 5x5, 19 free cells, 5 obstacles, 1 tunnel, alternating 10-second turns, warder first. No rule-changing modifiers. |
| Stage | Solo player advances through maps against AI | Stage selects map, size, opponent, and difficulty. Sizes 5x5, 7x7, and 9x9. Enhanced rules can be selected for an additional challenge. |
| Special | Human or AI opponent with selected modifiers | Five named presets plus Custom, where all five modifiers and power-ups can be combined. |

Modes are presets over one rules engine. The board UI, move validation, timer, scoring, rematch, and networking are shared. Map balancing and optional analysis/meme overlays are available across entry points. Power-ups are available in enhanced PvP, Stage, and Special; the Classic preset remains exact for grading.

## Full extra-feature coverage

| Team idea | Place in the game | Implementation |
| --- | --- | --- |
| Solo AI opponent | Stage and Special | Bot submits the same actions as a human; either role is supported. |
| Easy difficulty | Opponent settings | Random legal actions. |
| BFS and A* | Medium difficulty | Selectable pathfinding policies; warder chases, prisoner targets key/exit while considering immediate capture risk. |
| Minimax with alpha-beta pruning | Hard difficulty | Iterative deepening targeting 4-6 plies (individual player actions), with a computation deadline. |
| Q-learning | Selectable trained opponent and training screen | Real training, saved policy, held-out evaluation, and a visible learning graph. |
| Live win-probability bar | Optional match overlay | Target 200 bounded rollouts per position, showing simulation estimates and unresolved outcomes. |
| Move coach | Optional match overlay | Compare estimates before/after a move using the same perspective and evaluation configuration. |
| Pop-up memes and sound effects | Coach feedback | Local, predefined assets selected by feedback category; mute and reduced-animation controls. |
| Map balancer with 100 maps | Shared map service | Maintain 100 validated candidates per supported size, randomly choose a candidate and legal starting pair, and replenish used candidates. |
| BFS no-deadlock check | Shared rules engine | Validate connectivity and objective reachability at generation and after terrain changes. |
| Warder not too close to tunnel | Map/spawn selection | Configurable minimum start distance to every tunnel; initial proposed minimum is 3 orthogonal steps. |
| Dig | Power-up system | Prisoner removes one adjacent removable obstacle. |
| Sprint | Power-up system | Prisoner traverses up to two consecutive orthogonal cells in one action. |
| Smoke bomb | Power-up system | Conceals prisoner position during the next warder turn. |
| Radar | Power-up system | Reveals prisoner position and overrides smoke for the stated duration. |
| Roadblock | Power-up system | Warder places one temporary obstacle, subject to reachability validation. |
| Map pickups or limited charges | Power-up settings | Support Limited, Pickups, and Both presets. |
| Stage progression | Stage screen | Ordered stages with increasing difficulty and size; save progress. |
| 5x5, 7x7, 9x9 maps | Stage and Special settings | 5, 10, and 16 obstacles respectively; objective cells occupy remaining non-obstacle cells. |
| Obstacle shifting | Special preset / modifier | Replace a normal move with pushing an adjacent obstacle one cell. |
| Key and tunnel | Special preset / modifier | Collect the key before the real tunnel allows escape. |
| Fake tunnels | Special preset / modifier | Three tunnels, one real; only the prisoner knows the real tunnel during play. |
| Shrinking prison | Special preset / modifier | Every three complete rounds, collapse a valid free cell into an obstacle. |
| Shrinking timer | Special preset / modifier | Reduce the turn allowance from 10 to 5 seconds as rounds advance. |

Map selection is performed by the server each match. Classic always uses random valid 5x5 candidates and randomized legal spawns, never an authored stage map. Stored candidate layouts are seeds/templates; selections and starting positions remain randomized. Stage retains a consistent map for a retry.

Connectivity is necessary but does not prove strategic fairness or that play cannot repeat. The balancer also measures spawn distances and evaluates candidate outcomes with both roles. Describe these as balance heuristics and measured results, not a fairness guarantee. Retain the candidate generation seed and balance metrics for inspection.

## Original assignment behavior retained

- Connect automatically with the server address and port defined in source configuration; no connection form.
- Broadcast the online-client list on connect/disconnect. Track connected clients even before nickname submission; identify pending clients by generated IDs.
- Welcome each player by nickname and display both players' names, roles, and scores.
- Initially assign roles randomly and place characters on distinct free cells.
- Warder starts; moves are one orthogonal cell in Classic; obstacles are impassable; warder cannot enter the tunnel.
- Prisoner reaching the tunnel wins; characters meeting causes capture. Award the winner one point exactly once.
- Display Win/Lost, both scores, and rematch controls.
- Both humans must agree to rematch. Previous winner becomes warder and starts; regenerate the map and positions. In solo play the AI accepts automatically.
- Admin dashboard displays connected-client count/list and a reset button. Admin connections are distinguished from game-client connections.
- Reset cancels active matches, timers, pending AI results, and rematch requests, zeros displayed session scores, and returns players to the lobby. Historical records can remain marked with their prior session ID.
- Preserve the LAN demonstration with one computer running server and client, and a second running the client. Cloud deployment uses the same code and provides the professor's additional demonstration.

## Proposed interaction rules

These decisions resolve missing details and make combinations implementable. They are design proposals, not requirements quoted from the PDFs.

### Actions and timing

- A turn accepts exactly one action: move, use a power, or shift an obstacle. Invalid input does not consume the turn or restart its timer.
- On timeout, pass the turn. A pass is also legal when there are no other legal actions.
- A round consists of one warder and one prisoner turn, including passed turns.
- Shrinking timer: `max(5, 10 - floor(completed_rounds / 3))` seconds, set at the start of the next turn. Classic always stays at 10 seconds.
- Human matches use an explicit Ready check. After both players are ready, roles and the board appear behind a synchronized `3 → 2 → 1 → GO!`; the warder's first turn begins only after GO.
- Server deadlines are authoritative. Every action includes match ID, turn ID, and request ID; stale or repeated actions cannot change a newer turn.
- On disconnect, pause for up to 20 seconds; reconnect with a server-issued session token. Resume the stored remaining time; otherwise abort without a point. Starting a new process aborts interrupted matches; crash recovery is not implied by persistence.

### Powers

- Limited preset starts with one charge of each role's powers. Pickups replenish the matching role's charge. Both is also supported. Display charges and expiry explicitly.
- Dig targets an adjacent permanent obstacle, including a collapsed cell. It cannot remove objectives or a temporary roadblock.
- Sprint chooses a direction and distance of one or two. Simulate its traversed substeps before committing, resolving pickup, capture, and escape after each step. Stop on a terminal event; cells beyond that terminal step are not traversed or validated. Reject an invalid nonterminal path without partially moving. It cannot jump over an obstacle or warder.
- Smoke consumes the prisoner's action. The prisoner stays hidden through the next warder turn, the prisoner's following action, and the warder turn after that, then reappears before their next action. It changes visibility, not collisions; Radar overrides it.
- Radar consumes the warder's action and reveals the prisoner immediately through the end of the warder's following turn, overriding smoke during that interval. It does not reveal which tunnel is real.
- Roadblock targets an adjacent free, empty cell, lasts until two complete rounds have elapsed, and cannot cover an objective or pickup. Reject placement that breaks required reachability.
- Pickup layout is generated only when pickups are enabled. Keep pickups off spawn cells and objectives; define a fixed initial budget per map size to avoid unbounded placement.

### Special-mode combinations

- Obstacle shift: a player adjacent to a permanent obstacle can push it one cell directly away, staying in place. The destination must be empty floor without objectives or pickups. Temporary roadblocks cannot be shifted. Validate the resulting board before consuming the turn.
- Key: prisoner must collect it before escape. Warder may traverse its cell without collecting it; it cannot be destroyed or covered. A locked tunnel is impassable to the prisoner until key collection.
- Fake tunnels: all three tunnel cells are forbidden to the warder. Once unlocked, the prisoner may enter a decoy but does not win. The true identity is private to the prisoner. With Key enabled, the key unlocks all tunnel entries but only the real one wins.
- Connectivity checks use each role's actual movement permissions. With Key enabled, require a route to the key before unlocking, then a route to the real exit. For the warder, test connectivity without any tunnel cells.
- Shrinking prison never collapses a character, tunnel, uncollected key, or pickup. It rejects collapses that break the reachability rules. If no legal cell exists, skip that collapse.
- Optional Shifting Escape Tunnel (Special only): remaining within two walking steps of a tunnel for three consecutive warder turns relocates it to a validated cell. Warn after two turns, reset pressure when the warder leaves, and apply a three-round cooldown after a successful shift. Real and decoy tunnels follow the same visible rule so the modifier does not disclose the real exit.
- Collapsing cells alone does not guarantee termination. For Shrinking Prison, add an explicit 60-round containment limit: if the prisoner has not escaped, the warder wins. Show this limit before play. A terminal move on the final round is resolved before the containment check.
- Power-ups, map changes, and all special rules are available to the shared simulator as well as live matches; AI must not use a simplified game with different legal actions.

### Resolution order

1. Authenticate the session; verify phase, match/turn/request IDs, deadline, and action payload.
2. Validate the complete action against the current ruleset and private authoritative state.
3. Apply the action, processing movement substeps and pickups; check capture/escape immediately.
4. If still running, expire effects whose duration ends with this action; increment completed-round count when appropriate.
5. At a round boundary, apply valid scheduled terrain changes and check the special containment limit.
6. If still running, select the next player and set the next deadline.
7. Increment state version, persist required records, and broadcast each recipient's permitted view.
8. Submit bounded analysis for that version; discard obsolete results. Award a terminal result once, using a unique result record.

## Architecture

```text
Browser clients and protected admin UI
        | HTTPS / native secure WebSockets
One cloud VM or LAN host
        | reverse proxy + built frontend
        | FastAPI / Uvicorn: ONE authoritative application process
        |   connections + rooms + match controller
        |   rules engine + personalized state views
        |   timers + version checks
        |   SQLite repository / serialized writes
        |
        + bounded Python process pool
            AI search + rollouts + Q-learning jobs
            receives snapshots; never mutates live matches
```

Use one application process while matches are in memory. Separate CPU computation processes do not own sockets, timers, or live state. This is a single application with helper processes; it does not require separate deployed AI services or a message broker.

Use a pure Python game engine with `legal_actions`, `apply_action`, `is_terminal`, `generate_map`, and `player_observation` operations. Given the same state, action, and random seed, live matches and simulations must agree. WebSocket and database code stay outside those functions.

Serialize mutations per room; never await a long AI task while holding the room lock. AI jobs use a match ID, state version, turn ID, and deadline. A returned move is revalidated on the main process. Search jobs check a cooperative time budget and return the best legal move found so far. Executor timeouts alone do not terminate running work; avoid a backlog of stale tasks.

Training is a bounded batch/offline job with checkpoints. Prioritize live bot moves over analysis and training. Precompute the trained model and training chart for the demonstration while retaining an actual reproducible training command.

## Hidden information changes the networking plan

The earlier idea of broadcasting the same complete snapshot to both clients is insufficient once Smoke and Fake Tunnels exist.

- Keep one full private state on the server.
- Produce a separate view for each player. Omit hidden coordinates and real-tunnel identity from unauthorized JSON, events, logs returned to clients, and reconnect snapshots. Hiding a DOM element is insufficient.
- AI receives only the information its role may know. For hidden-information search, sample states consistent with its observation/history instead of giving it the true private state.
- The live analysis bar and coach must use the recipient's information too, or they can reveal secrets indirectly. Full-information review can appear after the match.
- Server-assigned player IDs and resume tokens establish identity. Nicknames and client-supplied role fields are not authorization.

## AI details and honest presentation

- Easy, BFS, A*, and minimax are algorithms, not trained models. Implement each policy behind the same bot interface.
- Minimax targets 4-6 plies through iterative deepening. Larger boards and modifier combinations can exceed the budget; report the actual completed depth rather than promising six for every turn.
- Q-learning is a genuine additional trained bot, not a renamed minimax policy. Encode legal actions and relevant features such as role, relative targets, local obstacles, inventory, effects, and rule configuration. Mask illegal actions. A compact feature state trades away information; measure its limitations rather than claiming the entire randomized-map problem is small.
- Record training seed, ruleset, map-size coverage, hyperparameters, episode count, and checkpoint. Evaluate on held-out seeds against a fixed baseline for both roles. Plot measured reward/win rate and sample counts. If results do not improve, show that result and continue training; never fabricate a random-to-smart curve.
- Stage supports selecting the Q-learning policy. Show its trained configuration coverage; evaluate unfamiliar rule combinations separately. Use an explicitly identified legal-action fallback if a state/action has no learned value.
- Rollouts: target 200 simulations per analyzed position using a documented policy, seeded samples, and a finite horizon. Respect all modifiers. Record both wins and unresolved simulations. A result such as 130 prisoner wins out of 200 is a 65% simulated prisoner-win frequency under that policy/horizon, not a calibrated human win probability.
- If the budget prevents 200 runs, show the actual count or a pending state. Do not block the turn while analysis runs.
- Coach: compare the same player's perspective before/after a move using paired random seeds where possible. Use categories such as improved, worsened, and uncertain. Keep both evaluations within the information available at the action time so newly revealed secrets do not falsely become move quality.
- Memes and sounds are selected locally from a small bundled catalog. No paid generation API is necessary during gameplay.

## State and persistence

In-memory match state includes board, players, roles, positions, phase, turn/deadline, round, session scores, rule configuration, inventory, pickups, key state, tunnel identities, temporary terrain, visibility effects, stage, RNG seed, and version. Fields may be private.

SQLite tables (initial proposal):

| Table | Purpose |
| --- | --- |
| player_sessions | Generated ID, nickname, token hash, session score, reset/session group. |
| matches | Seed, ruleset JSON, players, outcome, timestamps, abort/reset reason. |
| match_actions | Ordered validated actions and version; assists debugging and deterministic verification. |
| map_candidates | Size, seed/layout, validation version, balance metrics. |
| stage_progress | Player session, stage, completion and best result. |
| training_runs | Configuration, seed, checkpoint reference, status, evaluation coverage. |
| training_metrics | Episode/evaluation step, rewards, wins, losses, unresolved counts. |

Keep model checkpoints as files in a persistent data directory and store references in SQLite. No full account-registration system is required. SQLite access is server-side, serialized, and transactional. A schema-version mechanism supports changes without assuming SQLite-to-MySQL migration is automatic.

## Network contract

Native WebSocket endpoint: `/ws`. REST serves health, stage metadata, training summaries, and protected admin functions. WebSocket is responsible for actual live gameplay.

Client envelope: `{type, request_id, match_id?, turn_id?, payload}`.
Server envelope: `{type, request_id?, match_id?, state_version?, server_time, payload}`.

Client events: `identify`, `create_room`, `join_room`, `ready`, `action`, `rematch`, `resume`, `leave_room`, and `ping`.
Server events: `welcome`, `online_clients`, `room_state`, `match_started`, `state_update`, `action_result`, `analysis_update`, `match_finished`, `paused`, `reset`, `error`, and `pong`.

- `action` represents move, power use, or obstacle shift with validated parameters.
- Acknowledge accepted/rejected actions and deduplicate by request ID. A repeated request returns its prior result without applying again.
- Reconnection requests a fresh personalized snapshot. Never blindly replay buffered moves into a new turn.
- Clients estimate clock offset for the display; server monotonic time enforces deadlines.
- Room configuration is locked when a match starts; players see the selected rules before readying.

## Frontend screens

1. Nickname and connection status.
2. Lobby with online clients, room creation/join, and Classic/Stage/Special entry points.
3. Stage selection with progress, size, and opponent selection.
4. Special setup with five presets, Custom combinations, and power-up settings.
5. Shared game screen: board, illustrated role-aware characters, directly clickable legal destinations, names/roles/scores, timer, inventory, objective status, modifiers, always-visible reactions, and optional analysis/coach.
6. Field Guide with named bot characters, fictional backgrounds, role behavior, counterplay, and layered algorithm explanations.
7. Results and rematch agreement.
8. AI training/evaluation screen with real metrics, personality configuration, role-separated evaluation, and saved policy details.
9. Protected server dashboard: online count/list, active matches, reset, and job status.

## Deployment

- Build the frontend once and serve it with the backend behind one HTTPS origin; proxy WebSocket upgrades to FastAPI.
- One Uvicorn application worker; a small bounded AI process pool sized after measuring the chosen VM.
- SQLite and checkpoints live on persistent disk, outside disposable build/container layers.
- Provide LAN/cloud source configuration profiles containing the server address and port, matching the assignment's source-configuration requirement. Secrets stay out of client bundles and source control.
- In cloud mode, restrict admin actions with server-side authentication. On LAN, local-only administration is acceptable. Ordinary game clients cannot reset scores or launch training jobs.
- Bind the application internally behind the proxy in cloud deployment. The public endpoint uses HTTPS/WSS.
- Preserve source code and startup scripts for the local two-computer demonstration. Cloud deployment is additional to that written topology unless the professor explicitly substitutes it.
- Cloud provisioning and publishing require a selected provider/account; this plan does not claim resources have been provisioned.

## Single build sequence

Every feature remains in the completion target.

1. Scaffold frontend/backend and establish a real two-client WebSocket connection, identity, online list, and server dashboard skeleton.
2. Build the pure rules engine, map validation, Classic gameplay, authoritative timer, scoring, rematch, reset, and reconnect behavior.
3. Add the generic rules configuration, action model, effect lifetimes, and per-player state filtering before implementing hidden-information features.
4. Implement Stage, all three sizes, 100-candidate map pools/balancing, Easy/BFS/A*/Hard bots, and stage persistence.
5. Implement all five powers, Limited/Pickups/Both acquisition, all five special presets, and Custom combinations using the same engine.
6. Add the Q-learning training/evaluation pipeline and selectable saved policy; train and record metrics on declared configurations.
7. Add the 200-rollout analysis service, probability overlay, move coach, meme/sound feedback, and training chart.
8. Complete UI styling and deploy the same application to the selected cloud VM. Verify play from two separate networks as well as the required LAN setup.

Prepare deployment scripts early and smoke-test a cloud instance after the connection milestone once an account is available; the final milestone verifies the complete feature set.

## Completion evidence

- Every original assignment requirement demonstrated in Classic with two physical computers.
- Every row of the extra-feature coverage table has a working UI path and backend behavior; no decorative-only controls.
- Rule tests for moves, role restrictions, timers, capture/escape, scoring once, rematch roles, and reset invalidating pending work.
- Seeded map checks for exact cell counts, valid spawns, role-specific connectivity, and objective reachability across all sizes.
- Targeted combination tests: key + fake tunnels; smoke + radar; sprint + key/pickup/capture; roadblock/shift/collapse reachability; shrinking timer + timeout; reset/disconnect during bot computation.
- A complete match with every modifier enabled, using the same rules in live execution and simulation.
- Privacy checks on both actual WebSocket payloads and AI observations, including analysis results and reconnection.
- Q-learning metrics generated from actual runs, held-out evaluation, and a saved policy that executes legal moves.
- Performance measurements on the chosen VM: responsive sockets/timers during bot search, 200-rollout jobs, and training; show actual achieved depth/sample counts.
- SQLite records and model checkpoints survive application restart. Interrupted active matches are explicitly aborted rather than silently resumed incorrectly.
- Test cloud HTTPS/WSS connections from different networks and prevent unauthenticated reset/training actions.

## Sources

- Local assignment: `EscapePlan-1525379-17884898599441.pdf` (all three pages).
- Team feature list: `Extra Features.pdf` (both pages).
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI workers: https://fastapi.tiangolo.com/deployment/server-workers/
- Python process executors: https://docs.python.org/3/library/concurrent.futures.html
- Python SQLite interface: https://docs.python.org/3/library/sqlite3.html

Rules labeled proposed are design decisions made to connect the supplied ideas; they are not represented as instructor requirements.
