# Extra Features Score Sheet

Use this table after demonstrating every fundamental requirement. The assignment awards
2 points for each accepted AI feature and 1 point for each accepted non-AI feature, up to
10 points. Final classification is the instructor's decision.

| # | Feature name | AI feature | Points | Fast demonstration |
|---:|---|:---:|---:|---|
| 1 | Search opponents (BFS, A*, minimax with alpha-beta) | ✓ | 2 | Play one bot turn and open Field Guide to show how the selected search works. |
| 2 | Q-learning opponent with saved training evidence | ✓ | 2 | Open AI Lab, show the saved 5,000-episode 5×5/no-powers policy, then play one learned move. Point out any labeled fallback. |
| 3 | Monte Carlo escape estimate and move coach | ✓ | 2 | Enable Live analysis, make one move, and show the estimate plus feedback. State that it is a simulation estimate. |
| 4 | Role-specific power-ups |  | 1 | Use one Prisoner power and one Warder power in Special mode. |
| 5 | Nine-stage progression and larger boards |  | 1 | Show saved stage progress and open a 7×7 or 9×9 stage. |
| 6 | Special-rule system |  | 1 | Demonstrate one clear modifier: moving wall, lock and key, or false exits. |
| 7 | Extended host dashboard and reconnect support |  | 1 | Show match history or a room reset, then refresh one client and resume within 20 seconds. |
|  | **Total requested** |  | **10** | |

## Claims to avoid

- Do not count room-code multiplayer, timers, scoring, rematch, random Classic maps,
  server validation, the client list, or global reset as extras; they support fundamental
  requirements.
- Do not claim each bot personality as a separate AI feature.
- Do not claim Q-learning improvement from the graph. Say that it records measured
  held-out results; the saved curve is noisy.
- Do not call the 30,000-map offline research database the live game's map pool.
- Keep containment and tunnel relocation as backups because they take too long to show
  in a 10-minute check.

## Thirty-second explanation

The browser sends player actions over one WebSocket. The FastAPI server owns the game
state, validates actions, advances the timer, updates scores, and sends each player an
authorized view. Search opponents, the Q-learning policy, and the Monte Carlo coach all
run on the server. The remaining extras are optional modes and host tools built around
the same server-authoritative game.
