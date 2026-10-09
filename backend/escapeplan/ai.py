"""Bounded CPU jobs. Inputs are role-filtered observations, never live matches."""
from __future__ import annotations
import json
import random
import time
from functools import lru_cache
from pathlib import Path
from .engine import State, Rules, generate, apply_action, legal_actions, distance, determinize, observation, candidate_actions, neighbors, walkable


def evaluate(s: State, role: str, algorithm: str = 'bfs') -> float:
    if s.winner:
        return 1000 if s.winner == role else -1000
    goal = s.key if not s.has_key and s.key is not None else s.real_tunnel
    escape = distance(s, s.positions['prisoner'], goal, 'prisoner', algorithm)
    chase = distance(s, s.positions['warder'], s.positions['prisoner'], 'warder', algorithm)
    style = s.rules.personality
    mobility = sum(walkable(s, n, 'prisoner') for n in neighbors(s.positions['prisoner'], s.rules.size))
    approaches = [n for n in neighbors(s.real_tunnel, s.rules.size) if walkable(s, n, 'warder')]
    intercept = min((distance(s, s.positions['warder'], n, 'warder', algorithm) for n in approaches), default=s.rules.size**2)
    if role == 'prisoner':
        if style == 'pursuer':
            value = chase*.7 - escape*4
        elif style == 'planner':
            value = chase*2 - escape*1.5 + mobility*1.5
        else:
            value = chase*1.4 - escape*1.8 + mobility*.5
        value += 2 if s.has_key else 0
    else:
        if style == 'pursuer':
            value = -chase*4
        elif style == 'planner':
            value = -chase*1.5 - intercept*.8 - mobility*1.5
        else:
            value = -chase*1.8 - intercept*.3 - mobility*.5 + len(s.roadblocks)*1.5
        if chase <= 1 and s.turn == 'warder':
            value += 20
    value += sum(s.charges[role].values()) * (.1 if style == 'trickster' else .5)
    if style == 'trickster':
        if role == 'prisoner' and s.smoke_until > s.ply and s.radar_until <= s.ply:
            value += 2
        if role == 'warder' and s.radar_until > s.ply and s.smoke_until > s.ply:
            value += 2
    if role == 'warder' and 'relocate' in s.rules.modifiers:
        value -= max(s.tunnel_pressure.values(), default=0) * .5
    return value


def action_key(a: dict) -> str:
    return f"{a['kind']}:{a.get('direction', '')}:{a.get('steps', 2) if a['kind'] == 'sprint' else ''}"


