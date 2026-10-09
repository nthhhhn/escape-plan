import json
from copy import deepcopy
import pytest
from escapeplan.engine import Rules, State, generate, connected, apply_action, legal_actions, observation, determinize
from escapeplan.ai import choose, rollout, train
from escapeplan.storage import Store
from escapeplan.engine import safe_escape_route


def test_static_stages_have_a_safe_escape_opening():
    for stage in range(1, 10):
        size = (5, 7, 9)[(stage - 1) // 3]
        state = generate(Rules(mode='stage', size=size, stage=stage), 10000 + stage*100 + size)
        assert safe_escape_route(state)


def test_safe_route_accounts_for_warder_first_and_camping():
    state = arena(powers='off')
    state.positions = {'warder': 0, 'prisoner': 23}
    assert safe_escape_route(state)
    state.positions['warder'] = 22
    assert not safe_escape_route(state)  # Captured before the first prisoner move.


def test_score_reset_preserves_progress_and_other_players(tmp_path):
    store = Store(tmp_path)
    for pid in ('a', 'b', 'other'):
        store.player(pid, pid)
    store.db.execute('UPDATE players SET score=4,progress=3')
    store.db.commit()
    store.reset_scores(['a', 'b'])
    assert store.player('a', 'a') == (0, 3)
    assert store.player('b', 'b') == (0, 3)
    assert store.player('other', 'other') == (4, 3)
    store.db.close()


def arena(modifiers=(), powers='both'):
    r=Rules(mode='special',modifiers=list(modifiers),powers=powers)
    return State(r,123,['.']*24+['T'],{'warder':0,'prisoner':12},[24],24,has_key=True,charges={'warder':{'radar':1,'roadblock':1},'prisoner':{'dig':1,'sprint':1,'smoke':1}})


@pytest.mark.parametrize('size,count',[(5,5),(7,10),(9,16)])
@pytest.mark.parametrize('mods',[[],['key','fake','shift','shrink','timer']])
def test_generated_maps(size,count,mods):
    for seed in range(15):
        s=generate(Rules(mode='special',size=size,modifiers=mods,powers='both'),seed)
        assert s.tiles.count('#')==count
        assert len(s.tunnels)==(3 if 'fake' in mods else 1)
        assert connected(s)
        assert s.positions['warder']!=s.positions['prisoner']
        assert not set(s.positions.values())&set(s.tunnels)
        assert s.turn=='warder'


def test_classic_cannot_enable_extras():
    r=Rules.parse({'mode':'classic','size':9,'bot':'hard','powers':'both','modifiers':['fake']})
    assert (r.size,r.bot,r.powers,r.modifiers)==(5,'','off',[])
    s=generate(r,1)
    assert s.tiles.count('.')==19


def test_moves_capture_escape_and_immutability():
    s=arena();s.positions['prisoner']=1
    end=apply_action(s,{'kind':'move','direction':'right'})
    assert end.winner=='warder' and s.positions['warder']==0
    with pytest.raises(ValueError): apply_action(end,{'kind':'move','direction':'down'})
    s=arena();s.turn='prisoner';s.positions['prisoner']=23
    assert apply_action(s,{'kind':'move','direction':'right'}).winner=='prisoner'
    s.turn='warder';s.positions['warder']=23
    with pytest.raises(ValueError):apply_action(s,{'kind':'move','direction':'right'})


def test_no_wrap_and_blocked_moves():
    s=arena();s.positions['warder']=4
    with pytest.raises(ValueError):apply_action(s,{'kind':'move','direction':'right'})
    s.tiles[9]='#'
    with pytest.raises(ValueError):apply_action(s,{'kind':'move','direction':'down'})


def test_smoke_and_radar_timing_and_privacy():
    s=arena(['fake']);s.tunnels=[22,23,24];s.tiles[22]=s.tiles[23]='T';s.turn='prisoner';s.ply=1
    s=apply_action(s,{'kind':'smoke'})
    view=observation(s,'warder')
    assert view['positions']['prisoner'] is None
    assert view['real_tunnel'] is None and 'seed' not in view
    assert observation(s,'prisoner')['positions']['prisoner']==12
    sample=determinize(json.loads(json.dumps(view)),20)
    assert sample.real_tunnel in s.tunnels
    s=apply_action(s,{'kind':'radar'})
    assert observation(s,'warder')['positions']['prisoner']==12
    assert observation(s,'warder')['real_tunnel'] is None
    s=apply_action(s,{'kind':'move','direction':'left'})
    assert s.radar_until>s.ply
    s=apply_action(s,{'kind':'move','direction':'down'})
    assert s.radar_until<=s.ply


def test_smoke_hides_next_movement_and_following_warder_turn():
    s=arena();s.turn='prisoner';s.ply=1
    s=apply_action(s,{'kind':'smoke'})
    assert observation(s,'warder')['positions']['prisoner'] is None
    s=apply_action(s,{'kind':'move','direction':'right'})
    s=apply_action(s,{'kind':'move','direction':'left'})
    assert observation(s,'warder')['positions']['prisoner'] is None
    s=apply_action(s,{'kind':'move','direction':'down'})
    assert observation(s,'warder')['positions']['prisoner'] is not None


def test_tunnel_pressure_warns_and_relocates_after_three_warder_turns():
    s=arena(['relocate']);s.positions={'warder':23,'prisoner':12}
    old=s.real_tunnel
    s=apply_action(s,{'kind':'pass'},timeout=True)
    s=apply_action(s,{'kind':'pass'},timeout=True)
    s=apply_action(s,{'kind':'pass'},timeout=True)
    assert s.tunnel_pressure[old]==2 and 'Tunnel pressure' in s.last_event
    s=apply_action(s,{'kind':'pass'},timeout=True)
    s=apply_action(s,{'kind':'pass'},timeout=True)
    assert s.real_tunnel!=old and 'Camping spot expired' in s.last_event
    assert s.shift_cooldown>s.ply


def test_key_fake_tunnels_and_sprint_collision():
    s=arena(['fake','key']);s.tunnels=[22,23,24];s.tiles[22]=s.tiles[23]='T';s.key=17;s.has_key=False;s.turn='prisoner';s.positions['prisoner']=12
    s=apply_action(s,{'kind':'sprint','direction':'down'})
    assert s.positions['prisoner']==22 and s.has_key and not s.winner
    s=arena();s.turn='prisoner';s.positions['prisoner']=10;s.positions['warder']=11
    s=apply_action(s,{'kind':'sprint','direction':'right'})
    assert s.winner=='warder' and s.positions['prisoner']==11


def test_sprint_rolls_back_if_second_step_blocked():
    s=arena();s.turn='prisoner';s.tiles[14]='#'
    with pytest.raises(ValueError):apply_action(s,{'kind':'sprint','direction':'right'})
    assert s.positions['prisoner']==12 and s.charges['prisoner']['sprint']==1


def test_dig_pickup_roadblock_and_shift():
    s=arena(['shift']);s.turn='prisoner';s.tiles[13]='#'
    s=apply_action(s,{'kind':'dig','direction':'right'})
    assert s.tiles[13]=='.' and s.charges['prisoner']['dig']==0
    s=apply_action(s,{'kind':'roadblock','direction':'right'})
    assert 1 in s.roadblocks
    for _ in range(4):s=apply_action(s,{'kind':'pass'},timeout=True)
    assert 1 not in s.roadblocks
    s=arena(['shift']);s.tiles[1]='#'
    s=apply_action(s,{'kind':'shift','direction':'right'})
    assert s.tiles[1]=='.' and s.tiles[2]=='#' and s.positions['warder']==0
    s=arena();s.turn='prisoner';s.pickups={13:'sprint'}
    s=apply_action(s,{'kind':'move','direction':'right'})
    assert s.charges['prisoner']['sprint']==2 and not s.pickups


def test_terrain_cannot_isolate_floor():
    s=arena();s.tiles[5]='#'
    with pytest.raises(ValueError):apply_action(s,{'kind':'roadblock','direction':'right'})
    assert not s.roadblocks


def test_shrink_timer_and_containment():
    s=arena(['shrink','timer']);s.ply=5;s.turn='prisoner'
    s=apply_action(s,{'kind':'pass'},timeout=True)
    assert s.tiles.count('#')==1 and connected(s) and s.seconds==9
    s.ply=119;s.turn='prisoner'
    s=apply_action(s,{'kind':'pass'},timeout=True)
    assert s.winner=='warder' and s.seconds==5


def test_full_modifier_simulation_is_deterministic():
    s=generate(Rules(mode='special',modifiers=['shift','fake','key','shrink','timer'],powers='both'),72)
    import random
    rng=random.Random(22)
    for _ in range(120):
        if s.winner:break
        a=rng.choice(legal_actions(s))
        assert apply_action(s,a)==apply_action(s,a)
        s=apply_action(s,a)
        assert connected(s)
    assert s.winner is not None


@pytest.mark.parametrize('policy',['easy','bfs','astar','hard','qlearning'])
def test_ai_returns_valid_action(policy):
    s=generate(Rules(mode='stage',bot=policy),31)
    result=choose(observation(s,s.turn),policy,99,budget=.1)
    assert result['action'] in legal_actions(s)
    assert result['elapsed_ms']<2000


def test_rollout_counts_censored_outcomes():
    s=arena()
    result=rollout(observation(s,'prisoner'),10,count=20,horizon=8,budget=5)
    assert result['samples']==20
    assert result['warder']+result['prisoner']+result['unresolved']==20


def test_training_generates_real_checkpoint(tmp_path):
    result=train(str(tmp_path),20,{'mode':'stage','size':5,'bot':'qlearning'},42)
    model=json.loads((tmp_path/'q-model.json').read_text())
    assert result['status']=='complete' and result['completed']==20
    assert len(model['q'])>0 and result['metrics'][-1]['samples']==20
    assert (tmp_path/'training.json').exists()


def test_storage_results_are_idempotent_and_pool_is_persisted(tmp_path):
    store=Store(tmp_path)
    store.player('a','Alice');store.player('b','Bob')
    seed,metrics=store.pick_map(Rules())
    assert store.db.execute('SELECT COUNT(*) FROM maps').fetchone()[0]==99
    assert metrics['prisoner_to_objective']>=2
    state=generate(Rules(),seed)
    store.start('m',state,{'warder':'a','prisoner':'b'})
    assert store.finish('m','a','caught')
    assert not store.finish('m','a','caught')
    assert store.player('a','Alice')[0]==1
    store.reset();assert store.player('a','Alice')[0]==0
    store.db.close()
