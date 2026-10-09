import { useState } from 'react';
import {DecisionGuide} from './DecisionGuide';
export {ReactionPanel} from './Reactions';
import type { GameState, Room, Rules } from './types';

export function Character({role='warder', muted=false, variant='pursuer'}:{role?:string;muted?:boolean;variant?:string}) {
  const officer=role==='warder';
  return <svg className={`character ${muted?'opponent-art':''}`} viewBox="0 0 100 110" aria-label={`${muted?'Opponent ':''}${role} illustration`} role="img">
    <ellipse cx="50" cy="103" rx="31" ry="5" fill="#000" opacity=".2"/>
    <path d="M19 98V80Q21 62 39 62H61Q80 62 82 80V98Z" fill={officer?'#477eac':'#e99542'} stroke="#262b2e" strokeWidth="3"/>
    {!officer&&<g stroke="#fff1d9" strokeWidth="7"><path d="M21 79H80M20 94H81"/></g>}
    <path d="M40 61V69L50 75L60 69V60" fill="#dca47f" stroke="#262b2e" strokeWidth="2"/>
    <ellipse cx="50" cy="42" rx="24" ry="28" fill="#edbd92" stroke="#262b2e" strokeWidth="3"/>
    <path d="M27 37V25Q28 9 49 9Q73 9 73 32L65 24Q49 30 34 22L32 39" fill="#403731"/>
    {officer&&<><path d="M22 24L25 12Q50 2 75 12L79 24Z" fill="#38648b" stroke="#262b2e" strokeWidth="3"/><path d="M21 24Q50 40 79 24Z" fill="#273f53" stroke="#262b2e" strokeWidth="2"/><path d="M46 12H55L53 21L50 23L46 20Z" fill="#f5d477"/></>}
    {!officer&&<path d="M26 22L30 12Q51 2 70 13L74 24Z" fill="#e99542" stroke="#262b2e" strokeWidth="3"/>}
    <path d={variant==='trickster'?'M35 39L44 42M57 41L66 36':'M35 39L44 39M57 39L65 40'} stroke="#44352b" strokeWidth="3" strokeLinecap="round"/>
    <ellipse cx="40" cy="46" rx="2.5" ry="3" fill="#292c30"/><ellipse cx="61" cy="46" rx="2.5" ry="3" fill="#292c30"/>
    <path d="M50 46L48 54H52" stroke="#bb825d" strokeWidth="2" fill="none"/>
    <path d={variant==='trickster'?'M42 59Q54 67 62 56':'M43 61Q51 64 59 60'} stroke="#664436" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
    {(variant==='planner')&&<g stroke="#263849" strokeWidth="2.5" fill="none"><rect x="32" y="40" width="15" height="12" rx="4"/><rect x="54" y="40" width="15" height="12" rx="4"/><path d="M47 45H54M43 59L50 56L58 59"/></g>}
    {variant==='qlearning'&&<g><path d="M25 42Q21 8 52 8Q80 10 77 43" stroke="#69d7bb" strokeWidth="5" fill="none"/><rect x="24" y="39" width="8" height="18" rx="4" fill="#263849"/><path d="M28 54L35 65H44" fill="none" stroke="#69d7bb" strokeWidth="3"/><rect x="34" y="41" width="34" height="10" rx="3" fill="#6ce2c2" opacity=".65"/></g>}
    {(variant==='bfs'||variant==='astar'||variant==='pursuer')&&<g><path d="M62 32L57 40M63 53L58 58" stroke="#aa604c" strokeWidth="2"/><path d="M23 22H77" stroke="#de6b5a" strokeWidth="4"/></g>}
    {variant==='easy'&&<g fill="#b77254"><circle cx="35" cy="53" r="1.7"/><circle cx="40" cy="55" r="1.7"/><circle cx="61" cy="55" r="1.7"/><circle cx="66" cy="53" r="1.7"/><path d="M44 58Q51 71 58 58Z" fill="#fff6dd"/></g>}
    {variant==='trickster'&&<g><path d="M30 31L32 19L42 24L51 15L58 29L67 23L69 34" fill="#aa79d2"/><circle cx="74" cy="53" r="4" fill="none" stroke="#eac65f" strokeWidth="2.5"/></g>}
    {officer?<><path d="M35 71L46 79L41 87L30 76M65 71L54 79L59 87L70 76" fill="#a1c2d9"/><path d="M65 82L72 85L69 93L65 95L61 91L60 85Z" fill="#f5d477"/><path d="M48 77H53L55 98H45Z" fill="#293e51"/></>:<rect x="36" y="82" width="28" height="11" rx="2" fill="#f5efdd"/>}
  </svg>
}

export function CircleTimer({seconds,total=10,large=false}:{seconds:number;total?:number;large?:boolean}) {
  const ratio=Math.max(0,Math.min(1,seconds/total));
  return <div className={`circle-timer ${large?'large':''} ${seconds<=3&&!large?'urgent':''}`} role="timer" aria-label={`${Math.ceil(seconds)} seconds remaining`}>
    <svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="43"/><circle className="timer-progress" cx="50" cy="50" r="43" strokeDasharray="270.18" strokeDashoffset={270.18*(1-ratio)}/></svg><strong>{Math.ceil(seconds)||(large?'GO!':0)}</strong>
  </div>
}

