# Gameplay revision

Agreed scope: illustrated role-aware characters; a quieter board-first layout; click targets and keyboard controls; room activity, readiness and a synchronized 3-second countdown; opt-in coaching; independent reaction panel and muted-by-default audio; extended stationary Smoke; balanced spawn heuristics; optional Shifting Escape Tunnel; named bot personalities and custom algorithms; an algorithm-aware Field Guide. Cloud deployment is excluded.

Implementation and verification notes will be recorded here. Training results must remain measured, and unavailable external meme assets must not be represented as installed.

## Implemented locally

- Board-first redesign with flat chess-inspired surfaces, illustrated warder/prisoner pieces, a colored `YOU` marker, and grayscale opponent art.
- Direct click movement with visible legal destinations, plus repaired WASD/arrow controls after clicking buttons.
- Server-owned Ready state, join/ready activity messages, and synchronized `3 → 2 → 1 → GO!` countdown before the first turn timer.
- Always-visible reaction panel using reaction-meme templates with an illustrated fallback. Sound remains separately muted by default; coaching is opt-in and its last result survives later turns.
- Longer stationary Smoke, role-visible effect durations, stricter tunnel approach/spawn validation, and the optional Shifting Escape Tunnel modifier.
- Named bot roster, role choice for solo practice, three scoring personalities, route caching, cached policy loading, role-separated Q-learning evaluation, and updated learned features. The saved model was retrained with schema 2 for the Planner personality on 5×5 maps without powers.
- Field Guide with character backgrounds, role behavior, weaknesses, interactive algorithm walkthroughs, pseudocode, powers, and counterplay.

## Verification

- Backend: 29 tests pass, including readiness/countdown state, extended Smoke privacy, relocation/cooldown, hidden information, all AI policies, training, persistence, and two-client WebSocket play.
- Frontend: TypeScript and Vite production build pass.
- Browser: two isolated clients joined one room, readied, saw the countdown, received distinct roles, displayed three legal targets for the active player, clicked a target, and advanced the turn without browser errors.
- Personality scoring produced different Hard-bot openings on 2 of 40 sampled maps with powers off and 2 of 40 with limited powers. The differences appear when route/power tradeoffs exist; names are preferences, not guarantees of a unique move every turn.
- Q-learning retraining completed 1,000 episodes and learned 7,525 compact states. Its final 20-game held-out evaluation against random legal play measured 55% overall wins: 70% as warder, 40% as prisoner, with 3 unresolved games. The small sample fluctuates across checkpoints and is not evidence of calibrated strength.

Cloud deployment remains deliberately pending until another gameplay review.

## Match and guide refinements — October 8

- Every started match, rematch, and next stage resets participant scores to zero in memory and storage. Completed-stage progress and match history remain intact.
- Solo stages have Skip stage during preparation, play, and results. Skipping aborts an unfinished match without a win or progress award and starts the next countdown. Skipping stage nine ends the run.
- Standard stages without modifiers or powers now require a safe prisoner escape route, accounting for the warder moving first and waiting. This is a sufficient route check, not a complete game solver or a fairness guarantee for modified games. The old stage-two 5×5 layout failed this check; all nine regenerated standard stages pass. Room IDs are ephemeral, so the precise historical state of Sector 20614A was not recovered.
- Warders see a persistent anti-camping explanation and an orange warning at pressure 2/3, above the board. It explains how to reset pressure and that relocation needs a valid destination.
- Role-specific Win/Lose results and revised right panel remain. Reactions now use 27 template images across 18 situations, including planning, pursuit, panic, exit proximity, powers, and camping. The previous two images are avoided; hidden prisoner positions never drive pursuit reactions. Images are externally hosted with a visible loading/error fallback and source link.
- Bot portraits now have distinct glasses, headset, hair, expressions, and cap details. The Field Guide uses separate random-choice, BFS/A* expansion, minimax reply-tree, and Q-value update examples, retaining technical pseudocode.
- Verification: 33 backend tests; production build; browser checks for warnings, Skip stage messaging, both results, reaction rotation/privacy, all algorithm tabs, Q-value update, and mobile overflow. Browser scenarios used controlled room snapshots, with skip and score persistence covered by real server integration tests.
