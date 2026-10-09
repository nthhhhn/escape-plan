"""Independent fixed-point reference uses the actual game engine for edges."""
import random
from copy import deepcopy
from escapeplan.engine import Rules, State, apply_action, DIRECTIONS, generate
from map_lab.solver import Solver, canonical_key


def make_state(solver,w,p,turn):
    return State(Rules(mode='special',size=solver.size),0,list(solver.tiles),
        {'warder':solver.cells[w],'prisoner':solver.cells[p]},[solver.cells[solver.exit]],
        solver.cells[solver.exit],has_key=True,turn=('warder','prisoner')[turn],
        charges={'warder':{},'prisoner':{}})


def engine_edges(solver,sid):
    w,p,t=solver.decode(sid)
    if w==p or p==solver.exit:return []
    state=make_state(solver,w,p,t)
    edges=[]
    for action in [{'kind':'move','direction':d} for d in DIRECTIONS]+[{'kind':'pass'}]:
        try:
            nxt=apply_action(state,action,timeout=action['kind']=='pass')
        except ValueError:continue
        edges.append(solver.sid(solver.index[nxt.positions['warder']],solver.index[nxt.positions['prisoner']],1-t))
    return edges


def reference(solver):
    states=list(solver.states())
    edges={s:engine_edges(solver,s) for s in states}
    resolved={}
    for s in states:
        w,p,_=solver.decode(s)
        if w==p:resolved[s]=1
        elif p==solver.exit:resolved[s]=2
    changed=True
    while changed:
        changed=False
        for s in states:
            if s in resolved:continue
            actor=s%2+1
            if any(resolved.get(c)==actor for c in edges[s]):
                resolved[s]=actor;changed=True
            elif edges[s] and all(resolved.get(c)==3-actor for c in edges[s]):
                resolved[s]=3-actor;changed=True
    return edges,{s:resolved.get(s,0) for s in states}


def test_exhaustive_three_by_three_layouts():
    # All 256 wall patterns with the exit fixed at 8; all legal spawns/turns.
    cycles=0
    for mask in range(256):
        tiles=['#' if mask&(1<<c) else '.' for c in range(8)]+['T']
        if tiles.count('.')==0:continue
        solver=Solver(tiles,3)
        edges,outcomes=reference(solver)
        for sid in solver.states():
            assert set(solver.children(sid))==set(edges[sid])
            assert solver.outcome[sid]==outcomes[sid]
            cycles+=outcomes[sid]==0
        assert solver.verify()
    assert cycles>0


def test_generated_boards_engine_and_proof_lines():
    from map_lab.generate import validate_trace
    for size in (5,7,9):
        state=generate(Rules(mode='special',size=size),71500+size)
        solver=Solver(state.tiles,size)
        assert solver.verify()
        rng=random.Random(size)
        states=list(solver.states())
        for sid in rng.sample(states, min(100,len(states))):
            assert set(engine_edges(solver,sid))==set(solver.children(sid))
        decisive=[s for s in states if solver.remoteness[s]>0]
        for sid in rng.sample(decisive,min(20,len(decisive))):
            trace=solver.proof_trace(sid)
            assert len(trace)-1==solver.remoteness[sid]
            validate_trace(solver,trace)


def test_rotation_reflection_deduplication():
    tiles=list('.#....#.T');size=3
    rotated=['']*9
    for i,t in enumerate(tiles):
        r,c=divmod(i,size);rotated[c*size+size-1-r]=t
    assert canonical_key(tiles,size)==canonical_key(rotated,size)
    different=list('..#...#.T')
    assert canonical_key(tiles,size)!=canonical_key(different,size)


def test_independent_route_counts():
    open_board=Solver(list('........T'),3)
    assert open_board.independent_routes(open_board.index[0])==2
    corridor=Solver(list('.##.##..T'),3)
    assert corridor.independent_routes(corridor.index[0])==1
