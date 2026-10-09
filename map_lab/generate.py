"""Resumable offline SQLite pool and standalone showcase export."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
import random
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timezone

from escapeplan.engine import Rules, State, generate, apply_action, DIRECTIONS
from map_lab.solver import Solver, NAMES, VERSION, canonical_key

ROOT=Path(__file__).resolve().parents[1]


def validate_trace(solver,trace):
    w,p,turn=solver.decode(trace[0])
    state=State(Rules(mode='special',size=solver.size),0,list(solver.tiles),
        {'warder':solver.cells[w],'prisoner':solver.cells[p]},[solver.cells[solver.exit]],
        solver.cells[solver.exit],has_key=True,turn=NAMES[turn+1],charges={'warder':{},'prisoner':{}})
    for sid in trace[1:]:
        w,p,_=solver.decode(sid)
        target=solver.cells[w if state.turn=='warder' else p]
        current=state.positions[state.turn]
        if target==current:
            state=apply_action(state,{'kind':'pass'},timeout=True)
        else:
            delta=(target//solver.size-current//solver.size,target%solver.size-current%solver.size)
            direction=next(d for d,v in DIRECTIONS.items() if v==delta)
            state=apply_action(state,{'kind':'move','direction':direction})
        assert state.positions=={'warder':solver.cells[w],'prisoner':solver.cells[p]}
    assert state.winner==NAMES[solver.outcome[trace[0]]]
    return True


def connect(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS maps (
        id TEXT PRIMARY KEY, size INTEGER NOT NULL, seed INTEGER NOT NULL,
        canonical TEXT NOT NULL UNIQUE, winner TEXT NOT NULL, raw_difficulty REAL NOT NULL,
        percentile REAL DEFAULT 0, difficulty TEXT DEFAULT '', scenario TEXT NOT NULL,
        metrics TEXT NOT NULL, trace TEXT NOT NULL, solver_version TEXT NOT NULL,
        verified INTEGER NOT NULL, created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS maps_rank ON maps(size,winner,raw_difficulty);
    CREATE TABLE IF NOT EXISTS progress (
        size INTEGER PRIMARY KEY, next_seed INTEGER NOT NULL, attempts INTEGER DEFAULT 0,
        rejected TEXT NOT NULL, elapsed_seconds REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
    ''')
    versions=db.execute('SELECT DISTINCT solver_version FROM maps').fetchall()
    if any(v[0]!=VERSION for v in versions):raise ValueError('Database belongs to another solver version; use a new database path')
    db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('rules',json.dumps({'powers':'off','modifiers':[],
        'warder_first':True,'allow_wait':'timeout pass','visibility':'full','objective':'capture or escape',
        'scope':'independent offline pool; not installed in live map selection'})))
    db.commit()
    return db


def build(db,size,target,max_attempts):
    row=db.execute('SELECT next_seed,attempts,rejected,elapsed_seconds FROM progress WHERE size=?',(size,)).fetchone()
    seed,attempts,rejected,elapsed=(row[0],row[1],Counter(json.loads(row[2])),row[3]) if row else (15000000+size*100000,0,Counter(),0.)
    count=db.execute('SELECT COUNT(*) FROM maps WHERE size=?',(size,)).fetchone()[0]
    role_counts=Counter(dict(db.execute('SELECT winner,COUNT(*) FROM maps WHERE size=? GROUP BY winner',(size,)).fetchall()))
    started=time.monotonic();since=0
    def checkpoint():
        db.execute('INSERT OR REPLACE INTO progress VALUES (?,?,?,?,?)',(size,seed,attempts,json.dumps(rejected),elapsed+time.monotonic()-started))
        db.commit()
    try:
        while count<target and since<max_attempts:
            trial_seed=seed;seed+=1;attempts+=1;since+=1
            state=generate(Rules(mode='special',size=size),trial_seed)
            key=canonical_key(state.tiles,size)
            if db.execute('SELECT 1 FROM maps WHERE canonical=?',(key,)).fetchone():
                rejected['duplicate_layout']+=1;continue
            solver=Solver(state.tiles,size)
            # Evaluate complete scenarios, not terrain in isolation. Prefer the
            # underrepresented winning role; fall back if that terrain has none.
            eligible={1:[],2:[]}
            for w in solver.valid:
                wc=solver.cells[w];exitcell=state.real_tunnel
                if abs(wc//size-exitcell//size)+abs(wc%size-exitcell%size)<3:continue
                if min(solver.wdist[w][a] for a in solver.adj[solver.exit])<2:continue
                for p in solver.valid:
                    pc=solver.cells[p]
                    if abs(wc//size-pc//size)+abs(wc%size-pc%size)<2 or solver.pdist[p][solver.exit]<2:continue
                    sid=solver.sid(w,p,0)
                    if solver.outcome[sid] and 4<=solver.remoteness[sid]<=80:
                        eligible[solver.outcome[sid]].append(sid)
            desired=1 if role_counts['warder']<role_counts['prisoner'] else 2
            candidates=eligible[desired] or eligible[3-desired]
            if not candidates:
                rejected['no_decisive_nontrivial_start']+=1;continue
            solver.verify()
            rng=random.Random(trial_seed)
            sampled=rng.sample(candidates,min(3,len(candidates)))
            evaluated=[]
            for start in sampled:
                trace=solver.proof_trace(start)
                features,frames=solver.features(start,trace)
                evaluated.append((features['raw_difficulty'],start,trace,features,frames))
            # Alternate easiest/median/hardest of three to retain variety.
            evaluated.sort(key=lambda item:item[0])
            _,start,trace,features,frames=evaluated[min(count%3,len(evaluated)-1)]
            validate_trace(solver,trace)
            w,p,_=solver.decode(start)
            state.positions={'warder':solver.cells[w],'prisoner':solver.cells[p]}
            features['spawn_candidates']=len(candidates)
            features['spawn_samples']=len(sampled)
            scenario={'size':size,'tiles':state.tiles,'positions':state.positions,'tunnel':state.real_tunnel,
                'turn':'warder','seed':trial_seed,'powers':'off','modifiers':[],'allow_wait':True}
            identifier=f'{size}-{trial_seed}'
            db.execute('INSERT INTO maps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (identifier,size,trial_seed,key,NAMES[solver.outcome[start]],features['raw_difficulty'],0,'',
                 json.dumps(scenario),json.dumps(features),json.dumps(frames),VERSION,1,datetime.now(timezone.utc).isoformat()))
            count+=1
            role_counts[NAMES[solver.outcome[start]]]+=1
            if count%100==0:
                checkpoint()
                print(json.dumps({'size':size,'accepted':count,'attempts':attempts,'rejected':dict(rejected),
                    'seconds_this_run':round(time.monotonic()-started,2)}),flush=True)
    finally:checkpoint()
    print(json.dumps({'size':size,'complete':count>=target,'accepted':count,'attempts':attempts,
        'seconds_total':round(elapsed+time.monotonic()-started,2)}),flush=True)


def rank(db):
    for size,winner in db.execute('SELECT DISTINCT size,winner FROM maps').fetchall():
        rows=db.execute('SELECT id,raw_difficulty FROM maps WHERE size=? AND winner=? ORDER BY raw_difficulty,id',(size,winner)).fetchall()
        # Midranks give identical raw scores the same percentile.
        i=0
        while i<len(rows):
            j=i+1
            while j<len(rows) and rows[j][1]==rows[i][1]:j+=1
            percentile=100*((i+j-1)/2)/max(1,len(rows)-1)
            label='Easy' if percentile<33.333 else 'Medium' if percentile<66.667 else 'Hard'
            db.executemany('UPDATE maps SET percentile=?,difficulty=? WHERE id=?',[(round(percentile,2),label,row[0]) for row in rows[i:j]])
            i=j
    db.commit()


def export(db,directory):
    directory.mkdir(parents=True,exist_ok=True)
    chosen=[];summary=[]
    for size in (5,7,9):
        counts=dict(db.execute('SELECT winner,COUNT(*) FROM maps WHERE size=? GROUP BY winner',(size,)).fetchall())
        progress=db.execute('SELECT attempts,rejected,elapsed_seconds FROM progress WHERE size=?',(size,)).fetchone()
        summary.append({'size':size,'total':sum(counts.values()),'outcomes':counts,'attempts':progress[0] if progress else 0,
            'rejected':json.loads(progress[1]) if progress else {},'seconds':round(progress[2],2) if progress else 0})
        for winner in ('prisoner','warder'):
            rows=db.execute('SELECT id,percentile,difficulty,scenario,metrics,trace FROM maps WHERE size=? AND winner=? ORDER BY raw_difficulty,id',(size,winner)).fetchall()
            if len(rows)<15:raise ValueError(f'Need 15 distinct {winner} wins for {size}x{size}; currently {len(rows)}')
            for i in range(15):
                row=rows[round(i*(len(rows)-1)/14)]
                chosen.append({'id':row[0],'percentile':row[1],'difficulty':row[2],'scenario':json.loads(row[3]),
                    'metrics':json.loads(row[4]),'trace':json.loads(row[5]),'winner':winner})
    chosen.sort(key=lambda m:(m['scenario']['size'],m['percentile'],m['metrics']['raw_difficulty'],m['id']))
    payload={'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'summary':summary,'maps':chosen,
        'human_validated':False,'rules':json.loads(db.execute("SELECT value FROM metadata WHERE key='rules'").fetchone()[0])}
    (directory/'showcase-data.json').write_text(json.dumps(payload,separators=(',',':')))
    template=(ROOT/'map_lab'/'showcase.template.html').read_text()
    (directory/'index.html').write_text(template.replace('/*__MAP_DATA__*/',json.dumps(payload,separators=(',',':')).replace('</','<\\/')))
    (directory/'generation-report.json').write_text(json.dumps({k:v for k,v in payload.items() if k!='maps'},indent=2))
    print(json.dumps({'showcase':str(directory/'index.html'),'maps':len(chosen),'database_maps':sum(s['total'] for s in summary)}),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',type=Path,default=ROOT/'data'/'map-lab-pool.sqlite3')
    parser.add_argument('--output',type=Path,default=ROOT/'map-showcase')
    parser.add_argument('--target',type=int,default=1000,help='accepted unique layouts per board size')
    parser.add_argument('--sizes',type=int,nargs='+',default=[5,7,9],choices=[5,7,9])
    parser.add_argument('--max-attempts',type=int,default=50000,help='per size, per invocation')
    parser.add_argument('--no-export',action='store_true')
    parser.add_argument('--export-only',action='store_true')
    args=parser.parse_args()
    db=connect(args.database)
    try:
        if not args.export_only:
            for size in args.sizes:build(db,size,args.target,args.max_attempts)
        rank(db)
        if not args.no_export:export(db,args.output)
    finally:db.close()


if __name__=='__main__':main()
