import {useEffect,useRef,useState} from 'react';
import type {Room,GameState} from './types';

type Meme={image:string;name:string;caption:string};
const templates=[
 ['1bij.jpg','One Does Not Simply'],['1o00in.jpg','Is This A Pigeon'],['30b1gx.jpg','Drake'],['1g8my4.jpg','Two Buttons'],['345v97.jpg','Woman Yelling At Cat'],['26jxvz.jpg',"Gru’s Plan"],['1b42wl.jpg','Bike Fall'],['54hjww.jpg','Trade Offer'],['2za3u1.jpg','Same Picture'],['24y43o.jpg','Change My Mind'],['2fm6x.jpg','Waiting Skeleton'],['1c1uej.jpg','Pablo Escobar'],['28j0te.jpg','Epic Handshake'],['261o3j.jpg','Running Away Balloon'],['22bdq6.jpg','Exit Ramp'],['1ur9b0.jpg','Distracted Boyfriend'],['23ls.jpg','Disaster Girl'],['46e43q.png','Always Has Been'],['3oevdk.jpg','Bernie Asking'],['3lmzyx.jpg','UNO Draw 25'],['9ehk.jpg','Batman Slapping Robin'],['26am.jpg','Ancient Aliens'],
 ['5c7lwq.png','Anakin and Padme'],['1ihzfe.jpg','Everywhere'],['2odckz.jpg','Marked Safe'],['1otk96.jpg','Mocking SpongeBob'],['2xscjb.png','You Guys Are Getting Paid'],
];
const pool=(items:[number,string][]):Meme[]=>items.map(([i,caption])=>({image:templates[i][0],name:templates[i][1],caption}));
const reactions:Record<string,Meme[]>={
 waiting:pool([[10,'Me waiting for my opponent.'],[11,'Any minute now…'],[18,'I am once again asking for a player two.']]),
 ready:pool([[12,'A worthy opponent has arrived.'],[7,'You receive: a match. I receive: your full attention.'],[5,'Step one: enter the yard. Step two: have a plan.']]),
 planning:pool([[22,'You have an escape plan, right? …Right?'],[26,'You guys already have a strategy?'],[5,'Studied the map. Forgot the opponent.'],[3,'Left or right? My entire future depends on this.'],[21,'The calculations are definitely calculating.'],[1,'Is this… a strategy?'],[9,'This opening deserves a documentary.']]),
 move:pool([[0,'One does not simply walk out.'],[2,'Obvious route? No. Questionable route? Yes.'],[4,'That move started an argument.'],[6,'This cannot possibly backfire.'],[7,'You receive: one move. I receive: your route.'],[8,'Safe route. Dangerous route. Same picture.'],[9,'Corners are a personality trait.'],[15,'Me looking at a different route halfway through the plan.']]),
 chase:pool([[13,'You can run. I can also run.'],[16,'The prisoner is close. This is the fun part.'],[20,'Escape privileges are about to be revoked.'],[18,'I am once again asking you to stop running.'],[7,'You receive: panic. I receive: a shorter chase.'],[2,'Patrolling? No. Hot pursuit? Yes.']]),
 panic:pool([[23,'Threats. Threats everywhere.'],[25,'“Just follow the shortest route.”'],[3,'The warder is close. Both buttons are panic.'],[14,'New plan: anywhere else. Immediately.'],[11,'I may, in fact, be cooked.'],[6,'My shortcut brought me directly to the warder.'],[19,'Find an exit or draw 25.'],[4,'My brain and my feet disagree.']]),
 escapeSoon:pool([[13,'Freedom is right there. No pressure.'],[3,'One last move. Please do not fumble.'],[12,'The tunnel and I are about to meet.'],[5,'Final step: actually escape.']]),
 guardExit:pool([[14,'They are near the exit. Intercept now!'],[4,'That tunnel was not an invitation.'],[19,'Stop the escape or draw 25.'],[18,'I am once again asking you to step away from the exit.']]),
 sprint:pool([[13,'Gotta go. Immediately.'],[14,'Taking the express lane.'],[15,'Walking speed watching Sprint leave.'],[2,'One square? Make it two.']]),
 smoke:pool([[16,'You saw absolutely nothing.'],[17,'Wait, where did the prisoner go?'],[4,'The warder would like an explanation.'],[21,'Not missing. Stealth science.']]),
 radar:pool([[0,'Nice smoke. Anyway…'],[18,'I am once again asking for your location.'],[17,'You were visible? Always have been.'],[20,'Invisibility privileges revoked.']]),
 roadblock:pool([[19,'Take the scenic route.'],[20,'Shortcut privileges revoked.'],[7,'You receive: a wall. I receive: time.'],[9,'This route is closed. Change my mind.']]),
 dig:pool([[21,'Walls? More like suggestions.'],[16,'Renovation started without permission.'],[14,'Creating my own exit ramp.'],[5,'Step three: remove the architecture.']]),
 timeout:pool([[11,'Those seconds went WHERE?'],[10,'My brain was still buffering.'],[3,'Still choosing. Turn already gone.'],[6,'I spent the entire turn planning my turn.']]),
 shift:pool([[16,'Camping spot expired.'],[14,'The exit has left the chat.'],[8,'Old tunnel. New tunnel. Definitely not the same square.'],[4,'The campsite has been evicted.']]),
 warning:pool([[19,'Move away or lose your camping spot.'],[3,'Keep camping? Watch the tunnel move?'],[18,'The yard is once again asking you to move.'],[5,'Step three: the tunnel relocates. Wait—what?']]),
 win:pool([[24,'Marked safe from losing this round.'],[12,'That’s how it’s done.'],[16,'All according to plan.'],[7,'You receive: defeat. I receive: one point.'],[5,'The plan actually worked.']]),
 lose:pool([[11,'I would like a rematch.'],[6,'That was a practice round.'],[3,'Accept defeat or demand a rematch?'],[4,'My plan would like to file a complaint.']]),
};
function steps(s:GameState,start:number|null,goal:number|null,role='warder'){
 if(start===null||goal===null)return Infinity;
 const queue:[[number,number]]=[[start,0]],seen=new Set([start]);
 for(let i=0;i<queue.length;i++){const [cell,d]=queue[i];if(cell===goal)return d;
  for(const next of [cell-s.rules.size,cell+1,cell+s.rules.size,cell-1]){
   if(next<0||next>=s.tiles.length||Math.abs(next%s.rules.size-cell%s.rules.size)+Math.abs(Math.floor(next/s.rules.size)-Math.floor(cell/s.rules.size))!==1||s.tiles[next]==='#'||s.roadblocks[next]||seen.has(next))continue;
   if(role==='warder'&&s.tiles[next]==='T')continue;
   seen.add(next);queue.push([next,d+1]);
  }
 }return Infinity;
}
export function reactionKind(room:Room){
 const s=room.state;if(room.phase==='waiting')return 'waiting';if(!s||['ready','countdown'].includes(room.phase))return 'ready';
 if(s.winner)return s.winner===s.role?'win':'lose';
 const event=s.last_event||'';
 if(event.includes('Tunnel shifted'))return 'shift';
 if(s.role==='warder'&&Math.max(0,...Object.values(s.tunnel_pressure||{}))>=2)return 'warning';
 for(const kind of ['timeout','sprint','smoke','radar','roadblock','dig'])if(event.includes(kind))return kind;
 if(steps(s,s.positions.warder,s.positions.prisoner)<=2)return s.role==='warder'?'chase':'panic';
 const exit=s.real_tunnel;
 if(s.has_key&&exit!==null&&steps(s,s.positions.prisoner,exit,'prisoner')<=1)return s.role==='prisoner'?'escapeSoon':'guardExit';
 return s.ply<=3?'planning':'move';
}
function MemeImage({meme}:{meme:Meme}){
 const [status,setStatus]=useState('loading');
 return <div className="reaction-image"><div className="meme-placeholder" aria-hidden="true"><span>EP</span><b>{status==='failed'?'The reaction lives on.':'Preparing the reaction…'}</b></div><img style={{opacity:status==='loaded'?1:0}} src={`https://i.imgflip.com/${meme.image}`} alt={meme.name} referrerPolicy="no-referrer" onLoad={()=>setStatus('loaded')} onError={()=>setStatus('failed')}/></div>
}
export function ReactionPanel({room,muted,onSound}:{room:Room;muted:boolean;onSound:(kind:string)=>void}){
 const kind=reactionKind(room),key=`${room.match_id}:${room.state?.ply}:${room.phase}:${kind}`;
 const history=useRef<string[]>([]),lastKey=useRef('');
 const [meme,setMeme]=useState(reactions[kind][0]);
 useEffect(()=>{
  if(lastKey.current===key)return;lastKey.current=key;
  const choices=reactions[kind].filter(m=>!history.current.slice(-2).includes(m.image));
  let hash=0;for(const c of key+(room.state?.role||''))hash=(hash*31+c.charCodeAt(0))>>>0;
  const selected=choices[hash%choices.length];setMeme(selected);history.current=[...history.current.slice(-2),selected.image];
  if(!muted&&['playing','finished'].includes(room.phase))onSound(kind==='win'?'improved':kind==='lose'?'worsened':'uncertain');
 },[key]);
 return <section className="card reaction-panel" aria-label="Game reactions"><div className="card-title"><div><span className="panel-kicker">TURN {String((room.state?.ply||0)+1).padStart(2,'0')} REACTION</span><h3>From the sidelines</h3></div><span className="reaction-kind">{kind==='escapeSoon'?'exit ahead':kind==='guardExit'?'intercept':kind}</span></div><MemeImage key={meme.image} meme={meme}/><p className="reaction-caption" aria-live="polite">{meme.caption}</p><div className="reaction-footer"><span>{meme.name}</span><a href="https://imgflip.com/memetemplates" target="_blank" rel="noreferrer">Imgflip templates ↗</a></div></section>
}
