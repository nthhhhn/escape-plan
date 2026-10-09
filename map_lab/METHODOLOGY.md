# Map Atlas: methodology and reproducibility

This is an isolated, offline experiment. It does not modify the live game's map pool, SQLite database, server, or rules.

## Delivered data

- 30,000 unique layouts/scenarios: 10,000 each for 5x5, 7x7, and 9x9.
- Each size has 5,000 forced prisoner wins and 5,000 forced warder wins. This is deliberate outcome coverage, **not a 50% player win-rate claim**.
- 30 displayed scenarios per size, 15 for each winning role, selected across relative difficulty ranks. Total: 90.
- Full persistent local database: `data/map-lab-pool.sqlite3`.
- Portable, analysis-only snapshot: `map-showcase/map-pool.sqlite3.gz` (about 11 MB compressed, 139 MB uncompressed).
- `map-showcase/index.html` is self-contained. Open it directly in a browser. No game server, external scripts, external images or network access is needed.
- Measured generation time on the development Mac: 21.23s (5x5), 73.48s (7x7), 201.85s (9x9), approximately 4m57s total. These are measured generation times, not promises for another machine.

The universe of maps is much larger than this dataset. This is a finite, resumable sample. It is not exhaustive enumeration or a claim that every accepted map is fun.

## Exact rules being solved

Fixed walls, one visible tunnel, no powers, no keys, no pickups, and no changing terrain. Both players see the complete board. Orthogonal one-cell movement. Warder moves first and cannot enter the tunnel. Capture takes precedence if positions coincide; otherwise the prisoner wins by entering the tunnel.

Either player can stay still by allowing a turn to time out. This is included because `engine.apply_action(..., timeout=True)` supports it. In the real UI, the ordinary Pass button does not allow arbitrary waiting. An animated wait represents a timeout, with time compressed for replay. The model treats waiting as an available action, not as a random event.

There is no repetition-draw or turn-limit rule in this static model. A residual state means both sides can avoid their own loss indefinitely; it does not mean the live game declares a draw. A forced win is preferred to indefinite play, which is preferred to a forced loss. Network disconnects and missed input are outside the model.

These results do not establish outcomes for powers, Smoke, fake tunnels, keys, collapsing floors, shifting walls or tunnel relocation. Those need new state representations and separate analysis.

## Exact solver and proof reasoning

A state is `(warder location, prisoner location, side to move)`. Locations are indices of non-wall cells; a warder at the tunnel is excluded. There are at most 760, 2,964 and 8,320 valid location/turn combinations under the respective obstacle counts, including terminal positions.

Retrograde analysis starts from every terminal capture and escape:

1. A state is winning for the active player when at least one successor is already a win for that player.
2. A state is losing for the active player when every successor is already a win for the opponent.
3. Iterate until the queue is empty. States left unresolved by these two rules permit indefinite avoidance.

A priority queue processes solved states by increasing remoteness. At a winning player's turn, remoteness is one plus the minimum distance among winning successors. At a losing player's turn, it is one plus the maximum successor distance. Thus the demonstration shows fastest forced victory against longest possible resistance.

Every generated layout runs `Solver.verify()` over **every valid state**. It checks terminal labels, successor outcome conditions and both distance equations. Unresolved states must have no immediately force-winning successor for their actor and at least one unresolved successor. Strictly decreasing remoteness along each proof line ensures its advertised finish cannot conceal a loop.

The solver proves the existence of a strategy against every opposing response. The animation shows one principal variation; it is not itself the proof and does not enumerate every winning line.

## Independent validation

`map_lab/test_solver.py` constructs transitions through the real game engine and applies a separate fixed-point algorithm (no retrograde predecessor queue). It compares outcomes for every 3x3 wall pattern with a fixed corner exit and every legal spawn/turn combination. The all-walls pattern has no legal warder location and is skipped. It includes disconnected boards and cyclic play. Additional tests compare larger-board transitions, replay proof lines through the engine, check rotation/reflection deduplication and verify independent-path counts.

Generation validates every selected trace through `engine.apply_action()`. The final audit again replays **all 30,000 stored demonstrations, comprising 233,818 actions, including 26,758 waits**. It checks coordinates, alternating turns, terminal winners, frame counts, decreasing remoteness, unique layouts and SQLite integrity.

The audit also re-solves all 90 exported examples, checks every displayed move alternative against exact outcomes/remoteness, and verifies 30 examples per size with 15 of each winner. `validation-report.json` contains actual totals, timing and the SHA-256 of the uncompressed SQLite snapshot.

Browser QA exercises all 90 examples, all size/role/difficulty filters, move stepping, timeline scrubbing, terminal displays, replay loops, move inspection and mobile overflow. The page makes no external requests. See `map_lab/check_showcase.cjs`.

