# Escape Plan Demo Runbook

Target seven to eight minutes so there is time for questions. Follow the rubric order:
setup, clients, Classic gameplay, server controls, then extras.

## Before the slot

- [ ] Computer A runs the server and one game client. Computer B runs only a game client.
- [ ] Both computers open the source-defined address from `frontend/src/config.ts`; no one
  types an address or port into the game.
- [ ] Open `/server` on Computer A and unlock it with the private admin token.
- [ ] Confirm the dashboard shows both clients by nickname.
- [ ] Press the global Reset button to clear rehearsal rooms and scores.
- [ ] Confirm AI Lab shows the completed 5,000-episode, 5×5, powers-off,
  no-modifier policy.
- [ ] Close unrelated tabs, disable sleep, connect power, and keep the browser at 100%.
  The Classic board and Rematch button fit at 1366×768 in the checked build.
- [ ] Keep a recording of the same final build available as a backup.

## Live sequence

| Time | Action | Checkpoint to say aloud |
|---|---|---|
| 0:00–0:30 | Point to both computers and the server process/dashboard on A. | “A runs the socket server and a client. B runs only a client and connects directly to A.” |
| 0:30–1:10 | Enter Alice and Bob. Show `Welcome, Alice.` / `Welcome, Bob.`, the waiting room, and the dashboard count/list. | No IP or port form; server sends the connected-user list. |
| 1:10–1:45 | Alice creates Classic; Bob joins; both click Ready. | 5×5 board: 19 free, 5 obstacles, 1 tunnel; roles, terrain, and free-cell starts are randomized; warder moves first. |
| 1:45–2:35 | Make adjacent moves, point to the 10-second timer, try a wall, and show that the warder cannot use the tunnel. | The server rejects illegal movement and alternates turns. Let one timeout occur only if time permits. |
| 2:35–3:20 | Cooperate to finish by capture or escape. | Both clients show Win/Lost, both current scores, winner +1, and Rematch. |
| 3:20–3:55 | Alice clicks Rematch; pause. Bob clicks Rematch. | One request does not restart; after both agree, the previous winner is the warder and moves first. |
| 3:55–4:30 | Show the server dashboard and press Reset games & scores. | Connected-client count/list remain visible; both clients return to the lobby with scores cleared. |
| 4:30–5:30 | Demonstrate a search bot and briefly open Field Guide. | Name the selected algorithm and show one real server-selected move. |
| 5:30–6:15 | Open AI Lab, then play one Q-learning move. | Policy is saved for 5×5, powers off, no modifiers; unseen states use a labeled pathfinding fallback. |
| 6:15–6:50 | Enable Live analysis and make one move. | Monte Carlo estimate and move coach are simulation evidence, not a guaranteed human win probability. |
| 6:50–7:40 | Show powers, one special modifier, and a larger Stage board. | These features are separate from Classic so the fundamental rules remain unchanged. |
| 7:40–8:00 | Return to the extra-feature table. | Point to the seven requested feature rows and invite questions. |

## Exact short answers

**Where is the server address and port?**

“They are in `frontend/src/config.ts`. The selected build profile supplies a fixed host and
port, so players never enter either value.”

**Why WebSocket?**

“The client sends actions through one persistent connection and the server pushes the
authoritative state to both players immediately.”

**How do you prevent cheating?**

“The browser requests an action; the server validates turn ownership, adjacency, terrain,
the timer, and hidden information before publishing the result.”

**Does the Q-learning curve prove improvement?**

“No. It records held-out results against random legal play. The policy is real, but the curve
is noisy and unseen states use a labeled fallback.”

**How is the cloud setup related to the required topology?**

For strict grading, use the two-computer LAN arrangement above. If the cloud build is shown,
say: “The same server also runs on GCP; this is deployment evidence in addition to the
required two-computer demonstration.”

## Stop conditions before submission

Do not record or submit a build unless all of these are true:

- both real computers can complete a Classic match and rematch;
- `/server` has the correct private token and shows both clients;
- the public address has not changed, or `CLOUD_IP` has been updated and rebuilt;
- AI Lab reports `complete` for the cloud copy if Q-learning is claimed there;
- source ZIP and video both open from the submitted locations.
