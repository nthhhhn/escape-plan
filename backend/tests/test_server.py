import os
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from escapeplan import server
from escapeplan.engine import legal_actions


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
        assert all(g.players[pid].score == 0 for pid in r.players)
        assert client.post('/api/admin/reset').status_code==403
        assert client.post('/api/admin/reset',headers={'Authorization':'Bearer integration-test-token'}).status_code==200
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