## Generation and acceptance

Use the existing engine generator for obstacle count, connected terrain, two approaches to each tunnel and basic spawn constraints. Then enumerate eligible starting pairs on that layout: warder sufficiently far from the exit/approaches, players at least two Manhattan steps apart, and prisoner at least two walking steps from the exit.

Retain starts with a proven finish of 4–80 individual turns. Prefer the currently underrepresented winning role where the layout supports it, otherwise use the other role. Sample up to three eligible starts with a seeded RNG. Alternate selecting the lowest, middle and highest provisional difficulty among those samples. This is a sampling heuristic, not an exhaustive search for the hardest start.

Deduplicate layouts under all four rotations and their reflections, including tunnel placement. Only one scenario is retained for each canonical layout. The final 5x5 run rejected 779 duplicate candidates. Each 7x7 and 9x9 candidate in this run admitted an eligible nontrivial start and had a unique layout. That does not establish that every possible layout is suitable.

The stored scenario includes its modified spawn pair. The seed reproduces the terrain, **not the chosen final spawn pair by itself**. Use stored positions when replaying/importing a scenario.

## Difficulty: provisional, transparent, not a human probability

Let each component be scaled to [0,1]. The raw score is:

`100 × (0.40 lookahead + 0.25 precision + 0.20 greedy traps + 0.10 detours + 0.05 execution)`

- **Lookahead:** at up to six evenly spaced winning-role turns on the proof line, run 1–5-ply minimax using an independent distance/mobility heuristic. Find the first tested depth at which all tied preferred choices preserve the solved win. A sentinel depth 6 means none of the tested depths succeeded. Scale `(depth-1)/5`, then average. This is not the minimum human reasoning depth; deeper searches can also behave differently.
- **Precision:** average fraction of legal choices that give up the forced win on the winner's turns. Some of these choices lead to indefinite play rather than an immediate loss.
- **Greedy traps:** average fraction of tied one-ply heuristic favourites that fail to preserve the forced win.
- **Detours:** share of winning-role moves that increase distance to the tunnel (prisoner) or to the prisoner's current square (warder).
- **Execution:** winner decisions divided by 15, capped at 1. This gives game length only 5% of the score.

The heuristic is prisoner-oriented: `3 × warder-to-prisoner distance − 2 × prisoner-to-exit distance + 0.4 × prisoner mobility − 0.2 × warder mobility`; terminal values dominate. It never reads solved outcomes while searching. Outcome labels are used afterwards to evaluate its preferred moves.

Percentiles use equal-score midranks within each `(board size, proven winner)` group. Easy/Medium/Hard divide that distribution into thirds. A "Hard" 9x9 warder win may still be easy for a person or easier than a "Medium" prisoner win. Do not compare percentiles across groups as absolute difficulty.

All these proxies depend on one optimal demonstration and one heuristic model. They do not quantify perceived fairness, enjoyment, creativity, actual human error, or the probability a person discovers the outcome. Human playtests and additional agent styles are needed before using these labels as a calibrated difficulty system.

Independent route counts are internally vertex-disjoint prisoner-to-exit paths, computed with a vertex-capacitated max-flow construction. Junction count, dead ends, cycle rank and independent routes are descriptive topology features; they are not weighted in this first score and do not guarantee safe traversal against the warder.

## Reproduce, restore, or extend

Use the project virtual environment after running the usual setup. From the project root:

```bash
PYTHONPATH=backend:. .venv/bin/python -m pytest map_lab/test_solver.py -q

# Restore the portable database on a new checkout. Refuses to overwrite.
.venv/bin/python -m map_lab.restore

# Extend to a larger finite pool, or create one if no database exists.
PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --target 20000 --no-export

# Re-rank and select 30 showcase maps per size.
PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --export-only

# Re-audit everything and refresh the portable compressed snapshot.
PYTHONPATH=backend:. .venv/bin/python -m map_lab.audit
```

Run only one generator/writer at a time. Progress, next seed, accepted records and rejection counts are committed periodically and on normal interruption. For a separate experiment, supply `--database PATH --output DIRECTORY`; do not overwrite the live database. Changing rules or scoring methodology requires a new version/dataset and fresh validation.

For browser QA, make Playwright available to Node and run `node map_lab/check_showcase.cjs`. On macOS it uses the installed Chrome; elsewhere set `CHROME_PATH` or install Playwright's Chromium. The check writes screenshots to `/tmp` and does not control the live game.

The next scientific step is paired human playtesting with roles and presentation order counterbalanced. Record meaningful-choice ratings, explanations after losses and willingness to replay; then calibrate or reject these proxy weights. Pool selection should eventually consider those results and diversity jointly, rather than optimizing one scalar score.