export const BOT_CARDS = [
  {name:'Rookie',bot:'easy',personality:'pursuer',level:'Beginner',quote:'I have a plan. Probably.',description:'Random legal actions. Unpredictable, with plenty of mistakes.',algorithm:'Random selection',story:'The newest face in the yard is still finding their feet.',warder:'Wanders between legal actions, sometimes stumbling into a capture.',prisoner:'May find an escape by chance, but does not plan a route.',weakness:'No threat prediction or consistent strategy.'},
  {name:'Chaser',bot:'bfs',personality:'pursuer',level:'Medium',quote:'No time for the scenic route.',description:'Direct pursuit, quick escapes, and immediate threat awareness.',algorithm:'BFS / A* + action scoring',story:'A former track star who believes every problem can be outrun.',warder:'Favors closing the distance to the prisoner.',prisoner:'Favors progress toward the key or tunnel, while penalizing immediate danger.',weakness:'A short route can still lead into a trap beyond its one-action evaluation.'},
  {name:'Mastermind',bot:'hard',personality:'planner',level:'Hard',quote:'Leave yourself another way out.',description:'Looks ahead, values escape options, and conserves powers.',algorithm:'Minimax + alpha-beta pruning',story:'The quiet strategist who studies every corner of the yard.',warder:'Searches possible replies and values limiting the prisoner’s routes.',prisoner:'Balances progress with distance from the warder and available exits.',weakness:'A limited search horizon can miss a longer trap; hidden information requires guesses.'},
  {name:'Wildcard',bot:'hard',personality:'trickster',level:'Hard',quote:'You thought that was the plan?',description:'Values useful concealment and spends powers more readily.',algorithm:'Minimax + alpha-beta pruning',story:'An improviser who sees a shortcut where everyone else sees a wall.',warder:'Values Radar during Smoke, with less incentive to hoard charges.',prisoner:'Values concealment and is more willing to spend powers to improve a position.',weakness:'Power preferences are scoring heuristics, not a guarantee of a successful trick.'},
  {name:'The Trainee',bot:'qlearning',personality:'planner',level:'Experimental',quote:'Learning one escape at a time.',description:'A saved Q-learning policy. Strength depends on its training.',algorithm:'Tabular Q-learning',story:'An apprentice whose experience comes from simulated games.',warder:'Chooses actions with learned values; uses pathfinding for unseen situations.',prisoner:'Uses the same learned action-value system from the prisoner’s perspective.',weakness:'Compact observations omit parts of the board. Unfamiliar settings may rely mostly on fallback.'},
];

