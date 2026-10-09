from __future__ import annotations
import asyncio
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .engine import Rules, State, generate, apply_action, observation, legal_actions
from .ai import choose, analyze_pair, train
from .storage import Store

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get('ESCAPE_DATA', str(ROOT/'data')))
# Bonjour publishes this host on the local network; this setting does not
# register DNS or change the WebSocket origin checks. The Mac launcher passes
# its actual hostname so a rename or Bonjour conflict can be reflected here.
LAN_HOST = os.environ.get('ESCAPE_LAN_HOST', 'escape-plan15.local')
LAN_URL = f'http://{LAN_HOST}:8000'


@dataclass
class Player:
    id: str
    name: str
    socket: WebSocket | None = None
    room: str | None = None
    score: int = 0
    progress: int = 0
    rate_start: float = 0
    rate_count: int = 0


@dataclass
class Room:
    id: str
    rules: Rules
    players: list[str]
    state: State | None = None
    roles: dict[str, str] = field(default_factory=dict)
    phase: str = 'waiting'
    match_id: str = ''
    deadline: float = 0
    remaining: float = 10
    disconnected_at: float = 0
    rematch: set[str] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    bot_busy: bool = False
    analysis_busy: set[str] = field(default_factory=set)
    estimates: dict = field(default_factory=dict)
    previous: dict = field(default_factory=dict)
    last_actor: str = ''
    bot_info: dict = field(default_factory=dict)
    map_metrics: dict = field(default_factory=dict)
    ready: set[str] = field(default_factory=set)
    activity: list[str] = field(default_factory=list)
    paused_phase: str = 'playing'
    coaches: dict = field(default_factory=dict)


def bot_name(rules):
    if rules.bot == 'easy': return 'Rookie'
    if rules.bot == 'qlearning': return 'The Trainee'
    return {'pursuer': 'Chaser', 'planner': 'Mastermind', 'trickster': 'Wildcard'}[rules.personality]


