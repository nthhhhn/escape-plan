import os
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from escapeplan import server
from escapeplan.engine import legal_actions

ADMIN_HEADERS = {'Authorization':'Bearer integration-test-token'}


def receive(ws,kind):
    for _ in range(40):
        msg=ws.receive_json()
        if msg['type']==kind:return msg
    raise AssertionError(f'Missing {kind}')


def identify(ws,name,token=None):
    ws.send_json({'type':'identify','payload':{'nickname':name,'token':token}})
    return receive(ws,'welcome')['payload']


def event(ws,kind,payload={},rid='r',**kw):
    ws.send_json({'type':kind,'request_id':rid,'payload':payload,**kw})


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DATA',tmp_path)
    monkeypatch.setenv('ADMIN_TOKEN','integration-test-token')
    with TestClient(server.app) as c:yield c


def test_two_clients_moves_dedupe_rematch_and_reset(client):
    with client.websocket_connect('/ws') as a, client.websocket_connect('/ws') as b:
        pa=identify(a,'Alice');pb=identify(b,'Bob')
        event(a,'create_room',{'mode':'classic','analysis':False},'create')
        room=receive(a,'room')['payload']
        event(b,'join_room',{'id':room['id']},'join')
        waiting_a=receive(a,'room')['payload'];waiting_b=receive(b,'room')['payload']
        assert waiting_a['phase']==waiting_b['phase']=='ready'
        event(a,'ready',rid='ready-a');receive(a,'room');receive(b,'room')
        event(b,'ready',rid='ready-b')
        va=receive(a,'room')['payload'];vb=receive(b,'room')['payload']
        assert va['phase']==vb['phase']=='countdown'
        assert va['state']['role']!=vb['state']['role']
        g=client.app.state.game;r=g.rooms[room['id']]
        r.phase='playing';r.deadline=time.monotonic()+10
        actor=a if r.roles['warder']==pa['id'] else b
        action=legal_actions(r.state)[0]
        event(actor,'action',action,'move1',match_id=r.match_id,turn_id=0)
        receive(a,'room');receive(b,'room')
        assert r.state.ply==1
        event(actor,'action',action,'move1',match_id=r.match_id,turn_id=0)
        # Read until matching ack; initial create/join acknowledgements may be queued.
        while True:
            msg=receive(actor,'ack')
            if msg.get('request_id')=='move1':break
        assert r.state.ply==1
        # Set up a known legal escape without relying on random game length.
        r.state.turn='prisoner';r.state.positions['prisoner']=23;r.state.positions['warder']=0
        r.state.tiles=['.']*24+['T'];r.state.tunnels=[24];r.state.real_tunnel=24;r.state.has_key=True
        prisoner=a if r.roles['prisoner']==pa['id'] else b
        winner=r.roles['prisoner']
        event(prisoner,'action',{'kind':'move','direction':'right'},'escape',match_id=r.match_id,turn_id=r.state.ply)
        end=receive(prisoner,'room')['payload']
        assert end['phase']=='finished' and g.players[winner].score==1
        # Drain other player's terminal state.
        receive(b if prisoner is a else a,'room')
        event(a,'rematch',rid='ra');receive(a,'room');receive(b,'room')
        event(b,'rematch',rid='rb');receive(a,'room');receive(b,'room')
        assert r.roles['warder']==winner and r.state.turn=='warder' and r.state.ply==0
        assert g.players[winner].score == 1
        assert sum(g.players[pid].score for pid in r.players) == 1
        # The same player wins the next round; the series score must accumulate.
        r.phase='playing';r.deadline=time.monotonic()+10
        r.state.positions['warder']=0;r.state.positions['prisoner']=1
        r.state.tiles=['.']*25
        repeat_winner=a if winner==pa['id'] else b
        event(repeat_winner,'action',{'kind':'move','direction':'right'},'round-two',match_id=r.match_id,turn_id=0)
        receive(a,'room');receive(b,'room')
        assert g.players[winner].score == 2
        assert sum(g.players[pid].score for pid in r.players) == 2
        assert client.get('/api/admin').status_code == 403
        admin = client.get('/api/admin',headers=ADMIN_HEADERS).json()
        assert admin['history'][0]['status'] == 'finished'
        assert admin['history'][0]['winner'] in ('Alice','Bob')
        assert client.post('/api/admin/reset',headers=ADMIN_HEADERS).status_code==200
        receive(a,'reset');receive(b,'reset')
        assert not g.rooms and all(p.score==0 for p in g.players.values())


