# Escape Plan Map Atlas

Download/open `index.html` in your browser. It works offline and includes 90 animated scenarios: 30 each for 5x5, 7x7 and 9x9. Use the size tabs and difficulty/role filters; inspect moves to see exact outcomes of alternatives.

The full collection contains 30,000 unique layouts. From the project root, run `.venv/bin/python -m map_lab.restore` to restore the included compressed SQLite snapshot into `data/map-lab-pool.sqlite3`. Existing files are never overwritten. The live multiplayer database is separate.

Outcomes are proved for fixed terrain with a visible tunnel, no powers or modifiers, and timeout waiting allowed. Difficulty labels are provisional relative rankings, not human-tested ratings or fair-win probabilities.

See [methodology](../map_lab/METHODOLOGY.md), [validation results](validation-report.json), [generation results](generation-report.json), and [handoff / next steps](../HANDOFF.md).

The [Python and database reference](../map_lab/README.md) links the actual scripts used, explains the generation pipeline and database fields, and records the reproduction commands.