class GameServer:
    def __init__(self):
        self.store = Store(DATA)
        token_file = DATA/'admin-token'
        if not token_file.exists():
            token_file.write_text(secrets.token_urlsafe(32))
            token_file.chmod(0o600)
        self.admin_token = os.environ.get('ADMIN_TOKEN') or token_file.read_text().strip()
        self.players: dict[str, Player] = {}
        self.connections: dict[WebSocket, str | None] = {}
        self.rooms: dict[str, Room] = {}
        self.responses: OrderedDict = OrderedDict()
        self.bot_pool = ProcessPoolExecutor(max_workers=1)
        self.analysis_pool = ProcessPoolExecutor(max_workers=1)
        self.training_pool = ProcessPoolExecutor(max_workers=1)
        self.analysis_slots = asyncio.Semaphore(1)
        self.bot_slots = asyncio.Semaphore(1)
        self.training = None
        self.tasks = set()
        # An interrupted training job cannot remain falsely "running" forever.
        path = DATA/'training.json'
        if path.exists():
            status = json.loads(path.read_text())
            if status.get('status') == 'running':
                status['status'] = 'interrupted'
                path.write_text(json.dumps(status))

    def task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def send(self, ws, kind, payload, **extra):
        try:
            await asyncio.wait_for(ws.send_json({'type': kind, 'payload': payload, 'server_time': time.time(), **extra}), timeout=2)
        except (RuntimeError, OSError, asyncio.TimeoutError, WebSocketDisconnect):
            pass

    def lobby(self):
        online = []
        for ws, pid in self.connections.items():
            p = self.players.get(pid)
            online.append({'id': pid or f'connecting-{id(ws)}', 'name': p.name if p else 'Connecting…', 'room': p.room if p else None})
        return {'online': online, 'rooms': [{'id': r.id, 'mode': r.rules.mode, 'size': r.rules.size, 'players': [self.players[p].name for p in r.players], 'phase': r.phase, 'rules': asdict(r.rules)} for r in self.rooms.values() if not r.rules.bot and r.phase == 'waiting']}

    async def broadcast_lobby(self):
        data = self.lobby()
        await asyncio.gather(*(self.send(ws, 'lobby', data) for ws in list(self.connections)))

    def room_view(self, room, pid):
        role = next((role for role, p in room.roles.items() if p == pid), None)
        return {'id': room.id, 'match_id': room.match_id, 'phase': room.phase, 'rules': asdict(room.rules), 'state': observation(room.state, role) if room.state and role else None, 'players': [{'id': p, 'name': self.players[p].name, 'score': self.players[p].score, 'role': next((role for role, player in room.roles.items() if player == p), None), 'online': self.players[p].socket is not None or p.startswith('bot-')} for p in room.players], 'ready': list(room.ready), 'activity': room.activity[-12:], 'coaches': room.coaches.get(pid), 'deadline': time.time()+max(0,room.deadline-time.monotonic()) if room.phase in ('playing','countdown') else None, 'remaining': room.remaining, 'rematch': list(room.rematch), 'analysis': room.estimates.get(pid), 'bot_info': room.bot_info, 'map_metrics': {'method': room.map_metrics.get('method','distance heuristics')}}

    async def publish(self, room):
        await asyncio.gather(*(self.send(self.players[pid].socket, 'room', self.room_view(room,pid)) for pid in room.players if self.players[pid].socket))

    async def start(self, room, winner=None):
        if room.rules.mode == 'stage':
            seed = 10000 + room.rules.stage*100 + room.rules.size
            room.map_metrics = {'method': 'fixed stage seed; safe escape route checked for static stages without powers or modifiers'}
        else:
            seed, room.map_metrics = self.store.pick_map(room.rules)
        room.state = generate(room.rules, seed)
        self.store.reset_scores(room.players)
        for pid in room.players:
            self.players[pid].score = 0
        room.match_id = uuid4().hex
        warder = winner if winner in room.players else secrets.choice(room.players)
        if winner is None and room.rules.bot and room.rules.player_role != 'random':
            human = next(p for p in room.players if not p.startswith('bot-'))
            warder = human if room.rules.player_role == 'warder' else next(p for p in room.players if p.startswith('bot-'))
        room.roles = {'warder': warder, 'prisoner': next(p for p in room.players if p != warder)}
        room.phase = 'countdown'
        room.deadline = time.monotonic()+3
        room.activity.append('Both players ready. 3, 2, 1…')
        if room.rules.bot:
            bot = next(p for p in room.players if p.startswith('bot-'))
            self.players[bot].name = bot_name(room.rules)
        room.rematch.clear()
        room.previous.clear()
        room.estimates.clear()
        room.coaches.clear()
        room.bot_info.clear()
        self.store.start(room.match_id,room.state,room.roles)
        await self.publish(room)

    async def transition(self, room, action, timeout=False):
        state = room.state
        previous = {pid: observation(state, role) for role,pid in room.roles.items() if not pid.startswith('bot-')}
        next_state = apply_action(state, action, timeout=timeout)
        if room.rules.analysis and not room.roles[state.turn].startswith('bot-'):
            pid = room.roles[state.turn]
            self.task(self.coach_move(room, pid, room.match_id, next_state.ply, previous[pid], observation(next_state, state.turn), state.turn))
        room.previous = previous
        room.last_actor = room.roles[state.turn]
        room.state = next_state
        room.estimates.clear()
        self.store.action(room.match_id,next_state,action)
        if next_state.winner:
            room.phase = 'finished'
            winner = room.roles[next_state.winner]
            stage = room.rules.stage if room.rules.mode == 'stage' else 0
            if self.store.finish(room.match_id,winner,next_state.reason,stage):
                p = self.players[winner]
                p.score += 1
                p.progress = max(p.progress,stage)
            if room.rules.bot:
                room.rematch.add(next(p for p in room.players if p.startswith('bot-')))
        else:
            room.deadline = time.monotonic()+next_state.seconds
        await self.publish(room)

    async def bot_move(self, room, mid, ply):
        room.bot_busy = True
        try:
            async with self.bot_slots:
                if room.match_id != mid or room.phase != 'playing' or room.state.ply != ply:
                    return
                view = observation(room.state,room.state.turn)
                result = await asyncio.get_running_loop().run_in_executor(self.bot_pool,choose,view,room.rules.bot,secrets.randbelow(2**31),str(DATA/'q-model.json'))
                async with room.lock:
                    if room.match_id != mid or room.phase != 'playing' or room.state.ply != ply or time.monotonic() >= room.deadline:
                        return
                    room.bot_info = {k:v for k,v in result.items() if k != 'action'}
                    try:
                        await self.transition(room,result['action'])
                    except ValueError:
                        # A sampled hidden position can invalidate a terrain action. Try a
                        # non-secret-dependent ordinary move; never give the bot private state.
                        view = observation(room.state,room.state.turn)
                        for direction in ('up','right','down','left'):
                            try:
                                await self.transition(room,{'kind':'move','direction':direction})
                                break
                            except ValueError:
                                continue
                        else:
                            await self.transition(room,{'kind':'pass'},timeout=True)
        except Exception as exc:
            room.bot_info = {'error': type(exc).__name__, 'policy': room.rules.bot}
        finally:
            room.bot_busy = False

    async def coach_move(self, room, pid, mid, ply, before, after, role):
        async with self.analysis_slots:
            if room.match_id != mid or room.phase == 'aborted':
                return
            result = await asyncio.get_running_loop().run_in_executor(self.analysis_pool, analyze_pair, before, after, role, ply*127+13)
            if room.match_id == mid and room.phase != 'aborted' and ply >= room.coaches.get(pid, {}).get('ply', -1):
                room.coaches[pid] = {'ply': ply, 'coach': result['coach']}
                await self.publish(room)

    async def analysis(self, room, pid, mid, ply):
        room.analysis_busy.add(pid)
        try:
            async with self.analysis_slots:
                if room.match_id != mid or room.state.ply != ply or room.phase != 'playing':
                    return
                role = next(r for r,p in room.roles.items() if p == pid)
                current = observation(room.state,role)
                before = None
                result = await asyncio.get_running_loop().run_in_executor(self.analysis_pool,analyze_pair,before,current,role,ply*127+13)
                if room.match_id == mid and room.state.ply == ply and room.phase == 'playing':
                    room.estimates[pid] = result
                    if self.players[pid].socket:
                        await self.send(self.players[pid].socket,'analysis',{'match_id':mid,'ply':ply,**result})
        finally:
            room.analysis_busy.discard(pid)

    async def ticker(self):
        while True:
            await asyncio.sleep(.1)
            for room in list(self.rooms.values()):
                if room.phase == 'paused' and time.monotonic()-room.disconnected_at >= 20:
                    async with room.lock:
                        room.phase = 'aborted'
                        self.store.finish(room.match_id,None,'Reconnect window expired')
                        await self.publish(room)
                if room.phase == 'countdown' and time.monotonic() >= room.deadline:
                    async with room.lock:
                        if room.phase == 'countdown':
                            room.phase = 'playing'
                            room.deadline = time.monotonic()+room.state.seconds
                            room.activity.append('GO! The warder moves first.')
                            await self.publish(room)
                if room.phase != 'playing':
                    continue
                if time.monotonic() >= room.deadline:
                    async with room.lock:
                        if room.phase == 'playing' and time.monotonic() >= room.deadline:
                            await self.transition(room,{'kind':'pass'},timeout=True)
                    continue
                if room.roles[room.state.turn].startswith('bot-') and not room.bot_busy:
                    room.bot_busy = True
                    self.task(self.bot_move(room,room.match_id,room.state.ply))
                if room.rules.analysis:
                    for pid in room.players:
                        if not pid.startswith('bot-') and pid not in room.analysis_busy and pid not in room.estimates:
                            room.analysis_busy.add(pid)
                            self.task(self.analysis(room,pid,room.match_id,room.state.ply))

    async def leave(self, p):
        room = self.rooms.get(p.room)
        if room:
            async with room.lock:
                if room.phase in ('playing','paused','countdown','ready'):
                    self.store.finish(room.match_id,None,'Player left')
                    room.phase = 'aborted'
                    await self.publish(room)
                room.players = [pid for pid in room.players if pid != p.id]
                if not room.players or all(pid.startswith('bot-') for pid in room.players) or room.phase == 'waiting':
                    self.rooms.pop(room.id,None)
                else:
                    await self.publish(room)
        p.room = None
        if p.socket:
            await self.send(p.socket,'left',{})
        await self.broadcast_lobby()

    async def handle(self, p, message):
        kind = message.get('type')
        payload = message.get('payload',{})
        if not isinstance(payload,dict):
            raise ValueError('Invalid payload')
        if kind == 'ping':
            return {'pong': payload.get('time')}
        if kind == 'leave_room':
            await self.leave(p)
            return {}
        if kind == 'create_room':
            if p.room:
                raise ValueError('Leave the current room first')
            if len(self.rooms) >= 12:
                raise ValueError('Server room limit reached')
            rules = Rules.parse(payload)
            rid = secrets.token_hex(3).upper()
            room = Room(rid,rules,[p.id])
            room.activity.append(f'{p.name} created the room.')
            self.rooms[rid],p.room = room,rid
            if rules.bot:
                bid = f'bot-{rid}'
                score,progress = self.store.player(bid,bot_name(rules))
                self.players[bid] = Player(bid,bot_name(rules),room=rid,score=score,progress=progress)
                room.players.append(bid)
                room.ready.add(bid)
                room.phase = 'ready'
                room.activity.append(f'{bot_name(rules)} joined the room.')
                await self.publish(room)
            else:
                await self.publish(room)
            await self.broadcast_lobby()
            return {}
        if kind == 'join_room':
            if p.room:
                raise ValueError('Leave the current room first')
            room = self.rooms.get(str(payload.get('id','')).upper())
            if not room or room.phase != 'waiting' or len(room.players) != 1:
                raise ValueError('Room is no longer available')
            async with room.lock:
                room.players.append(p.id)
                p.room = room.id
                room.phase = 'ready'
                room.activity.append(f'{p.name} joined the room.')
                await self.publish(room)
            await self.broadcast_lobby()
            return {}
        room = self.rooms.get(p.room)
        if not room:
            raise ValueError('Join a room first')
        async with room.lock:
            if kind == 'ready':
                if room.phase != 'ready' or len(room.players) != 2:
                    raise ValueError('Room is not ready to start')
                if not all(self.players[pid].socket or pid.startswith('bot-') for pid in room.players):
                    raise ValueError('Wait for both players to connect')
                if p.id not in room.ready:
                    room.ready.add(p.id)
                    room.activity.append(f'{p.name} is ready.')
                if all(pid in room.ready for pid in room.players):
                    await self.start(room)
                else:
                    await self.publish(room)
            elif kind == 'action':
                if room.phase != 'playing' or message.get('match_id') != room.match_id or message.get('turn_id') != room.state.ply:
                    raise ValueError('This turn is no longer active')
                if room.roles[room.state.turn] != p.id:
                    raise ValueError('Wait for your turn')
                if time.monotonic() >= room.deadline:
                    await self.transition(room,{'kind':'pass'},timeout=True)
                    raise ValueError('The turn expired')
                await self.transition(room,payload)
            elif kind == 'rematch':
                if room.phase != 'finished' or len(room.players) != 2:
                    raise ValueError('Rematch is not available')
                room.rematch.add(p.id)
                if all(pid in room.rematch for pid in room.players):
                    await self.start(room,room.roles[room.state.winner])
                else:
                    await self.publish(room)
            elif kind in ('next_stage', 'skip_stage'):
                if kind == 'skip_stage':
                    if room.rules.mode != 'stage' or not room.rules.bot or room.phase not in ('playing', 'countdown', 'finished', 'ready'):
                        raise ValueError('Skipping is available only in solo stages')
                    if room.match_id:
                        self.store.finish(room.match_id, None, 'Stage skipped')
                    room.activity.append(f'Stage {room.rules.stage} skipped. No win or progress awarded.')
                    if room.rules.stage >= 9:
                        room.phase = 'aborted'
                        await self.publish(room)
                        return {}
                elif room.rules.mode != 'stage' or room.phase != 'finished' or room.roles[room.state.winner] != p.id:
                    raise ValueError('Win this stage first')
                if room.rules.stage >= 9:
                    raise ValueError('All nine stages complete')
                room.rules.stage += 1
                room.rules.size = (5,7,9)[(room.rules.stage-1)//3]
                room.rules.bot = ('easy','bfs','hard')[(room.rules.stage-1)%3]
                room.rules.personality = 'planner' if room.rules.bot == 'hard' else 'pursuer'
                await self.start(room)
            else:
                raise ValueError('Unknown event')
        return {}


@asynccontextmanager
async def lifespan(app):
    g = GameServer()
    app.state.game = g
    g.task(g.ticker())
    yield
    for task in list(g.tasks):
        task.cancel()
    await asyncio.gather(*g.tasks,return_exceptions=True)
    for pool in (g.bot_pool,g.analysis_pool,g.training_pool):
        pool.shutdown(wait=False,cancel_futures=True)
    g.store.db.close()


app = FastAPI(title='Escape Plan',lifespan=lifespan)


def admin(request: Request, authorization: str | None):
    expected = request.app.state.game.admin_token
    if not authorization or not secrets.compare_digest(authorization, 'Bearer '+expected):
        raise HTTPException(403,'Server admin token required')
    return request.app.state.game


@app.get('/api/health')
def health():
    return {'status':'ok','transport':'native-websocket','workers':1,'lan_url':LAN_URL}


@app.get('/api/training')
def training_status():
    path = DATA/'training.json'
    return json.loads(path.read_text()) if path.exists() else {'status':'not_started','metrics':[]}


@app.post('/api/admin/train')
async def start_training(request: Request, authorization: str | None = Header(default=None)):
    g = admin(request,authorization)
    if g.training and not g.training.done():
        raise HTTPException(409,'Training is already running')
    body = await request.json()
    episodes = body.get('episodes',200)
    if type(episodes) is not int or not 20 <= episodes <= 2000:
        raise HTTPException(400,'Use 20 to 2000 episodes')
    try:
        rules = Rules.parse(body.get('rules',{'mode':'stage'}))
    except (TypeError,ValueError) as exc:
        raise HTTPException(400,str(exc))
    async def run():
        try:
            result = await asyncio.get_running_loop().run_in_executor(g.training_pool,train,str(DATA),episodes,asdict(rules),42)
            g.store.db.execute('INSERT INTO training_runs(result) VALUES (?)',(json.dumps(result),))
            g.store.db.commit()
        except Exception as exc:
            (DATA/'training.json').write_text(json.dumps({'status':'failed','error':type(exc).__name__,'metrics':[]}))
    g.training = g.task(run())
    return {'status':'starting'}


@app.get('/api/admin')
def dashboard(request: Request, authorization: str | None = Header(default=None)):
    g = admin(request,authorization)
    return {'clients':g.lobby()['online'],'rooms':[{'id':r.id,'phase':r.phase,'mode':r.rules.mode,'round':r.state.rounds if r.state else 0,'players':[g.players[p].name for p in r.players]} for r in g.rooms.values()], 'map_candidates':g.store.db.execute('SELECT COUNT(*) FROM maps').fetchone()[0], 'matches':g.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0], 'training_running': bool(g.training and not g.training.done())}