def test_disconnect_resume_preserves_role_and_time(client):
    with client.websocket_connect('/ws') as a:
        pa=identify(a,'A')
        event(a,'create_room',{'mode':'classic','analysis':False},'create')
        room=receive(a,'room')['payload']
        with client.websocket_connect('/ws') as b:
            pb=identify(b,'B');event(b,'join_room',{'id':room['id']},'join')
            receive(a,'room');receive(b,'room')
            event(a,'ready',rid='ready-a');receive(a,'room');receive(b,'room')
            event(b,'ready',rid='ready-b');receive(a,'room');before=receive(b,'room')['payload']
            g=client.app.state.game;r=g.rooms[room['id']]
            r.phase='playing';r.deadline=time.monotonic()+10
        paused=receive(a,'room')['payload']
        assert paused['phase']=='paused'
        with client.websocket_connect('/ws') as b2:
            resumed=identify(b2,'B',pb['token'])
            assert resumed['id']==pb['id']
            after=receive(b2,'room')['payload']
            assert after['phase']=='playing' and after['state']['role']==before['state']['role']


def test_skip_stage_aborts_without_award_and_starts_next(client):
    with client.websocket_connect('/ws') as ws:
        player = identify(ws, 'Skipper')
        event(ws, 'create_room', {'mode':'stage','bot':'easy','player_role':'prisoner'}, 'create')
        view = receive(ws, 'room')['payload']
        event(ws, 'ready', rid='ready')
        receive(ws, 'room')
        game = client.app.state.game
        room = game.rooms[view['id']]
        old_match = room.match_id
        event(ws, 'skip_stage', rid='skip')
        next_view = receive(ws, 'room')['payload']
        assert next_view['rules']['stage'] == 2
        assert next_view['phase'] == 'countdown'
        assert room.match_id != old_match
        assert game.store.db.execute('SELECT status,winner FROM matches WHERE id=?', (old_match,)).fetchone() == ('aborted', None)
        assert game.players[player['id']].score == game.players[player['id']].progress == 0
        room.rules.stage = 9
        event(ws, 'skip_stage', rid='final-skip')
        assert receive(ws, 'room')['payload']['phase'] == 'aborted'
        assert game.players[player['id']].progress == 0


def test_websocket_rejects_cross_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws',headers={'origin':'https://untrusted.example'}):pass


def test_admin_can_disconnect_client_and_cancel_room(client):
    with client.websocket_connect('/ws') as a, client.websocket_connect('/ws') as b:
        pa=identify(a,'Alice');identify(b,'Bob')
        event(a,'create_room',{'mode':'classic','analysis':False},'create')
        room=receive(a,'room')['payload']
        event(b,'join_room',{'id':room['id']},'join')
        receive(a,'room');receive(b,'room')
        response=client.post(f"/api/admin/clients/{pa['id']}/disconnect",headers=ADMIN_HEADERS)
        assert response.status_code==200
        assert receive(a,'kicked')['payload']['message'].startswith('You were disconnected')
        closed=receive(b,'room_closed')['payload']
        assert 'game was cancelled' in closed['message']
        assert not client.app.state.game.rooms
        admin=client.get('/api/admin',headers=ADMIN_HEADERS).json()
        assert [p['name'] for p in admin['clients']]==['Bob']


def test_admin_can_reset_one_game_without_affecting_another(client):
    with client.websocket_connect('/ws') as a, client.websocket_connect('/ws') as b, client.websocket_connect('/ws') as c:
        pa=identify(a,'Alice');pb=identify(b,'Bob');pc=identify(c,'Carol')
        event(a,'create_room',{'mode':'classic','analysis':False},'create-a')
        first=receive(a,'room')['payload']
        event(b,'join_room',{'id':first['id']},'join-b')
        receive(a,'room');receive(b,'room')
        event(a,'ready',rid='ready-a');receive(a,'room');receive(b,'room')
        event(b,'ready',rid='ready-b');receive(a,'room');receive(b,'room')
        event(c,'create_room',{'mode':'classic','analysis':False},'create-c')
        second=receive(c,'room')['payload']
        game=client.app.state.game
        for pid,score in ((pa['id'],4),(pb['id'],5),(pc['id'],7)):
            game.players[pid].score=score
            game.store.db.execute('UPDATE players SET score=? WHERE id=?',(score,pid))
        game.store.db.commit()

        response=client.post(f"/api/admin/rooms/{first['id']}/reset",headers=ADMIN_HEADERS)
        assert response.status_code==200
        assert 'was reset by the host' in receive(a,'reset')['payload']['message']
        assert 'was reset by the host' in receive(b,'reset')['payload']['message']
        assert first['id'] not in game.rooms and second['id'] in game.rooms
        assert game.players[pa['id']].score==game.players[pb['id']].score==0
        assert game.players[pc['id']].score==7 and game.players[pc['id']].room==second['id']
        saved=dict(game.store.db.execute('SELECT id,score FROM players'))
        assert saved[pa['id']]==saved[pb['id']]==0 and saved[pc['id']]==7
        history=game.store.match_history()
        assert history[0]['reason']=='Game reset by server'