def features(s: State) -> str:
    role = s.turn
    size = s.rules.size
    pos = s.positions[role]
    other = s.positions['prisoner' if role == 'warder' else 'warder']
    goal = s.key if s.key is not None else s.real_tunnel
    # Compact tabular approximation; terrain farther than immediate neighbors is omitted.
    from .engine import neighbors, walkable
    local = ''.join('1' if walkable(s, n, role) else '0' for n in neighbors(pos, size))
    charges = ','.join(str(v) for v in s.charges[role].values())
    return '|'.join(map(str, [role, size, ','.join(sorted(s.rules.modifiers)), s.rules.powers, s.rules.personality, other//size-pos//size, other%size-pos%size, goal//size-pos//size, goal%size-pos%size, local, s.has_key, charges, max(0,s.smoke_until-s.ply), max(0,s.radar_until-s.ply), distance(s,pos,goal,role), max(s.tunnel_pressure.values(),default=0)]))


@lru_cache(maxsize=4)
def load_model(path, modified):
    return json.loads(Path(path).read_text())


def greedy(s: State, actions: list[dict], rng: random.Random, algorithm='bfs') -> dict:
    ranked = [(evaluate(apply_action(s, a), s.turn, algorithm), rng.random(), a) for a in actions]
    return max(ranked, key=lambda row: row[:2])[2]


def choose(view: dict, policy: str, seed: int, model_path: str = '', budget: float = .65) -> dict:
    start = time.monotonic()
    rng = random.Random(seed)
    s = determinize(view, seed)
    actions = legal_actions(s)
    meta = {'policy': policy, 'depth': 0, 'fallback': False}
    if policy == 'easy':
        action = rng.choice(actions)
    elif policy == 'qlearning':
        try:
            model = load_model(model_path, Path(model_path).stat().st_mtime_ns)
            values = model['q'].get(features(s), {})
        except (OSError, ValueError, KeyError):
            values = {}
        known = [a for a in actions if action_key(a) in values]
        action = max(known, key=lambda a: values[action_key(a)]) if known else greedy(s, actions, rng)
        meta['fallback'] = not bool(known)
    elif policy != 'hard':
        action = greedy(s, actions, rng, policy)
    else:
        role = s.turn
        action = greedy(s, actions, rng)
        def search(node, depth, alpha, beta):
            if time.monotonic() - start > budget:
                raise TimeoutError
            if not depth or node.winner:
                return evaluate(node, role)
            maximize = node.turn == role
            value = -float('inf') if maximize else float('inf')
            children = [apply_action(node, a) for a in legal_actions(node)]
            children.sort(key=lambda child: evaluate(child, role), reverse=maximize)
            for child in children:
                score = search(child, depth-1, alpha, beta)
                if maximize:
                    value, alpha = max(value, score), max(alpha, score)
                else:
                    value, beta = min(value, score), min(beta, score)
                if beta <= alpha:
                    break
            return value
        for depth in range(1, 7):
            try:
                scores = [(search(apply_action(s, a), depth-1, -float('inf'), float('inf')), a) for a in actions]
                action = max(scores, key=lambda pair: pair[0])[1]
                meta['depth'] = depth
            except TimeoutError:
                break
    meta['elapsed_ms'] = round((time.monotonic()-start)*1000)
    return {'action': action, **meta}



def random_step(s: State, rng: random.Random) -> State:
    # A shuffled candidate list gives each legal action equal probability without
    # constructing every possible successor first.
    actions = candidate_actions(s)
    rng.shuffle(actions)
    for action in actions:
        try:
            return apply_action(s, action)
        except ValueError:
            continue
    return apply_action(s, {'kind': 'pass'}, timeout=True)


def rollout(view: dict, seed: int, count: int = 200, horizon: int = 60, budget: float = 5) -> dict:
    start = time.monotonic()
    rng = random.Random(seed)
    wins = {'warder': 0, 'prisoner': 0, 'unresolved': 0}
    for i in range(count):
        if i and time.monotonic()-start > budget:
            break
        s = determinize(view, seed+i)
        for _ in range(horizon):
            if s.winner:
                break
            s = random_step(s, rng)
        wins[s.winner or 'unresolved'] += 1
    n = sum(wins.values())
    return {**wins, 'samples': n, 'target': count, 'horizon': horizon, 'policy': 'random legal actions', 'elapsed_ms': round((time.monotonic()-start)*1000), 'prisoner_pct': round(wins['prisoner']/max(n, 1)*100)}


def analyze_pair(before: dict | None, after: dict, role: str, seed: int) -> dict:
    current = rollout(after, seed)
    feedback = None
    # Do not compare different information sets: revelations would masquerade as move quality.
    if before and before['positions']['prisoner'] is not None and after['positions']['prisoner'] is not None and before['real_tunnel'] is not None and after['real_tunnel'] is not None:
        prior = rollout(before, seed, budget=3)
        old = prior[role]/max(prior['samples'], 1)
        new = current[role]/max(current['samples'], 1)
        delta = new-old
        # Broad band avoids pretending Monte Carlo noise is a precise verdict.
        category = 'improved' if delta > .15 else 'worsened' if delta < -.15 else 'uncertain'
        feedback = {'category': category, 'delta': round(delta*100), 'before_samples': prior['samples']}
    return {'estimate': current, 'coach': feedback}


def write_json(path: Path, data: dict):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def train(data_dir: str, episodes: int, config: dict, seed: int) -> dict:
    """Tabular Q-learning versus a random opponent, alternating training roles."""
    root = Path(data_dir)
    q: dict[str, dict[str, float]] = {}
    metrics = []
    rules = Rules.parse(config)
    rng = random.Random(seed)
    start = time.time()
    coverage = {'size': rules.size, 'modifiers': rules.modifiers, 'powers': rules.powers, 'personality': rules.personality, 'schema': 2}
    status = {'status': 'running', 'episodes': episodes, 'completed': 0, 'metrics': metrics, 'seed': seed, 'coverage': coverage, 'started': start, 'alpha': .2, 'gamma': .95, 'baseline': 'random legal actions', 'horizon': 80}
    write_json(root/'training.json', status)
    def episode(index: int, learning: bool):
        role = 'warder' if index % 2 == 0 else 'prisoner'
        state = generate(rules, seed+index if learning else seed+1_000_000+index)
        for _ in range(40):
            if state.winner:
                break
            if state.turn != role:
                state = random_step(state, rng)
                if state.winner:
                    break
            # Q observations respect smoke and private tunnel identities too.
            perceived = determinize(observation(state, role), seed+index+state.ply)
            options = legal_actions(perceived)
            key = features(perceived)
            values = q.setdefault(key, {}) if learning else q.get(key, {})
            epsilon = max(.08, 1-index/max(episodes, 1)) if learning else 0
            if rng.random() < epsilon or not values:
                action = rng.choice(options)
            else:
                action = max(options, key=lambda a: values.get(action_key(a), 0))
            try:
                next_state = apply_action(state, action)
            except ValueError:
                # Inference can miss hidden collisions; an invalid action consumes no live turn.
                # For bounded training, model the remaining turn as timing out.
                next_state = apply_action(state, {'kind': 'pass'}, timeout=True)
            if not next_state.winner:
                next_state = random_step(next_state, rng)
            reward = (1 if next_state.winner == role else -1) if next_state.winner else -.01
            if learning:
                # Small bounded potential shaping avoids rewarding repeated power use.
                from math import tanh
                potential = lambda node: 0 if node.winner else .08*tanh(evaluate(node, role)/10)
                reward += .95*potential(next_state)-potential(state)
            if learning:
                akey = action_key(action)
                next_view = determinize(observation(next_state, role), seed+index+next_state.ply)
                future = max((q.get(features(next_view), {}).get(action_key(a), 0) for a in legal_actions(next_view)), default=0) if not next_state.winner else 0
                values[akey] = values.get(akey, 0) + .2*(reward+.95*future-values.get(akey, 0))
            state = next_state
        return state.winner == role, state.winner is None
    for i in range(episodes):
        episode(i, True)
        if (i+1) % max(10, episodes//10) == 0 or i+1 == episodes:
            results = [episode(j, False) for j in range(20)]
            metric = {'episode': i+1, 'win_rate': sum(w for w, _ in results)/20, 'warder_win_rate': sum(w for w, _ in results[::2])/10, 'prisoner_win_rate': sum(w for w, _ in results[1::2])/10, 'unresolved': sum(u for _, u in results), 'samples': 20, 'states': len(q)}
            metrics.append(metric)
            status['completed'] = i+1
            write_json(root/'training.json', status)
    write_json(root/'q-model.json', {'q': q, 'coverage': coverage, 'seed': seed, 'episodes': episodes})
    status.update(status='complete', elapsed_seconds=round(time.time()-start, 1), states=len(q))
    write_json(root/'training.json', status)
    return status