@app.post('/api/admin/reset')
async def reset(request: Request, authorization: str | None = Header(default=None)):
    g = admin(request,authorization)
    for room in list(g.rooms.values()):
        async with room.lock:
            room.phase = 'aborted'
            room.match_id = ''
    g.rooms.clear()
    g.store.reset()
    for p in g.players.values():
        p.score,p.room = 0,None
    await asyncio.gather(*(g.send(ws,'reset',{}) for ws in list(g.connections)))
    await g.broadcast_lobby()
    return {'status':'reset'}


@app.websocket('/ws')
async def websocket(ws: WebSocket):
    # Reject cross-site browser socket hijacking. Same-origin works through Vite/proxy.
    origin = ws.headers.get('origin')
    host = ws.headers.get('host')
    allowed = os.environ.get('ALLOWED_ORIGINS','').split(',')
    from urllib.parse import urlparse
    if origin and urlparse(origin).netloc != host and origin not in allowed:
        await ws.close(code=1008)
        return
    await ws.accept()
    g: GameServer = ws.app.state.game
    g.connections[ws] = None
    p = None
    try:
        await g.send(ws,'connected',g.lobby())
        await g.broadcast_lobby()
        message = await asyncio.wait_for(ws.receive_json(),timeout=30)
        if not isinstance(message,dict) or message.get('type') != 'identify':
            await ws.close(code=1008)
            return
        payload = message.get('payload',{})
        name = str(payload.get('nickname','')).strip()[:24]
        if not name:
            raise ValueError('Enter a nickname')
        token = payload.get('token')
        if not isinstance(token,str) or len(token) != 43:
            token = secrets.token_urlsafe(32)
        pid = hashlib.sha256(token.encode()).hexdigest()[:24]
        score,progress = g.store.player(pid,name)
        p = g.players.get(pid) or Player(pid,name,score=score,progress=progress)
        if p.socket and p.socket is not ws:
            await p.socket.close(code=4001)
        p.socket,p.name = ws,name
        g.players[pid] = p
        g.connections[ws] = pid
        await g.send(ws,'welcome',{'id':pid,'token':token,'nickname':name,'score':p.score,'progress':p.progress})
        room = g.rooms.get(p.room)
        if room:
            async with room.lock:
                if room.phase == 'paused' and all(g.players[i].socket or i.startswith('bot-') for i in room.players):
                    room.phase = room.paused_phase
                    room.deadline = time.monotonic()+(3 if room.phase == 'countdown' else room.remaining)
                await g.publish(room)
        await g.broadcast_lobby()
        while True:
            message = await ws.receive_json()
            if not isinstance(message,dict):
                continue
            rid = message.get('request_id')
            if not isinstance(rid,str) or not 1 <= len(rid) <= 80:
                await g.send(ws,'error',{'message':'A request ID is required'})
                continue
            cache_key = (pid,rid)
            if cache_key in g.responses:
                await g.send(ws,'ack',g.responses[cache_key],request_id=rid)
                continue
            now = time.monotonic()
            if now-p.rate_start > 1:
                p.rate_start,p.rate_count = now,0
            p.rate_count += 1
            try:
                if p.rate_count > 25:
                    raise ValueError('Too many requests; wait a moment')
                result = await g.handle(p,message)
                response = {'ok':True,**result}
            except (ValueError,TypeError,KeyError) as exc:
                response = {'ok':False,'message':str(exc)}
            g.responses[cache_key] = response
            while len(g.responses) > 3000:
                g.responses.popitem(last=False)
            await g.send(ws,'ack',response,request_id=rid)
    except (WebSocketDisconnect,asyncio.TimeoutError,RuntimeError,ValueError):
        pass
    finally:
        # ASGI shutdown may cancel the socket handler while peers still need a pause.
        await asyncio.shield(disconnect(g, ws, p))


async def disconnect(g, ws, p):
    g.connections.pop(ws,None)
    if p and p.socket is ws:
        p.socket = None
        room = g.rooms.get(p.room)
        if room:
            async with room.lock:
                if room.phase in ('playing','countdown'):
                    room.paused_phase = room.phase
                    room.remaining = max(0,room.deadline-time.monotonic())
                    room.disconnected_at = time.monotonic()
                    room.phase = 'paused'
                elif room.phase == 'ready':
                    room.ready.discard(p.id)
                elif room.phase == 'waiting':
                    g.rooms.pop(room.id,None)
                    p.room = None
                await g.publish(room)
    await g.broadcast_lobby()



DIST = ROOT/'frontend'/'dist'
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/{path:path}')
    def frontend(path: str):
        return FileResponse(DIST/'index.html')