def wait_until(client, predicate):
    import asyncio

    async def check():
        for _ in range(200):
            if predicate():
                return
            await asyncio.sleep(.01)
        raise AssertionError('Server did not reach the expected state')

    client.portal.call(check)


@pytest.mark.parametrize('phase', ['waiting', 'ready', 'finished', 'aborted'])
def test_abandoned_rooms_do_not_exhaust_capacity(client, phase):
    game = client.app.state.game
    for index in range(13):
        with client.websocket_connect('/ws') as ws:
            player = identify(ws, f'Player {index}')
            event(ws, 'create_room', {'mode': 'classic'} if phase == 'waiting' else
                  {'mode': 'stage', 'bot': 'easy'}, f'create-{index}')
            view = receive(ws, 'room')['payload']
            room = game.rooms[view['id']]
            # Isolate terminal cleanup from the separately tested game rules.
            room.phase = phase
            bot_ids = [pid for pid in room.players if pid.startswith('bot-')]
        wait_until(client, lambda: view['id'] not in game.rooms)
        assert game.players[player['id']].room is None
        assert all(pid not in game.players for pid in bot_ids)
    assert not game.rooms


def test_empty_active_room_keeps_reconnect_window_then_releases_capacity(client):
    game = client.app.state.game
    with client.websocket_connect('/ws') as ws:
        player = identify(ws, 'Solo')
        event(ws, 'create_room', {'mode': 'stage', 'bot': 'easy'}, 'create')
        view = receive(ws, 'room')['payload']
        event(ws, 'ready', rid='ready')
        receive(ws, 'room')
        room = game.rooms[view['id']]
        match_id = room.match_id
    wait_until(client, lambda: room.phase == 'paused')
    assert view['id'] in game.rooms
    # Returning before expiry must retain the original match and role.
    with client.websocket_connect('/ws') as resumed:
        identify(resumed, 'Solo', player['token'])
        restored = receive(resumed, 'room')['payload']
        assert restored['match_id'] == match_id
        assert restored['phase'] == 'countdown'
    wait_until(client, lambda: room.phase == 'paused')
    room.disconnected_at = time.monotonic() - 21
    wait_until(client, lambda: view['id'] not in game.rooms)
    assert game.players[player['id']].room is None
    assert game.store.db.execute('SELECT status,winner FROM matches WHERE id=?',
                                 (match_id,)).fetchone() == ('aborted', None)


def test_finished_room_is_retained_for_connected_player(client):
    game = client.app.state.game
    with client.websocket_connect('/ws') as a:
        pa = identify(a, 'Alice')
        event(a, 'create_room', {'mode': 'classic'}, 'create')
        view = receive(a, 'room')['payload']
        with client.websocket_connect('/ws') as b:
            pb = identify(b, 'Bob')
            event(b, 'join_room', {'id': view['id']}, 'join')
            receive(a, 'room'); receive(b, 'room')
            game.rooms[view['id']].phase = 'finished'
        wait_until(client, lambda: game.players[pb['id']].socket is None)
        assert view['id'] in game.rooms
        assert game.players[pa['id']].room == view['id']
    wait_until(client, lambda: view['id'] not in game.rooms)
    assert game.players[pa['id']].room is game.players[pb['id']].room is None


