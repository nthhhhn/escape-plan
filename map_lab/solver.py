"""Exact static-game solver. Outcomes: 0 indefinite avoidance, 1 W, 2 P.

Assumptions: orthogonal movement, W first, capture on contact, visible exit,
no powers/modifiers, and waiting by timing out. A forced finish outranks
indefinite avoidance, which outranks a forced loss. Time itself has no score.
"""
from collections import deque
from functools import lru_cache
import hashlib
import heapq

VERSION = 'static-retrograde-v1'
NAMES = {0: 'indefinite', 1: 'warder', 2: 'prisoner'}


class Solver:
    def __init__(self, tiles, size):
        if len(tiles) != size*size or tiles.count('T') != 1:
            raise ValueError('Expected square static board with one tunnel')
        self.tiles, self.size = list(tiles), size
        self.cells = [c for c,t in enumerate(tiles) if t != '#']
        self.index = {c:i for i,c in enumerate(self.cells)}
        self.n = len(self.cells)
        self.exit = self.index[tiles.index('T')]
        self.adj = []
        for cell in self.cells:
            near = []
            for delta in (-size,1,size,-1):
                nxt = cell+delta
                if nxt in self.index and abs(nxt%size-cell%size)+abs(nxt//size-cell//size) == 1:
                    near.append(self.index[nxt])
            self.adj.append(near)
        self.wa = [[j for j in ns if j != self.exit]+[i] for i,ns in enumerate(self.adj)]
        self.pa = [ns+[i] for i,ns in enumerate(self.adj)]
        self.valid = [i for i in range(self.n) if i != self.exit]
        self.count = 2*self.n*self.n
        self.outcome = [0]*self.count
        self.remoteness = [-1]*self.count
        self.solve()
        self.pdist = self.distances(self.adj)
        self.wdist = self.distances([[j for j in ns if j != self.exit] for ns in self.adj])

    def sid(self,w,p,turn=0): return (w*self.n+p)*2+turn

    def decode(self,sid):
        pair,turn = divmod(sid,2)
        w,p = divmod(pair,self.n)
        return w,p,turn

    def terminal(self,w,p): return 1 if w == p else 2 if p == self.exit else 0

    def children(self,sid):
        w,p,turn = self.decode(sid)
        if self.terminal(w,p): return []
        if turn: return [self.sid(w,q,0) for q in self.pa[p]]
        return [self.sid(q,p,1) for q in self.wa[w]]

    def states(self):
        return (self.sid(w,p,t) for w in self.valid for p in range(self.n) for t in (0,1))

    def solve(self):
        pending,maximum,queue = [0]*self.count,[0]*self.count,[]
        for sid in self.states():
            w,p,turn = self.decode(sid)
            pending[sid] = len(self.pa[p] if turn else self.wa[w])
            winner = self.terminal(w,p)
            if winner:
                self.outcome[sid],self.remoteness[sid] = winner,0
                heapq.heappush(queue,(0,sid))
        while queue:
            distance,sid = heapq.heappop(queue)
            w,p,turn = self.decode(sid)
            winner = self.outcome[sid]
            # Undirected floor movement plus waiting gives these predecessors.
            parents = (self.sid(w,q,1) for q in self.pa[p]) if turn == 0 else (self.sid(q,p,0) for q in self.wa[w])
            for parent in parents:
                if self.outcome[parent]: continue
                if parent%2+1 == winner:
                    self.outcome[parent],self.remoteness[parent] = winner,distance+1
                    heapq.heappush(queue,(distance+1,parent))
                else:
                    pending[parent] -= 1
                    maximum[parent] = max(maximum[parent],distance)
                    if pending[parent] == 0:
                        self.outcome[parent],self.remoteness[parent] = winner,maximum[parent]+1
                        heapq.heappush(queue,(maximum[parent]+1,parent))

    def verify(self):
        """Check outcome and remoteness equations at EVERY valid state."""
        for sid in self.states():
            w,p,turn = self.decode(sid)
            terminal = self.terminal(w,p)
            result,distance = self.outcome[sid],self.remoteness[sid]
            if terminal:
                assert (result,distance) == (terminal,0)
                continue
            children = self.children(sid)
            actor = turn+1
            if result == actor:
                winning = [self.remoteness[c] for c in children if self.outcome[c] == actor]
                assert winning and distance == 1+min(winning)
            elif result:
                assert all(self.outcome[c] == result for c in children)
                assert distance == 1+max(self.remoteness[c] for c in children)
            else:
                assert not any(self.outcome[c] == actor for c in children)
                assert any(self.outcome[c] == 0 for c in children)
                assert distance == -1
        return True

    def distances(self,adjacency):
        rows=[]
        for start in range(self.n):
            dist=[999]*self.n; dist[start]=0; queue=deque([start])
            while queue:
                here=queue.popleft()
                for nxt in adjacency[here]:
                    if dist[nxt] == 999:
                        dist[nxt]=dist[here]+1; queue.append(nxt)
            rows.append(dist)
        return rows

    def proof_trace(self,start):
        if not self.outcome[start]: return []
        trace=[start]
        while self.remoteness[trace[-1]]:
            sid=trace[-1]; winner=self.outcome[sid]
            choices=[c for c in self.children(sid) if self.outcome[c] == winner]
            distances=[self.remoteness[c] for c in choices]
            distance=min(distances) if sid%2+1 == winner else max(distances)
            tied=[c for c in choices if self.remoteness[c] == distance]
            w,p,_=self.decode(sid)
            selected=min(tied,key=lambda c:(self.decode(c)[:2] == (w,p),c))
            assert self.remoteness[selected] == self.remoteness[sid]-1
            trace.append(selected)
        return trace

    def heuristic(self,sid):
        w,p,_=self.decode(sid)
        terminal=self.terminal(w,p)
        if terminal: return 10000 if terminal == 2 else -10000
        return 3*self.wdist[w][p]-2*self.pdist[p][self.exit]+0.4*len(self.adj[p])-0.2*len(self.wa[w])

    def independent_routes(self,start):
        """Vertex-capacitated max flow: internally disjoint P-to-exit paths.

        This is a static topology descriptor, not a proof that these paths
        remain safe against a moving warder.
        """
        source=2*start+1; sink=2*self.exit
        residual=[{} for _ in range(2*self.n)]
        def edge(a,b,capacity):
            residual[a][b]=residual[a].get(b,0)+capacity
            residual[b].setdefault(a,0)
        for i,ns in enumerate(self.adj):
            edge(2*i,2*i+1,4 if i in (start,self.exit) else 1)
            for j in ns:edge(2*i+1,2*j,1)
        flow=0
        while flow<4:
            parent={source:None};queue=deque([source])
            while queue and sink not in parent:
                a=queue.popleft()
                for b,capacity in residual[a].items():
                    if capacity>0 and b not in parent:parent[b]=a;queue.append(b)
            if sink not in parent:break
            node=sink
            while node!=source:
                prev=parent[node];residual[prev][node]-=1;residual[node][prev]+=1;node=prev
            flow+=1
        return flow

    def features(self,start,trace):
        """Human-difficulty PROXIES along one optimal-resistance demonstration.

        The heuristic is independent of solved values. The lookahead probe
        succeeds only when ALL its tied preferred actions retain the proven win.
        It is sampled at <=6 winning-side decisions, not a human probability.
        """
        winner=self.outcome[start]
        @lru_cache(maxsize=None)
        def evaluate(sid,depth):
            w,p,_=self.decode(sid)
            if not depth or self.terminal(w,p): return self.heuristic(sid)
            values=[evaluate(c,depth-1) for c in self.children(sid)]
            return max(values) if sid%2 else min(values)
        decisions=[s for s in trace[:-1] if s%2+1 == winner]
        precision,bait,detours,discovery=[],[],[],[]
        enriched=[]
        for position,sid in enumerate(trace):
            w,p,turn=self.decode(sid)
            children=self.children(sid)
            good=[c for c in children if self.outcome[c] == winner]
            choices=[]
            for child in children:
                cw,cp,_=self.decode(child)
                choices.append({'cell':self.cells[cp if turn else cw], 'winner':NAMES[self.outcome[child]],
                    'remaining':self.remoteness[child], 'wait':(cw,cp)==(w,p)})
            enriched.append({'warder':self.cells[w],'prisoner':self.cells[p],'turn':NAMES[turn+1],
                'remaining':self.remoteness[sid],'choices':choices})
            if sid not in decisions: continue
            precision.append(1-len(good)/len(children))
            options=[(c,self.heuristic(c)) for c in children]
            best=(max if winner==2 else min)(v for _,v in options)
            preferred=[c for c,v in options if abs(v-best)<1e-8]
            bait.append(sum(self.outcome[c]!=winner for c in preferred)/len(preferred))
            nw,np,_=self.decode(trace[position+1])
            detours.append(int(self.pdist[np][self.exit]>self.pdist[p][self.exit]) if winner==2 else int(self.wdist[nw][p]>self.wdist[w][p]))
        sample=decisions if len(decisions)<=6 else [decisions[round(i*(len(decisions)-1)/5)] for i in range(6)]
        for sid in sample:
            found=6
            for depth in (1,2,3,4,5):
                options=[(c,evaluate(c,depth-1)) for c in self.children(sid)]
                best=(max if winner==2 else min)(v for _,v in options)
                selected=[c for c,v in options if abs(v-best)<1e-8]
                if all(self.outcome[c]==winner for c in selected): found=depth; break
            discovery.append(found)
        mean=lambda xs:sum(xs)/len(xs) if xs else 0
        insight=mean([(d-1)/5 for d in discovery])
        raw=100*(.40*insight+.25*mean(precision)+.20*mean(bait)+.10*mean(detours)+.05*min(len(decisions)/15,1))
        w,p,_=self.decode(start)
        features={'raw_difficulty':round(raw,4),'lookahead_proxy':round(mean(discovery),2),'lookahead_limit':5,
            'precision':round(mean(precision),3),'greedy_trap_rate':round(mean(bait),3),'detour_rate':round(mean(detours),3),
            'winning_decisions':len(decisions),'plies':len(trace)-1,'cycle_rank':sum(map(len,self.adj))//2-self.n+1,
            'dead_ends':sum(len(ns)==1 for ns in self.adj),'junctions':sum(len(ns)>=3 for ns in self.adj),
            'prisoner_to_exit':self.pdist[p][self.exit],'warder_to_prisoner':self.wdist[w][p],
            'independent_routes':self.independent_routes(p),
            'cycle_states':sum(self.outcome[s]==0 for s in self.states())}
        evaluate.cache_clear()
        return features,enriched


def canonical_key(tiles,size):
    """Deduplicate whole layouts (not just spawns) under eight symmetries."""
    variants=[]
    for reflect in (False,True):
        for turns in range(4):
            result=['']*(size*size)
            for cell,tile in enumerate(tiles):
                r,c=divmod(cell,size)
                if reflect:c=size-1-c
                for _ in range(turns):r,c=c,size-1-r
                result[r*size+c]=tile
            variants.append(''.join(result))
    return hashlib.sha256(min(variants).encode()).hexdigest()
