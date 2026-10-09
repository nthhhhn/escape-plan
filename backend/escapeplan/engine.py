"""Deterministic rules shared by live games, search, and training. No I/O."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict, replace
from collections import deque
from copy import deepcopy
from functools import lru_cache
import random

DIRECTIONS = {'up': (-1, 0), 'right': (0, 1), 'down': (1, 0), 'left': (0, -1)}
POWERS = {'warder': ('radar', 'roadblock'), 'prisoner': ('dig', 'sprint', 'smoke')}
MODIFIERS = ('shift', 'key', 'fake', 'shrink', 'timer', 'relocate')
POLICIES = ('easy', 'bfs', 'astar', 'hard', 'qlearning')


@dataclass
class Rules:
    mode: str = 'classic'
    size: int = 5
    bot: str = ''
    stage: int = 1
    modifiers: list[str] = field(default_factory=list)
    powers: str = 'off'
    analysis: bool = False
    personality: str = 'planner'
    player_role: str = 'random'

    @classmethod
    def parse(cls, value: dict) -> 'Rules':
        if not isinstance(value, dict):
            raise ValueError('Invalid settings')
        r = cls(**{k: v for k, v in value.items() if k in cls.__dataclass_fields__})
        if r.mode not in ('classic', 'stage', 'special') or r.size not in (5, 7, 9):
            raise ValueError('Unsupported mode or board size')
        if r.bot not in ('', *POLICIES) or r.powers not in ('off', 'limited', 'pickups', 'both'):
            raise ValueError('Unsupported opponent or power setting')
        if r.personality not in ('pursuer', 'planner', 'trickster') or r.player_role not in ('random', 'warder', 'prisoner'):
            raise ValueError('Unsupported personality or role')
        if not isinstance(r.stage, int) or not 1 <= r.stage <= 9:
            raise ValueError('Stage must be between 1 and 9')
        if not isinstance(r.modifiers, list) or any(m not in MODIFIERS for m in r.modifiers):
            raise ValueError('Unknown modifier')
        r.modifiers = list(dict.fromkeys(r.modifiers))
        if r.mode == 'classic':
            r.size, r.bot, r.modifiers, r.powers = 5, '', [], 'off'
        if r.mode != 'special':
            r.modifiers = [m for m in r.modifiers if m != 'relocate']
        if not r.bot:
            r.player_role = 'random'
        if r.mode == 'stage' and not r.bot:
            r.bot = 'bfs'
        return r


@dataclass
class State:
    rules: Rules
    seed: int
    tiles: list[str]
    positions: dict[str, int]
    tunnels: list[int]
    real_tunnel: int
    key: int | None = None
    has_key: bool = False
    turn: str = 'warder'
    ply: int = 0
    winner: str | None = None
    reason: str = ''
    charges: dict[str, dict[str, int]] = field(default_factory=dict)
    pickups: dict[int, str] = field(default_factory=dict)
    roadblocks: dict[int, int] = field(default_factory=dict)
    smoke_until: int = 0
    radar_until: int = 0
    last_event: str = 'The warder moves first.'
    tunnel_pressure: dict[int, int] = field(default_factory=dict)
    shift_cooldown: int = 0

    @property
    def rounds(self):
        return self.ply // 2

    @property
    def seconds(self):
        return max(5, 10 - self.rounds // 3) if 'timer' in self.rules.modifiers else 10


def neighbor(cell: int, direction: str, size: int) -> int | None:
    if direction not in DIRECTIONS:
        return None
    row, col = divmod(cell, size)
    dr, dc = DIRECTIONS[direction]
    row, col = row + dr, col + dc
    return row * size + col if 0 <= row < size and 0 <= col < size else None


def neighbors(cell: int, size: int):
    return [n for d in DIRECTIONS if (n := neighbor(cell, d, size)) is not None]


def walkable(s: State, cell: int, role: str, unlocked: bool | None = None) -> bool:
    if s.tiles[cell] == '#' or cell in s.roadblocks:
        return False
    if cell in s.tunnels:
        return role == 'prisoner' and (s.has_key if unlocked is None else unlocked)
    return True


def reachable(s: State, start: int, role: str, unlocked: bool | None = None) -> set[int]:
    seen = {start}
    q = deque([start])
    while q:
        for cell in neighbors(q.popleft(), s.rules.size):
            if cell not in seen and walkable(s, cell, role, unlocked):
                seen.add(cell)
                q.append(cell)
    return seen


def connected(s: State) -> bool:
    floors = {i for i, t in enumerate(s.tiles) if t == '.' and i not in s.roadblocks}
    if not floors:
        return False
    if not floors.issubset(reachable(s, s.positions['warder'], 'warder')):
        return False
    if not s.has_key and s.key is not None and s.key not in reachable(s, s.positions['prisoner'], 'prisoner', False):
        return False
    return s.real_tunnel in reachable(s, s.positions['prisoner'], 'prisoner', True)


def distance(s: State, start: int, goal: int, role: str, algorithm: str = 'bfs') -> int:
    return route_distance(tuple(s.tiles), tuple(sorted(s.roadblocks)), s.has_key, s.rules.size, start, goal, role, algorithm)


@lru_cache(maxsize=20000)
def route_distance(tiles, blocks, unlocked, size, start, goal, role, algorithm):
    if start == goal:
        return 0
    # Both policies use the same movement permissions. A* prioritizes Manhattan distance.
    import heapq
    def allowed(cell):
        return tiles[cell] != '#' and cell not in blocks and (tiles[cell] != 'T' or (role == 'prisoner' and unlocked))
    if algorithm == 'bfs':
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            cell, cost = queue.popleft()
            for nxt in neighbors(cell, size):
                if nxt not in seen and allowed(nxt):
                    if nxt == goal:
                        return cost + 1
                    seen.add(nxt)
                    queue.append((nxt, cost + 1))
        return size * size
    def h(c):
        return abs(c // size - goal // size) + abs(c % size - goal % size) if algorithm == 'astar' else 0
    queue = [(h(start), 0, start)]
    best = {start: 0}
    while queue:
        _, cost, cell = heapq.heappop(queue)
        if cell == goal:
            return cost
        for nxt in neighbors(cell, size):
            if allowed(nxt) and cost + 1 < best.get(nxt, 10**6):
                best[nxt] = cost + 1
                heapq.heappush(queue, (cost + 1 + h(nxt), cost + 1, nxt))
    return size * size


def safe_escape_route(s: State) -> bool:
    """Sufficient escape proof on static terrain, including a warder who waits.

    Before prisoner move k the warder has had k moves. Both the departure
    square and arrival square must be outside that reach (except the exit).
    This deliberately rejects some winnable maps; it is not a full solver.
    """
    start = s.positions['prisoner']
    reach = {s.positions['warder']: 0}
    queue = deque(reach)
    while queue:
        cell = queue.popleft()
        for nxt in neighbors(cell, s.rules.size):
            if nxt not in reach and walkable(s, nxt, 'warder'):
                reach[nxt] = reach[cell] + 1
                queue.append(nxt)
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cell, moves = queue.popleft()
        next_move = moves + 1
        if reach.get(cell, 10**6) <= next_move:
            continue
        for nxt in neighbors(cell, s.rules.size):
            if not walkable(s, nxt, 'prisoner'):
                continue
            if nxt == s.real_tunnel:
                return True
            if nxt not in seen and reach.get(nxt, 10**6) > next_move:
                seen.add(nxt)
                queue.append((nxt, next_move))
    return False


def generate(rules: Rules, seed: int) -> State:
    rng = random.Random(seed)
    size = rules.size
    for _ in range(3000):
        cells = list(range(size * size))
        rng.shuffle(cells)
        count = {5: 5, 7: 10, 9: 16}[size]
        obstacles = set(cells[:count])
        tunnels = cells[count:count + (3 if 'fake' in rules.modifiers else 1)]
        floors = [c for c in cells if c not in obstacles and c not in tunnels]
        warders = [c for c in floors if all(abs(c // size - t // size) + abs(c % size - t % size) >= 3 for t in tunnels)]
        if not warders:
            continue
        w = rng.choice(warders)
        prisoners = [c for c in floors if c != w and abs(c // size - w // size) + abs(c % size - w % size) >= 2]
        if not prisoners:
            continue
        p = rng.choice(prisoners)
        key = rng.choice([c for c in floors if c not in (w, p)]) if 'key' in rules.modifiers else None
        s = State(deepcopy(rules), seed, ['#' if c in obstacles else 'T' if c in tunnels else '.' for c in range(size*size)], {'warder': w, 'prisoner': p}, tunnels, rng.choice(tunnels), key, key is None)
        s.charges = {role: {power: int(rules.powers in ('limited', 'both')) for power in powers} for role, powers in POWERS.items()}
        if not connected(s):
            continue
        # Multiple entrances reduce single-square exit control. Walking distance
        # to an approach matters more than the visual distance to the tunnel.
        approaches = [[n for n in neighbors(t, size) if walkable(s, n, 'warder')] for t in tunnels]
        if any(len(a) < 2 for a in approaches):
            continue
        if any(min(distance(s, w, n, 'warder') for n in a) < 2 for a in approaches):
            continue
        # Initial route-distance constraints are balance heuristics, not proof of fairness.
        if distance(s, p, key if key is not None else s.real_tunnel, 'prisoner') < 2:
            continue
        if rules.mode == 'stage' and not rules.modifiers and rules.powers == 'off' and not safe_escape_route(s):
            continue
        if rules.powers in ('pickups', 'both'):
            eligible = [c for c in floors if c not in (w, p, key)]
            rng.shuffle(eligible)
            power_list = [*POWERS['prisoner'], *POWERS['warder']]
            s.pickups = dict(zip(eligible[:5], power_list))
        return s
    raise ValueError('Could not generate a connected map; try another seed')


def shift_tunnels(s: State):
    """Public pressure rule: identical treatment of real and decoy tunnels."""
    if s.ply < s.shift_cooldown:
        s.tunnel_pressure = {}
        return
    for tunnel in list(s.tunnels):
        approaches = [n for n in neighbors(tunnel, s.rules.size) if walkable(s, n, 'warder')]
        near = bool(approaches) and min(distance(s, s.positions['warder'], n, 'warder') for n in approaches) <= 1
        count = s.tunnel_pressure.get(tunnel, 0) + 1 if near else 0
        s.tunnel_pressure[tunnel] = count
        if count == 2:
            s.last_event += ' Tunnel pressure: move away next turn to prevent a shift.'
        if count < 3:
            continue
        old_distance = distance(s, s.positions['prisoner'], tunnel, 'prisoner') if s.has_key else None
        candidates = [c for c, tile in enumerate(s.tiles) if tile == '.' and not protected(s, c) and c not in s.roadblocks]
        random.Random(s.seed + s.ply * 3571 + tunnel).shuffle(candidates)
        for cell in candidates:
            entrances = [n for n in neighbors(cell, s.rules.size) if walkable(s, n, 'warder')]
            if len(entrances) < 2 or min(distance(s, s.positions['warder'], n, 'warder') for n in entrances) < 2:
                continue
            prisoner_distance = distance(s, s.positions['prisoner'], cell, 'prisoner')
            if prisoner_distance < 3 or (old_distance is not None and abs(prisoner_distance-old_distance) > 2):
                continue
            old_real = s.real_tunnel
            s.tiles[tunnel], s.tiles[cell] = '.', 'T'
            s.tunnels[s.tunnels.index(tunnel)] = cell
            if old_real == tunnel:
                s.real_tunnel = cell
            if connected(s):
                s.tunnel_pressure = {}
                s.shift_cooldown = s.ply + 6
                s.last_event += ' Tunnel shifted. Camping spot expired!'
                return
            s.tiles[tunnel], s.tiles[cell] = 'T', '.'
            s.tunnels[s.tunnels.index(cell)] = tunnel
            s.real_tunnel = old_real
        s.last_event += ' Tunnel shift postponed: no suitable destination.'


def protected(s: State, cell: int) -> bool:
    return cell in s.positions.values() or cell in s.tunnels or cell == s.key or cell in s.pickups


def terminal(s: State):
    if s.positions['warder'] == s.positions['prisoner']:
        s.winner, s.reason = 'warder', 'The prisoner was caught.'
    elif s.has_key and s.positions['prisoner'] == s.real_tunnel:
        s.winner, s.reason = 'prisoner', 'The prisoner reached the real tunnel.'


def apply_action(original: State, action: dict, *, timeout: bool = False) -> State:
    if original.winner:
        raise ValueError('This match has finished')
    if not isinstance(action, dict):
        raise ValueError('Invalid action')
    s = replace(original, tiles=original.tiles.copy(), tunnels=original.tunnels.copy(), tunnel_pressure=original.tunnel_pressure.copy(), positions=original.positions.copy(), charges={r: c.copy() for r,c in original.charges.items()}, pickups=original.pickups.copy(), roadblocks=original.roadblocks.copy())
    role, kind = s.turn, action.get('kind', '')
    pos = s.positions[role]
    direction = action.get('direction', '')
    target = neighbor(pos, direction, s.rules.size)
    power = kind if kind in POWERS[role] else None
    if kind in [p for ps in POWERS.values() for p in ps] and power is None:
        raise ValueError('That power belongs to the other role')
    if power:
        if s.charges[role].get(power, 0) <= 0:
            raise ValueError('No charges remaining')
        s.charges[role][power] -= 1
    if kind in ('move', 'sprint'):
        steps = action.get('steps', 2) if kind == 'sprint' else 1
        if type(steps) is not int or steps not in (1, 2):
            raise ValueError('Sprint distance must be 1 or 2')
        for _ in range(steps):
            nxt = neighbor(s.positions[role], direction, s.rules.size)
            if nxt is None or not walkable(s, nxt, role):
                raise ValueError('That path is blocked')
            s.positions[role] = nxt
            if role == 'prisoner' and nxt == s.key:
                s.key, s.has_key = None, True
            pickup = s.pickups.get(nxt)
            if pickup in POWERS[role]:
                s.charges[role][pickup] += 1
                del s.pickups[nxt]
            terminal(s)
            if s.winner:
                break
    elif kind == 'dig':
        if target is None or s.tiles[target] != '#' or target in s.roadblocks:
            raise ValueError('Dig needs an adjacent permanent obstacle')
        s.tiles[target] = '.'
    elif kind == 'smoke':
        s.smoke_until = s.ply + 4
    elif kind == 'radar':
        s.radar_until = s.ply + 3
    elif kind == 'roadblock':
        if target is None or s.tiles[target] != '.' or target in s.roadblocks or protected(s, target):
            raise ValueError('Choose an adjacent empty floor')
        s.roadblocks[target] = s.ply + 4
        if not connected(s):
            raise ValueError('That roadblock would trap a player or objective')
    elif kind == 'shift':
        if 'shift' not in s.rules.modifiers:
            raise ValueError('Obstacle shifting is not enabled')
        dest = neighbor(target, direction, s.rules.size) if target is not None else None
        if target is None or s.tiles[target] != '#' or dest is None or s.tiles[dest] != '.' or dest in s.roadblocks or protected(s, dest):
            raise ValueError('Push an adjacent obstacle into an empty floor')
        s.tiles[target], s.tiles[dest] = '.', '#'
        if not connected(s):
            raise ValueError('That shift would trap a player or objective')
    elif kind == 'pass':
        if not timeout and any(neighbor(pos, d, s.rules.size) is not None and walkable(s, neighbor(pos, d, s.rules.size), role) for d in DIRECTIONS):
            raise ValueError('You can pass only when blocked or the timer expires')
    else:
        raise ValueError('Unknown action')
    s.last_event = f'{role.title()}: {"timeout" if timeout else kind}{" " + direction if direction else ""}.'
    s.ply += 1
    if not s.winner and role == 'warder' and 'relocate' in s.rules.modifiers:
        shift_tunnels(s)
    s.roadblocks = {c: end for c, end in s.roadblocks.items() if end > s.ply}
    if not s.winner and s.ply % 6 == 0 and 'shrink' in s.rules.modifiers:
        eligible = [i for i, t in enumerate(s.tiles) if t == '.' and i not in s.roadblocks and not protected(s, i)]
        random.Random(s.seed + s.ply * 997).shuffle(eligible)
        for cell in eligible:
            s.tiles[cell] = '#'
            if connected(s):
                s.last_event += ' A floor collapsed.'
                break
            s.tiles[cell] = '.'
    if not s.winner and 'shrink' in s.rules.modifiers and s.rounds >= 60:
        s.winner, s.reason = 'warder', 'Containment: the 60-round limit was reached.'
    s.turn = 'prisoner' if role == 'warder' else 'warder'
    return s


def candidate_actions(s: State) -> list[dict]:
    if s.winner:
        return []
    actions = [{'kind': 'move', 'direction': d} for d in DIRECTIONS]
    for power, count in s.charges[s.turn].items():
        if not count:
            continue
        if power in ('smoke', 'radar'):
            actions.append({'kind': power})
        else:
            actions.extend({'kind': power, 'direction': d} for d in DIRECTIONS)
    if 'shift' in s.rules.modifiers:
        actions.extend({'kind': 'shift', 'direction': d} for d in DIRECTIONS)
    return actions


def legal_actions(s: State) -> list[dict]:
    if s.winner:
        return []
    result = []
    for a in candidate_actions(s):
        try:
            apply_action(s, a)
            result.append(a)
        except ValueError:
            pass
    return result or [{'kind': 'pass'}]


def observation(s: State, role: str) -> dict:
    result = asdict(s)
    # Generation seed reconstructs secrets, so it is never in a live player view.
    result.pop('seed')
    visible = role == 'prisoner' or s.winner or s.smoke_until <= s.ply or s.radar_until > s.ply
    if not visible:
        result['positions']['prisoner'] = None
    if role != 'prisoner' and 'fake' in s.rules.modifiers and not s.winner:
        result['real_tunnel'] = None
    result.update(role=role, rounds=s.rounds, seconds=s.seconds)
    # Revealing legal actions could expose a hidden occupant through terrain powers.
    # Clients request actions; the authoritative engine validates them.
    return result


def determinize(view: dict, seed: int) -> State:
    """Sample an information-consistent state, never the actual private seed."""
    data = deepcopy(view)
    for k in ('role', 'rounds', 'seconds'):
        data.pop(k, None)
    rules = Rules(**data.pop('rules'))
    data['pickups'] = {int(k): v for k, v in data['pickups'].items()}
    data['roadblocks'] = {int(k): v for k, v in data['roadblocks'].items()}
    data['tunnel_pressure'] = {int(k): v for k, v in data.get('tunnel_pressure', {}).items()}
    rng = random.Random(seed)
    if data['real_tunnel'] is None:
        data['real_tunnel'] = rng.choice(data['tunnels'])
    if data['positions']['prisoner'] is None:
        candidates = [i for i, tile in enumerate(data['tiles']) if tile != '#' and i not in data['roadblocks'] and i != data['positions']['warder'] and (tile != 'T' or data['has_key'])]
        data['positions']['prisoner'] = rng.choice(candidates)
    return State(rules=rules, seed=seed, **data)
