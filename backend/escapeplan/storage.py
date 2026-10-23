from __future__ import annotations
import json
import sqlite3
import random
import time
from pathlib import Path
from dataclasses import asdict
from .engine import Rules, generate, distance


class Store:
    def __init__(self, directory: Path):
        self.root = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory/'escapeplan.sqlite3', check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, nickname TEXT, score INTEGER DEFAULT 0, progress INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, seed INTEGER, rules TEXT, players TEXT, status TEXT, winner TEXT, reason TEXT, room_id TEXT, started_at REAL, finished_at REAL);
        CREATE TABLE IF NOT EXISTS actions (match_id TEXT, ply INTEGER, action TEXT, PRIMARY KEY(match_id, ply));
        CREATE TABLE IF NOT EXISTS maps (pool TEXT, seed INTEGER, metrics TEXT, PRIMARY KEY(pool, seed));
        CREATE TABLE IF NOT EXISTS training_runs (id INTEGER PRIMARY KEY, result TEXT);
        PRAGMA user_version=2;
        ''')
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(matches)')}
        for name, kind in (('room_id','TEXT'), ('started_at','REAL'), ('finished_at','REAL')):
            if name not in columns:
                self.db.execute(f'ALTER TABLE matches ADD COLUMN {name} {kind}')
        self.db.execute("UPDATE matches SET status='aborted', reason='Server restarted' WHERE status='running'")
        self.db.commit()

    def player(self, pid, nickname):
        self.db.execute('INSERT INTO players(id,nickname) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET nickname=excluded.nickname', (pid,nickname))
        self.db.commit()
        return self.db.execute('SELECT score,progress FROM players WHERE id=?', (pid,)).fetchone()

    def start(self, mid, state, players, room_id=None):
        self.db.execute('INSERT INTO matches(id,seed,rules,players,status,winner,reason,room_id,started_at,finished_at) VALUES (?,?,?,?,?,?,?,?,?,?)', (mid,state.seed,json.dumps(asdict(state.rules)),json.dumps(players),'running',None,None,room_id,time.time(),None))
        self.db.commit()

    def action(self, mid, state, action):
        self.db.execute('INSERT OR IGNORE INTO actions VALUES (?,?,?)', (mid,state.ply,json.dumps(action)))
        self.db.commit()

    def finish(self, mid, winner, reason, stage=0):
        with self.db:
            cursor = self.db.execute("UPDATE matches SET status=?,winner=?,reason=?,finished_at=? WHERE id=? AND status='running'", ('finished' if winner else 'aborted',winner,reason,time.time(),mid))
            if cursor.rowcount and winner:
                self.db.execute('UPDATE players SET score=score+1,progress=MAX(progress,?) WHERE id=?', (stage,winner))
        return bool(cursor.rowcount)

    def reset_scores(self, players):
        with self.db:
            self.db.executemany('UPDATE players SET score=0 WHERE id=?', [(pid,) for pid in players])

    def reset(self):
        with self.db:
            self.db.execute('UPDATE players SET score=0')
            self.db.execute("UPDATE matches SET status='aborted',reason='Admin reset',finished_at=? WHERE status='running'", (time.time(),))

    def match_history(self, limit=50):
        rows = self.db.execute("SELECT id,rules,players,status,winner,reason,room_id,started_at,finished_at FROM matches WHERE status != 'running' ORDER BY COALESCE(finished_at,started_at,0) DESC LIMIT ?", (limit,)).fetchall()
        names = dict(self.db.execute('SELECT id,nickname FROM players'))
        history = []
        for mid, rules_json, players_json, status, winner, reason, room_id, started_at, finished_at in rows:
            roles = json.loads(players_json)
            history.append({
                'id': mid,
                'room': room_id,
                'mode': json.loads(rules_json).get('mode','classic'),
                'players': [{'id': pid, 'name': names.get(pid,pid), 'role': role} for role,pid in roles.items()],
                'status': status,
                'winner': names.get(winner,winner) if winner else None,
                'reason': reason,
                'started_at': started_at,
                'finished_at': finished_at,
            })
        return history

    def pick_map(self, rules: Rules) -> tuple[int, dict]:
        signature = json.dumps([2, rules.size, sorted(rules.modifiers), rules.powers])
        rows = self.db.execute('SELECT seed,metrics FROM maps WHERE pool=?', (signature,)).fetchall()
        rng = random.SystemRandom()
        while len(rows) < 100:
            seed = rng.randrange(1, 2**31)
            s = generate(rules, seed)
            metrics = {'prisoner_to_objective': distance(s,s.positions['prisoner'],s.key if s.key is not None else s.real_tunnel,'prisoner'), 'warder_to_prisoner': distance(s,s.positions['warder'],s.positions['prisoner'],'warder'), 'validation': 'connected; multiple tunnel approaches; warder >=2 walking steps from approaches', 'method': 'distance heuristics; not guaranteed fair'}
            self.db.execute('INSERT OR IGNORE INTO maps VALUES (?,?,?)', (signature,seed,json.dumps(metrics)))
            rows.append((seed,json.dumps(metrics)))
        selected = rng.choice(rows)
        # Consume it; next selection replenishes to 100 with a newly generated layout.
        self.db.execute('DELETE FROM maps WHERE pool=? AND seed=?', (signature,selected[0]))
        self.db.commit()
        return selected[0], json.loads(selected[1])
