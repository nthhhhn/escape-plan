"""Audit every stored demonstration and re-solve every showcased scenario.

Produces an analysis-only compressed SQLite snapshot for GitHub handoff.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time

from escapeplan.engine import Rules, State, apply_action, DIRECTIONS
from map_lab.solver import Solver, NAMES, canonical_key
from map_lab.generate import ROOT


def audit(database,output):
    started=time.monotonic()
    db=sqlite3.connect(database)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    selected=json.loads((output/'showcase-data.json').read_text())
    selected_by_id={m['id']:m for m in selected['maps']}
    assert len(selected_by_id)==90
    counts=Counter();moves=0;waits=0;canonical=set();verified_showcase=0
    for row in db.execute('SELECT id,size,canonical,winner,scenario,metrics,trace,verified FROM maps ORDER BY id'):
        identifier,size,key,winner,scenario_json,metrics_json,trace_json,verified=row
        scenario,metrics,trace=map(json.loads,(scenario_json,metrics_json,trace_json))
        assert verified==1 and scenario['size']==size
        assert key==canonical_key(scenario['tiles'],size) and key not in canonical
        canonical.add(key)
        assert len(trace)==metrics['plies']+1 and 4<=metrics['plies']<=80
        assert trace[0]['warder']==scenario['positions']['warder'] and trace[0]['prisoner']==scenario['positions']['prisoner']
        assert trace[0]['turn']=='warder'
        state=State(Rules(mode='special',size=size),scenario['seed'],scenario['tiles'],dict(scenario['positions']),
            [scenario['tunnel']],scenario['tunnel'],has_key=True,charges={'warder':{},'prisoner':{}})
        for index,frame in enumerate(trace):
            assert frame['remaining']==len(trace)-1-index
            assert state.positions=={'warder':frame['warder'],'prisoner':frame['prisoner']}
            assert state.turn==frame['turn']
            if index==len(trace)-1:
                assert state.winner==winner and frame['choices']==[]
                break
            assert state.winner is None
            nxt=trace[index+1]
            origin=state.positions[state.turn];target=nxt[state.turn]
            if origin==target:
                state=apply_action(state,{'kind':'pass'},timeout=True);waits+=1
            else:
                delta=(target//size-origin//size,target%size-origin%size)
                direction=next(d for d,v in DIRECTIONS.items() if v==delta)
                state=apply_action(state,{'kind':'move','direction':direction})
            moves+=1
        counts[(size,winner)]+=1
        if identifier in selected_by_id:
            item=selected_by_id[identifier]
            assert item['scenario']==scenario and item['trace']==trace and item['metrics']==metrics
            solver=Solver(scenario['tiles'],size)
            assert solver.verify()
            initial=solver.sid(solver.index[scenario['positions']['warder']],solver.index[scenario['positions']['prisoner']],0)
            assert NAMES[solver.outcome[initial]]==winner
            assert solver.remoteness[initial]==metrics['plies']
            for frame in trace:
                sid=solver.sid(solver.index[frame['warder']],solver.index[frame['prisoner']],frame['turn']=='prisoner')
                children=solver.children(sid)
                assert len(children)==len(frame['choices'])
                for choice in frame['choices']:
                    target=solver.index[choice['cell']]
                    w,p,t=solver.decode(sid)
                    child=solver.sid(w,target,0) if t else solver.sid(target,p,1)
                    assert child in children
                    assert NAMES[solver.outcome[child]]==choice['winner'] and solver.remoteness[child]==choice['remaining']
            verified_showcase+=1
    for size in (5,7,9):
        maps=[m for m in selected['maps'] if m['scenario']['size']==size]
        assert len(maps)==30
        assert [m['percentile'] for m in maps]==sorted(m['percentile'] for m in maps)
        assert Counter(m['winner'] for m in maps)=={'warder':15,'prisoner':15}
    assert verified_showcase==90
    snapshot=output/'map-pool.sqlite3.gz'
    # SQLite's backup API makes a consistent, complete snapshot (including WAL).
    # Convert the snapshot to rollback-journal format so it needs no WAL sidecar
    # and can also be deserialized into memory by the restore verifier.
    with tempfile.TemporaryDirectory(prefix='escape-map-snapshot-') as directory:
        backup=sqlite3.connect(str(Path(directory)/'pool.sqlite3'))
        db.backup(backup)
        assert backup.execute('PRAGMA journal_mode=DELETE').fetchone()[0]=='delete'
        raw=backup.serialize()
        backup.close()
    check=sqlite3.connect(':memory:')
    check.deserialize(raw)
    assert check.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    check.close()
    with gzip.open(snapshot,'wb',compresslevel=9) as stream:stream.write(raw)
    report={'records':sum(counts.values()),'unique_layouts':len(canonical),'demonstration_moves':moves,'timeout_waits':waits,
        'showcase_maps_resolved_again':verified_showcase,'groups':[{'size':s,'winner':w,'count':c} for (s,w),c in sorted(counts.items())],
        'database_integrity':'ok','all_traces_engine_validated':True,'seconds':round(time.monotonic()-started,2),
        'snapshot_bytes':snapshot.stat().st_size,'uncompressed_bytes':len(raw),'sqlite_sha256':hashlib.sha256(raw).hexdigest()}
    (output/'validation-report.json').write_text(json.dumps(report,indent=2))
    db.close()
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',type=Path,default=ROOT/'data'/'map-lab-pool.sqlite3')
    parser.add_argument('--output',type=Path,default=ROOT/'map-showcase')
    args=parser.parse_args()
    audit(args.database,args.output)
