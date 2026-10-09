# Escape Plan handoff

Updated: 2026-10-09 (Asia/Bangkok), solver checkpoint

## Current status

The game source, launcher, documentation and deployment files are on GitHub at `nthhhhn/escape-plan`, branch `main`, initial commit `0bcd309`. The working tree was clean when this handoff was prepared. The local game uses FastAPI, WebSockets, React and SQLite. Previous backend validation passed 33 tests.

The current task is a separate, offline map-analysis database and animated HTML showcase. The initial approval/usage interruption has cleared. `map_lab/solver.py`, `map_lab/generate.py`, and `map_lab/test_solver.py` now exist. Four tests pass, including independent engine-based fixed-point analysis for all 256 fixed-exit 3x3 wall patterns, larger-board transitions and proof replays, symmetry deduplication, and independent-route counts. Every generated layout also passes all-state outcome/remoteness checks and its demonstration is replayed through the real engine.

A resumable run is generating 10,000 accepted layouts for each supported size (30,000 total) into **`data/map-lab-pool.sqlite3`**. The pilot `data/map-lab.sqlite3` is an earlier spawn-sampling experiment, not the final pool. Final HTML is not built yet. Resume with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --target 10000 --no-export`. Do not run two writers concurrently. A 100-layout pilot took approximately 0.21s / 0.73s / 1.99s for 5x5 / 7x7 / 9x9 on this host; final run timings will be exported.

The generator samples up to three eligible starting pairs on each layout and alternates selecting the easiest/median/hardest by its provisional score. It preferentially seeks the underrepresented winning role when possible. Every map is decisive with an optimal finish of 4–80 plies. These are exact static-rule puzzles, not proven competitively balanced or human-validated maps. Difficulty is ranked within board size and winning role; saved scores are proxies, not human success probabilities.

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

- Finish the active generation run or resume it after confirming no writer is running.
- Create `map_lab/showcase.template.html`; then run generation with `--export-only` to create the standalone 90-map HTML and JSON exports in `map-showcase/`.
- Browser-check playback, board size selection, rank ordering, both winning roles, step/scrub controls, finish/replay, and responsive layout. No live-server restart is needed.
- Add a method document with exact rule assumptions, formulas, solver proof reasoning, human-difficulty limitations and measured final counts/runtime.
- Audit all database records and all exported traces independently. Supply a portable analysis-only database artifact if its size is suitable for GitHub.
- Commit code, method documentation and a shareable showcase or compact export. The ignored `data/` directory is not a GitHub handoff; provide reproducible commands and, if appropriate, a deliberately selected analysis-only export without player data.
- Update this log and push each meaningful milestone. Never force-push over teammates' work.

## Environment notes

- Actual local project: `/Users/nthn/Documents/Netcentric_Architecture/Term_Project`.
- App workspace permissions still refer to the old path containing spaces. Some writes, local-network checks and builds consequently require approval.
- GitHub remote: `https://github.com/nthhhhn/escape-plan.git`.
- `escape-plan15.local` is published by this Mac's Bonjour hostname configuration. The backend setting only reports a sharing URL; cloning the repository does not configure another computer's mDNS.
- Do not restart the live game server for this offline experiment.
