# Map generation: source code, algorithm and database reference

This directory contains the actual Python implementation used to generate the delivered 30,000-map dataset, not pseudocode. The first solver/generator checkpoint is `b915997`; the completed dataset, audit and showcase checkpoint is `cafe95b`.

## Files to read

| File | Purpose |
| --- | --- |
| [METHODOLOGY.md](METHODOLOGY.md) | Exact game assumptions, proof reasoning, difficulty formulas, validation and limitations. |
| [generate.py](generate.py) | Generate candidates, choose spawns, deduplicate layouts, save to SQLite, rank difficulty and export showcase examples. |
| [solver.py](solver.py) | Exact retrograde state-graph analysis, forced outcomes, optimal finish distance, replay construction and difficulty/topology metrics. |
| [Game engine](../backend/escapeplan/engine.py) | Existing terrain generator and real movement rules reused by generation and replay checks. |
| [test_solver.py](test_solver.py) | Independent outcome checks against engine-built transitions and other solver tests. |
| [audit.py](audit.py) | Replay every stored demonstration, re-solve showcase examples, verify data and create the compressed database snapshot. |
| [restore.py](restore.py) | Verify the snapshot checksum/integrity and restore it without overwriting an existing database. |
| [check_showcase.cjs](check_showcase.cjs) | Browser checks for the animated HTML showcase. |

## How the maps were produced

1. Generate seeded terrain using the existing engine with 5, 10 or 16 obstacles for sizes 5, 7 or 9 respectively.
2. Deduplicate layouts under rotation/reflection, including tunnel placement.
3. Solve the complete static state graph: both character positions and whose turn it is. Retrograde propagation proves forced wins; unresolved states permit indefinite avoidance. This handles cycles rather than recursively exploring infinitely repeated move sequences.
4. Consider eligible spawn pairs and keep decisive starts requiring 4–80 turns under optimal play. Sample up to three starts, alternating easier/middle/harder provisional scores while seeking coverage of both winning roles.
5. Verify graph outcome/distance equations and replay the chosen demonstration through the actual game engine.
6. Save the full scenario, metrics, proof replay and provenance in SQLite. Rank difficulty within each size and winning role, then export 30 examples per size.

No LLM generates individual moves or decides the proven winner. The Python solver performs that analysis. Human difficulty is estimated using lookahead, precision, misleading greedy choices, detours and execution length; it is not a proven human difficulty rating. See the methodology for the exact formula and qualifications.

## Database and saved fields

The complete local SQLite database is `data/map-lab-pool.sqlite3`, containing **30,000 maps**: 10,000 per size, with 5,000 prisoner wins and 5,000 warder wins in each size. This is outcome coverage, not evidence that each map is competitively fair.

The full database is committed in compressed form as [map-pool.sqlite3.gz](../map-showcase/map-pool.sqlite3.gz). It is about 11.4 MB compressed / 139 MB uncompressed. It contains all 30,000 records, not only the 90 showcase examples. Restore it on a new checkout with:

```bash
.venv/bin/python -m map_lab.restore
```

The `maps` table stores `id`, `size`, `seed`, symmetry-deduplication `canonical` hash, `winner`, `raw_difficulty`, `percentile`, `difficulty`, JSON `scenario`, JSON `metrics`, JSON `trace`, `solver_version`, `verified`, and `created_at`. The scenario includes terrain, tunnel, final spawns, starting turn and rule settings. The seed alone does not reproduce the selected spawns; use the stored scenario.

The `progress` table stores resumable seeds, attempts, rejection reasons and timing per size. The `metadata` table stores rule assumptions. This analysis database is separate from the live multiplayer database; the dataset has not been installed into live map selection.

## Commands used

Run from the repository root with the project Python environment and backend dependencies installed:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:. .venv/bin/python -m pytest map_lab/test_solver.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --target 10000 --no-export
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:. .venv/bin/python -m map_lab.generate --export-only
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:. .venv/bin/python -m map_lab.audit
```

`--target` is the number of maps **per size**. The generator resumes the existing database. Run only one writer at a time. To regenerate independently, supply a new `--database` path and `--output` directory to generation/export/audit; do not overwrite the delivered pool or live database. Changing the rules or score requires a separately versioned dataset and fresh validation.

Measured generation took approximately five minutes on the development Mac. Four solver tests passed; the audit replayed 233,818 actions across all 30,000 scenarios and re-solved all 90 showcase examples. Portable database restoration also passed checksum, integrity, table and record-count checks.

See the actual [generation report](../map-showcase/generation-report.json), [validation report](../map-showcase/validation-report.json), [animated showcase](../map-showcase/index.html), and [handoff / future work](../HANDOFF.md).
