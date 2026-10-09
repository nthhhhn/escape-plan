# Escape Plan handoff

Updated: 2026-10-09 (Asia/Bangkok)

## Current status

The game source, launcher, documentation and deployment files are on GitHub at `nthhhhn/escape-plan`, branch `main`, initial commit `0bcd309`. The working tree was clean when this handoff was prepared. The local game uses FastAPI, WebSockets, React and SQLite. Previous backend validation passed 33 tests.

The current task is a separate, offline map-analysis database and animated HTML showcase. **No map solver, new database, map pool or showcase has been created yet.** The first attempt to add `map_lab/solver.py` was not executed: automatic approval review could not complete because the account usage limit had been reached. This was an approval-system failure, not a finding that the code was unsafe.

The user asks to push progress and next-step notes to GitHub as work proceeds so a teammate can continue. Commit meaningful checkpoints together with updates to this file. Do not claim a push succeeded until Git confirms it. Do not include credentials, admin tokens, local player databases or unrelated changes.

## Latest user requirements

- Generate a large persistent pool of interesting maps, ordered from easy to hard, for the supported board sizes 5x5, 7x7 and 9x9.
- Difficulty must consider how difficult a human would find the winning strategy, not merely move count or simulated win rate.
- Produce a standalone HTML showcase with 30 selected maps per size (90 total), ordered by estimated difficulty and with looping animated winning demonstrations.
- Keep a much larger collection in a real SQLite database. The final pool size is not agreed; exhaustive enumeration is not feasible. Pick and disclose a finite generation budget, record actual counts and runtime, and make generation resumable.
- Keep the offline experiment separate from the running multiplayer game. Do not replace production map selection or change gameplay rules without discussing results.

## Research and findings

Current `engine.generate()` randomly places terrain and spawns, filters using BFS connectivity, checks tunnel approaches and starting distances. `Store.pick_map()` fills a pool to 100 per size/modifier/power configuration, randomly selects one and removes it. It does not rank maps by fairness or simulate role outcomes.

Standard Stage maps additionally require `safe_escape_route()`. This proves a sufficient prisoner escape route on static terrain but may over-select simple races; it is not a competitive fairness measure.

Fairness must be evaluated for a complete scenario: layout, objectives, both spawns, turn order, enabled rules and information. A 50% average can hide maps with trivial predetermined outcomes. Proven outcomes, estimated human difficulty, and human enjoyment must be reported separately.

Sources consulted for methodology (not installed or copied):

- https://github.com/GamesCrafters/GamesmanClassic — exact game analysis, including loops.
- https://github.com/GamesCrafters/GamesCraftersUWAPI — outcome and remoteness representation.
- https://github.com/tannousmarc/scotland-yard-AI — pursuit evaluation using routes and dangerous states.
- https://github.com/google-deepmind/open_spiel — adversarial search and policy evaluation.
- https://github.com/amidos2006/pcg_benchmark — quality, diversity and controllability as separate measurements.

## Proposed first experiment

1. Analyse fixed terrain, one visible tunnel, no powers, keys or modifiers. Use the existing obstacle counts: 5, 10 and 16. The warder moves first and cannot enter the tunnel. Document that results do not apply to Special-mode combinations.
2. Build a state graph from `(warder_position, prisoner_position, side_to_move)`. Mark terminal capture and escape states. Use retrograde propagation with memoized outcomes rather than naive recursive enumeration of move sequences.
3. Include waiting because the real engine allows timeout passes. Label such demonstration actions explicitly as waiting for timeout; normal movement-pass controls do not permit arbitrary passing. Excluding waiting would solve a different game.
4. Propagate forced wins and optimal remoteness. A winning player chooses the shortest forced finish; a losing opponent delays it as long as possible. Remaining states represent indefinite avoidance under these exact rules, not a simulation cutoff. Validate cycle handling carefully.
5. Provisional difficulty features: share of legal choices that lose the forced win; misleading choices preferred by a short-route heuristic; limited-lookahead depth needed to retain the win; counterintuitive detours; and a small contribution from sustained execution length. Also record dead ends, junctions, independent routes/bottlenecks and cycle structure where implemented. Distinguish implemented features from aspirations.
6. Difficulty is a heuristic for discovering/executing the proven winner's strategy, not a measured human success probability. Rank within each size and winning role; do not present relative percentiles as absolute cross-size difficulty. Calibrate with people later.
7. Reject invalid/trivial demonstrations, record rejection reasons, and select a diverse collection rather than only extreme metric scores. Deduplicate rotations/reflections. Tag the proven winner; a forced-win puzzle is not evidence of equal competitive chances.
8. Store scenario, seed, rules/solver version, outcome, metrics, difficulty, animation trace and validation result in an isolated SQLite file such as `data/map-lab.sqlite3`. Existing live database `data/escapeplan.sqlite3` must remain untouched.
9. Embed 30 representative examples per size into a standalone HTML file. Provide size selection, easy-to-hard order, proven winner, explanations, play/pause, next/previous step, speed control and looping replay after the terminal result. Distinguish replay looping from a stalemate.

## Immediate next steps

- Resolve the account approval/usage block before any further edits or network pushes that need approval; do not bypass it.
- Implement and test the exact solver in new isolated `map_lab/` files. The previously attempted patch did not land and should not be treated as tested code.
- Verify terminal precedence, all legal transitions, waiting, cycles and remoteness; cross-check small boards with an independent reference method.
- Replay every selected proof trace through the real `engine.apply_action()` (including `timeout=True` for waits). Assert the advertised winner and no illegal move.
- Benchmark a small batch before choosing a large pool target. Log candidate/accepted/rejected counts and elapsed time. A prior estimate of seconds to minutes was not a benchmark.
- Generate a resumable pool, then produce and browser-check the 90-map showcase on desktop and mobile.
- Commit code, method documentation and a shareable showcase or compact export. The ignored `data/` directory is not a GitHub handoff; provide reproducible commands and, if appropriate, a deliberately selected analysis-only export without player data.
- Update this log and push each meaningful milestone. Never force-push over teammates' work.

## Environment notes

- Actual local project: `/Users/nthn/Documents/Netcentric_Architecture/Term_Project`.
- App workspace permissions still refer to the old path containing spaces. Some writes, local-network checks and builds consequently require approval.
- GitHub remote: `https://github.com/nthhhhn/escape-plan.git`.
- `escape-plan15.local` is published by this Mac's Bonjour hostname configuration. The backend setting only reports a sharing URL; cloning the repository does not configure another computer's mDNS.
- Do not restart the live game server for this offline experiment.
