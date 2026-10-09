# Escape Plan handoff

Updated: 2026-10-09 (Asia/Bangkok), completed offline atlas

## Current status

The game source, launcher, documentation and deployment files are on GitHub at `nthhhhn/escape-plan`, branch `main`, initial commit `0bcd309`. The working tree was clean when this handoff was prepared. The local game uses FastAPI, WebSockets, React and SQLite. Previous backend validation passed 33 tests.

The current task is a separate, offline map-analysis database and animated HTML showcase. The initial approval/usage interruption has cleared. `map_lab/solver.py`, `map_lab/generate.py`, and `map_lab/test_solver.py` now exist. Four tests pass, including independent engine-based fixed-point analysis for all 256 fixed-exit 3x3 wall patterns, larger-board transitions and proof replays, symmetry deduplication, and independent-route counts. Every generated layout also passes all-state outcome/remoteness checks and its demonstration is replayed through the real engine.

Generation is complete: **30,000 unique layouts**, 10,000 per supported size, each with 5,000 proven prisoner wins and 5,000 proven warder wins. The full database is **`data/map-lab-pool.sqlite3`**. Generation took 21.23 / 73.48 / 201.85 seconds for 5x5 / 7x7 / 9x9 (about five minutes total). No generator is running. The pilot `data/map-lab.sqlite3` is an earlier experiment, not the final pool.

Open **`map-showcase/index.html`** directly in a browser: 30 animated examples per size, 90 total, with looping playback, stepping, speed control, filters, exact move alternatives, difficulty explanations and methodology. The portable analysis-only database is **`map-showcase/map-pool.sqlite3.gz`** (11.4 MB compressed). Restore on a fresh checkout with `.venv/bin/python -m map_lab.restore`; it refuses to overwrite an existing database. Restore was successfully verified in `/tmp`, including checksum, SQLite integrity, record count and table allowlist. Snapshot packaging converts WAL format to a self-contained rollback-journal database.

Validation is complete: four solver tests passed; all 30,000 demonstrations were replayed through the real engine (233,818 actions, including 26,758 timeout waits); all 90 exported scenarios were independently re-solved and their displayed alternatives checked. Browser QA passed for all 90 examples, controls, filters, replay loops and mobile layout, with zero JavaScript errors or external requests. Machine-readable counts are in `map-showcase/validation-report.json` and `generation-report.json`. Full assumptions, formulas and reproduction commands are in **`map_lab/METHODOLOGY.md`**.

The generator samples up to three eligible starting pairs on each layout and alternates selecting the easiest/median/hardest by its provisional score. It preferentially seeks the underrepresented winning role when possible. Every map is decisive with an optimal finish of 4–80 plies. These are exact static-rule puzzles, not proven competitively balanced or human-validated maps. Difficulty is ranked within board size and winning role; saved scores are proxies, not human success probabilities.

The user asks to push progress and next-step notes to GitHub as work proceeds so a teammate can continue. Commit meaningful checkpoints together with updates to this file. Do not claim a push succeeded until Git confirms it. Do not include credentials, admin tokens, local player databases or unrelated changes.

## Latest user requirements

- Generate a large persistent pool of interesting maps, ordered from easy to hard, for the supported board sizes 5x5, 7x7 and 9x9.
- Difficulty must consider how difficult a human would find the winning strategy, not merely move count or simulated win rate.
- Produce a standalone HTML showcase with 30 selected maps per size (90 total), ordered by estimated difficulty and with looping animated winning demonstrations.
- Keep a much larger collection in a real SQLite database. The chosen finite budget is 30,000 maps; exhaustive enumeration is not feasible. Generation is resumable and can extend this budget.
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

## Next steps for a teammate

The requested offline artifact is complete. These are future research/integration steps, not unfinished generation:

- Review the showcase with people before treating provisional Easy/Medium/Hard as actual human difficulty. Record errors, reasoning, enjoyment and willingness to replay; counterbalance roles and presentation order.
- Compare several imperfect agent styles and calibrate or reject the present score weights. A forced-win scenario is not proof of competitive fairness.
- Discuss live-game integration separately. No production map selection or live database has been changed. Powers, hidden information and moving tunnels require separate models and validation.
- To extend the pool, restore if necessary, then run `PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --target 20000 --no-export` (20,000 per size), followed by `--export-only` and `python -m map_lab.audit` with the same environment. Run only one writer. Revalidate and update this log before pushing.
- Prior pushed checkpoints: `b0906f2` (requirements/handoff), `b915997` (solver/generator/tests). The completion commit contains this log, the showcase, portable database, audits and methodology. Never force-push over teammates' work.

## Environment notes

- Actual local project: `/Users/nthn/Documents/Netcentric_Architecture/Term_Project`.
- App workspace permissions still refer to the old path containing spaces. Some writes, local-network checks and builds consequently require approval.
- GitHub remote: `https://github.com/nthhhhn/escape-plan.git`.
- `escape-plan15.local` is published by this Mac's Bonjour hostname configuration. The backend setting only reports a sharing URL; cloning the repository does not configure another computer's mDNS.
- Do not restart the live game server for this offline experiment.
