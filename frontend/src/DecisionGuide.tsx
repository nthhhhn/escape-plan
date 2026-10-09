import {useState} from 'react';

const NAMES=['Random','BFS','A*','Minimax','Q-learning'];
const CODE=[
 'return random_choice(legal_actions(state))',
 'queue = [start]\nwhile queue:\n  cell = queue.pop_front()\n  enqueue_unseen_neighbors(cell)',
 'priority(cell) = steps_so_far + manhattan(cell, goal)\nexpand_lowest_priority_square()\nrelax_neighbor_distances()',
 'for my_action in legal_actions:\n  worst = min(score(reply) for reply in opponent_replies)\nreturn action_with_highest(worst)\n# Repeat recursively; alpha-beta prunes irrelevant branches.',
 'Q[s,a] += alpha * (reward + gamma * max(Q[next]) - Q[s,a])\n# Terminal states: future value = 0.\n# Play: read saved values; fall back if state is unseen.'
];
const WALLS=new Set([7,12,17]);
const START=10, GOAL=14;
function trace(astar:boolean){
  const frontier=[START], cost=new Map([[START,0]]), order:number[]=[];
  const estimate=(cell:number)=>Math.abs(cell%5-GOAL%5)+Math.abs(Math.floor(cell/5)-Math.floor(GOAL/5));
  while(frontier.length){
    if(astar)frontier.sort((a,b)=>(cost.get(a)!+estimate(a))-(cost.get(b)!+estimate(b))||estimate(a)-estimate(b));
    const cell=frontier.shift()!;order.push(cell);if(cell===GOAL)break;
    for(const next of [cell-5,cell+1,cell+5,cell-1]){
      if(next<0||next>=25||Math.abs(next%5-cell%5)+Math.abs(Math.floor(next/5)-Math.floor(cell/5))!==1||WALLS.has(next))continue;
      if(!cost.has(next)){cost.set(next,cost.get(cell)!+1);frontier.push(next)}
    }
  }
  return order;
}
export function DecisionGuide({initial=3}:{initial?:number}){
  const [algorithm,setAlgorithm]=useState(initial),[step,setStep]=useState(0);
  const order=trace(algorithm===2),shown=order.slice(0,step+1);
  return <section className="card algorithm-guide"><h2>Inside the decision</h2><p>Five methods, five different questions. These small examples explain the method; they are not recordings of a live bot.</p>
    <div className="mode-tabs">{NAMES.map((name,i)=><button key={name} className={algorithm===i?'selected':''} onClick={()=>{setAlgorithm(i);setStep(0)}}>{name}</button>)}</div>
    {algorithm===0&&<><h3>Random: “Which legal action did the dice pick?”</h3><p>Rookie checks what is allowed, then chooses randomly. It never compares routes or imagines your reply.</p><div className="choice-demo">{['Up','Right','Down','Left'].map((move,i)=><span key={move} className={i===[2,0,3,1][step%4]?'chosen':''}>{move}<small>25% chance</small></span>)}</div><button className="text-button" onClick={()=>setStep(step+1)}>Show another sample →</button><p className="fine-print">Illustrative sequence, assuming exactly four legal actions. Powers can add more choices.</p></>}
    {(algorithm===1||algorithm===2)&&<><h3>{algorithm===1?'BFS: “What is the fewest number of steps?”':'A*: “Which promising square should I explore first?”'}</h3><p>{algorithm===1?'Expand all squares one step away, then two steps away, and so on. Every direction gets a turn.':'Prioritize steps already traveled + estimated steps remaining. The estimate points toward the exit, but walls can force a detour.'}</p><div className="search-demo"><div className="search-grid" aria-label={`${NAMES[algorithm]} search, ${shown.length} squares expanded`}>{Array.from({length:25},(_,cell)=><span key={cell} className={WALLS.has(cell)?'blocked':cell===shown[shown.length-1]?'current':shown.includes(cell)?'visited':''}>{cell===START?'START':cell===GOAL?'EXIT':WALLS.has(cell)?'■':shown.includes(cell)?shown.indexOf(cell)+1:''}</span>)}</div><div><strong>{shown.length} squares explored</strong><p>Yellow = current square<br/>Green = already explored<br/>Dark = wall</p><p>{algorithm===1?'Uses a first-in, first-out queue.':'Uses a priority queue: traveled + Manhattan distance. Ties here favor squares nearer the exit.'}</p><p>Both find a shortest route on this equal-cost board. Neither route search predicts a moving opponent by itself. Chaser adds action scoring for danger.</p></div></div><button className="text-button" onClick={()=>setStep(step+1<order.length?step+1:0)}>{step+1<order.length?'Explore next square':'Replay search'} →</button></>}
    {algorithm===3&&<><h3>Minimax: “What if my opponent makes their best reply?”</h3><p>Imagine two prisoner moves. Higher scores are better for the prisoner. The warder chooses the lower score in each branch; the prisoner picks the better of those worst outcomes.</p><div className="choice-demo tree-demo"><div><strong>A · Direct route</strong><p>Warder blocks → −8<br/>Warder chases → +2</p><b>Worst outcome: −8</b></div><div className="chosen"><strong>B · Detour ✓</strong><p>Warder blocks → −3<br/>Warder chases → +1</p><b>Worst outcome: −3</b></div></div><p><strong>Choose B:</strong> −3 is better than −8, even though A looks more direct. These are teaching scores, not win percentages.</p><p>Mastermind values safe options and conserved powers. Wildcard uses the same search, but gives more value to concealment and useful power spending. Alpha-beta pruning skips branches that cannot change the choice; a time limit bounds how far either bot looks ahead.</p></>}
    {algorithm===4&&<><h3>Q-learning: “What worked in similar situations before?”</h3><p>During training, the Trainee tries actions and adjusts a table of learned values. During a match, it reads the saved table; it does not retrain after every move.</p><table className="q-example"><thead><tr><th>Same observed situation</th><th>Learned value</th></tr></thead><tbody><tr><td>Move up</td><td>0.20</td></tr><tr className="chosen"><td>Move right ✓</td><td>{step?'0.70':'0.60'}</td></tr><tr><td>Move down</td><td>−0.10</td></tr></tbody></table><p>{step?'Training update: 0.60 + 0.25 × (1.00 − 0.60) = 0.70. A winning reward strengthens that action.':'Play: choose Right because 0.60 is the highest stored value. Training may instead explore another action.'}</p><button className="text-button" onClick={()=>setStep(step?0:1)}>{step?'Reset example':'Show a training win update'} →</button><p>Example learning rate: 0.25. A terminal win has no future reward. In other states, the update also includes discounted future value. An unseen situation uses the game’s pathfinding fallback.</p></>}
    <details><summary>Technical explanation & pseudocode</summary><pre>{CODE[algorithm]}</pre><p>The game caches route distances. Minimax reports completed search depth within its time budget. Q-learning stores a compact observation rather than the whole board; see AI Lab for measured training coverage and results.</p></details>
    <p className="decision-summary"><strong>Remember:</strong> Random samples. BFS measures distance. A* guides distance search. Minimax predicts replies. Q-learning reuses learned experience.</p>
  </section>
}