export function BotPicker({rules,onChange,onGuide}:{rules:Rules;onChange:(r:Rules)=>void;onGuide:()=>void}) {
  const [custom,setCustom]=useState(false);
  return <div className="bot-picker"><p className="field-label">CHOOSE YOUR OPPONENT</p><div className="bot-roster">{BOT_CARDS.map(b=><button type="button" key={b.name} className={`bot-choice ${rules.bot===b.bot&&rules.personality===b.personality?'selected':''}`} aria-pressed={rules.bot===b.bot&&rules.personality===b.personality} onClick={()=>onChange({...rules,bot:b.bot,personality:b.personality})}><Character variant={b.bot==='hard'?b.personality:b.bot}/><strong>{b.name}</strong><small>{b.level}</small></button>)}</div><button className="text-button" onClick={onGuide}>Meet the bots & learn their algorithms →</button><label className="field-label" htmlFor="practice-role">YOUR ROLE</label><select id="practice-role" value={rules.player_role||'random'} onChange={e=>onChange({...rules,player_role:e.target.value})}><option value="random">Random assignment</option><option value="prisoner">Prisoner — escape</option><option value="warder">Warder — pursue</option></select><button className="text-button custom-toggle" onClick={()=>setCustom(!custom)} aria-expanded={custom}>Custom opponent {custom?'−':'+'}</button>{custom&&<div className="custom-bot"><label>Algorithm<select value={rules.bot} onChange={e=>onChange({...rules,bot:e.target.value})}>{[['easy','Random'],['bfs','BFS'],['astar','A*'],['hard','Minimax'],['qlearning','Q-learning']].map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label><label>Personality<select disabled={rules.bot==='easy'} value={rules.personality||'planner'} onChange={e=>onChange({...rules,personality:e.target.value})}>{['pursuer','planner','trickster'].map(s=><option key={s}>{s}</option>)}</select></label></div>}</div>
}


export function FieldGuide(){
 const [selected,setSelected]=useState(2); const [role,setRole]=useState('warder');
 const bot=BOT_CARDS[selected];
 return <section className="field-guide"><div className="guide-heading"><span className="small-tag">THE FIELD GUIDE</span><h1>Know your opponent.</h1><p>Meet the characters. Understand their decisions. Find your way out.</p></div><div className="guide-bots">{BOT_CARDS.map((b,i)=><button key={b.name} className={selected===i?'selected':''} onClick={()=>{setSelected(i)}}><Character variant={b.bot==='hard'?b.personality:b.bot}/><strong>{b.name}</strong></button>)}</div><div className="guide-profile card"><div className="portrait"><Character role={role} variant={bot.bot==='hard'?bot.personality:bot.bot}/><button className="text-button" onClick={()=>setRole(role==='warder'?'prisoner':'warder')}>View as {role==='warder'?'prisoner':'warder'}</button></div><div><span className="small-tag">{bot.level} · {bot.personality}</span><h2>{bot.name}</h2><blockquote>“{bot.quote}”</blockquote><p>{bot.story} <small>(Fictional background.)</small></p><dl><dt>As warder</dt><dd>{bot.warder}</dd><dt>As prisoner</dt><dd>{bot.prisoner}</dd><dt>Watch for</dt><dd>{bot.weakness}</dd></dl><p><strong>Algorithm:</strong> {bot.algorithm}</p></div></div><DecisionGuide key={selected} initial={selected===0?0:selected===1?1:selected===4?4:3}/><section className="card"><h2>Powers & counterplay</h2><div className="guide-grid">{[['Dig','Remove one adjacent permanent wall. Costs your turn; you stay put.'],['Sprint','Move up to two squares in a straight line. Cannot jump over walls or the warder.'],['Smoke','Stay still to activate. Hidden through the next warder turn, your next action, and the warder turn after that. Radar overrides it.'],['Radar','Stay still to reveal the prisoner through the end of your following turn. Does not reveal the real tunnel.'],['Roadblock','Block adjacent empty floor for two rounds, without trapping players or objectives.'],['Shifting tunnel','Special only: within two walking steps of a tunnel for three warder turns triggers relocation. Warning after two turns; a three-round cooldown follows a successful shift. No suitable destination means postponement.']].map(([name,text])=><p key={name}><b>{name}</b>{text}</p>)}</div><p>Classic keeps the original 5×5 rules. Special combines shifting walls, keys, fake tunnels, collapsing floors, shorter timers and optional tunnel pressure. Fake exits follow the same pressure rule without revealing their identity. Shrinking Prison has a 60-round containment limit.</p></section></section>
}

export function availableTargets(s:GameState,action:string):Map<number,{direction:string;steps:number}>{
 const result=new Map<number,{direction:string;steps:number}>(); const size=s.rules.size; const pos=s.positions[s.role]; if(pos===null)return result;
 const step=(cell:number,dr:number,dc:number)=>{const r=Math.floor(cell/size)+dr,c=cell%size+dc;return r>=0&&r<size&&c>=0&&c<size?r*size+c:null};
 const walk=(c:number)=>s.tiles[c]!=='#'&&!s.roadblocks[c]&&(s.tiles[c]!=='T'||s.role==='warder'||(s.role==='prisoner'&&s.has_key));
 const protectedCell=(c:number)=>Object.values(s.positions).includes(c)||s.tunnels.includes(c)||s.key===c||Boolean(s.pickups[c]);
 const connected=(tiles:string[],blocked:number[])=>{const floors=tiles.map((t,i)=>t==='.'&&!blocked.includes(i)?i:-1).filter(i=>i>=0);const seen=new Set<number>();const q=[floors[0]];while(q.length){const c=q.pop()!;if(c===undefined||seen.has(c))continue;seen.add(c);for(const [dr,dc] of [[-1,0],[1,0],[0,-1],[0,1]]){const n=step(c,dr,dc);if(n!==null&&tiles[n]==='.'&&!blocked.includes(n)&&!seen.has(n))q.push(n)}}return floors.every(c=>seen.has(c))&&s.tunnels.every(c=>[[-1,0],[1,0],[0,-1],[0,1]].some(([dr,dc])=>{const n=step(c,dr,dc);return n!==null&&seen.has(n)}))};
 for(const [direction,dr,dc] of [['up',-1,0],['down',1,0],['left',0,-1],['right',0,1]] as const){const n=step(pos,dr,dc);if(n===null)continue;
 if(action==='move'||action==='sprint'){if(!walk(n))continue;result.set(n,{direction,steps:1});const m=step(n,dr,dc);if(action==='sprint'&&m!==null&&walk(m)&&n!==s.positions.warder&&n!==s.real_tunnel)result.set(m,{direction,steps:2});}
 else if(action==='dig'&&s.tiles[n]==='#')result.set(n,{direction,steps:1});
 else if(action==='roadblock'&&s.tiles[n]==='.'&&!s.roadblocks[n]&&!protectedCell(n)&&connected(s.tiles,[...Object.keys(s.roadblocks).map(Number),n]))result.set(n,{direction,steps:1});
 else if(action==='shift'&&s.tiles[n]==='#'){const m=step(n,dr,dc);if(m!==null&&s.tiles[m]==='.'&&!s.roadblocks[m]&&!protectedCell(m)){const tiles=[...s.tiles];tiles[n]='.';tiles[m]='#';if(connected(tiles,Object.keys(s.roadblocks).map(Number)))result.set(n,{direction,steps:1})}}
 }
 return result;
}