def test_source_defined_endpoint_accepts_trusted_frontend_origin(client):
    origin = 'http://localhost:5173'
    with client.websocket_connect('/ws', headers={'origin': origin}) as ws:
        assert identify(ws, 'LAN player')['nickname'] == 'LAN player'
    response = client.options('/api/admin/reset', headers={
        'Origin': origin, 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin
    response = client.get('/api/training', headers={'Origin': origin})
    assert response.headers['access-control-allow-origin'] == origin
    # Cross-origin access never bypasses the admin token check.
    assert client.post('/api/admin/reset', headers={'Origin': origin}).status_code == 403
    rejected = client.options('/api/admin/reset', headers={
        'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'POST'})
    assert rejected.status_code == 400
    assert 'access-control-allow-origin' not in rejected.headers


def test_fresh_server_seeds_pretrained_q_policy(client):
    game = client.app.state.game
    model = __import__('json').loads((server.DATA/'q-model.json').read_text())
    status = client.get('/api/training').json()
    assert status['status'] == 'complete'
    assert model['episodes'] == status['episodes'] == 5000
    assert model['coverage'] == status['coverage'] == {
        'size': 5, 'modifiers': [], 'powers': 'off',
        'personality': 'planner', 'schema': 2,
    }
    assert len(model['q']) == status['states'] == 21954
    assert game.training is None


PLAYER_ROOM_KEYS={'id','match_id','phase','rules','state','players','ready','activity','coaches','deadline','remaining','rematch','analysis','bot_info','map_metrics'}


def start_classic(client,a,b):
    pa=identify(a,'Alice');pb=identify(b,'Bob')
    event(a,'create_room',{'mode':'classic','analysis':False},'create')
    room=receive(a,'room')['payload']
    event(b,'join_room',{'id':room['id']},'join')
    receive(a,'room');receive(b,'room')
    event(a,'ready',rid='ready-a');receive(a,'room');receive(b,'room')
    event(b,'ready',rid='ready-b');receive(a,'room');receive(b,'room')
    game=client.app.state.game;r=game.rooms[room['id']]
    r.phase='playing';r.deadline=time.monotonic()+10
    return pa,pb,game,r


def test_admin_rooms_include_live_board_with_full_information(client):
    with client.websocket_connect('/ws') as a, client.websocket_connect('/ws') as b:
        pa,pb,game,r=start_classic(client,a,b)
        names={pa['id']:'Alice',pb['id']:'Bob'}
        entry=next(x for x in client.get('/api/admin',headers=ADMIN_HEADERS).json()['rooms'] if x['id']==r.id)
        assert entry['size']==5 and entry['ply']==0 and entry['turn']=='warder' and entry['round']==0
        assert entry['roles']=={'warder':names[r.roles['warder']],'prisoner':names[r.roles['prisoner']]}
        board=entry['board']
        assert len(board['tiles'])==25 and board['tiles']==r.state.tiles
        assert board['positions']==r.state.positions and board['real_tunnel']==r.state.real_tunnel
        assert board['tunnels']==r.state.tunnels and board['role'] is None
        assert 'seed' not in board
        warder=a if r.roles['warder']==pa['id'] else b
        action=legal_actions(r.state)[0]
        event(warder,'action',action,'m1',match_id=r.match_id,turn_id=0)
        receive(a,'room');receive(b,'room')
        moved=next(x for x in client.get('/api/admin',headers=ADMIN_HEADERS).json()['rooms'] if x['id']==r.id)
        assert moved['ply']==1 and moved['turn']=='prisoner'
        assert moved['board']['positions']==r.state.positions


def test_admin_board_does_not_leak_into_player_room_messages(client):
    with client.websocket_connect('/ws') as a, client.websocket_connect('/ws') as b:
        pa,pb,game,r=start_classic(client,a,b)
        # Hide the prisoner (Smoke) and the real exit (False exits) from the warder.
        r.state.rules.modifiers.append('fake');r.state.smoke_until=r.state.ply+4
        warder_ws,prisoner_ws=(a,b) if r.roles['warder']==pa['id'] else (b,a)
        event(warder_ws,'action',legal_actions(r.state)[0],'m1',match_id=r.match_id,turn_id=0)
        warder_view=receive(warder_ws,'room')['payload'];prisoner_view=receive(prisoner_ws,'room')['payload']
        for view in (warder_view,prisoner_view):
            assert set(view)==PLAYER_ROOM_KEYS
            assert 'seed' not in view['state']
        assert warder_view['state']['positions']['prisoner'] is None
        assert warder_view['state']['real_tunnel'] is None
        assert prisoner_view['state']['positions']['prisoner']==r.state.positions['prisoner']
        board=next(x for x in client.get('/api/admin',headers=ADMIN_HEADERS).json()['rooms'] if x['id']==r.id)['board']
        assert board['positions']['prisoner']==r.state.positions['prisoner'] is not None
        assert board['real_tunnel']==r.state.real_tunnel is not None
        # Lobby broadcasts never carry boards either.
        assert all('board' not in room and 'state' not in room for room in game.lobby()['rooms'])


def test_admin_board_requires_admin_token(client):
    assert client.get('/api/admin').status_code==403
    assert client.get('/api/admin',headers={'Authorization':'Bearer wrong'}).status_code==403
