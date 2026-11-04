// Original vector explanations. Every scene is selected by a reviewed task
// brief; small examples illustrate definitions, never benchmark performance.
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const p = (d, cls = 'di-line', attrs = '') => `<path d="${d}" class="${cls}"${attrs}/>`;
const line = (a,b,cls='di-line') => p(`M${a}L${b}`,cls);
const circle = (x,y,r=6,cls='di-node') => `<circle cx="${x}" cy="${y}" r="${r}" class="${cls}"/>`;
const rect = (x,y,w,h,cls='di-cell',r=4) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" class="${cls}"/>`;
const text = (x,y,s,cls='di-label') => `<text x="${x}" y="${y}" class="${cls}">${esc(s)}</text>`;
const group = (s,x=0,y=0) => `<g transform="translate(${x} ${y})">${s}</g>`;
const ring = (n,r=78,cx=220,cy=125) => Array.from({length:n},(_,i)=>[cx+r*Math.cos(-Math.PI/2+i*2*Math.PI/n),cy+r*Math.sin(-Math.PI/2+i*2*Math.PI/n)]);
const nodes = (ps,selected=[]) => ps.map(([x,y],i)=>circle(x,y,selected.includes(i)?7:5,selected.includes(i)?'di-solid':'di-node')).join('');
const edges = (ps,es,cls='di-line') => es.map(([a,b])=>line(ps[a],ps[b],cls)).join('');
const arrow = (a,b,cls='di-hot') => {
  const angle=Math.atan2(b[1]-a[1],b[0]-a[0]),size=6;
  return line(a,b,cls)+p(`M${b[0]-size*Math.cos(angle-.6)} ${b[1]-size*Math.sin(angle-.6)}L${b}L${b[0]-size*Math.cos(angle+.6)} ${b[1]-size*Math.sin(angle+.6)}`,cls,` data-motion-arrow="${a} ${b}"`);
};
const graphPoints=[[94,75],[176,42],[272,66],[348,130],[270,211],[166,204],[90,155],[218,126]];
const graphEdges=[[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,0],[0,7],[1,7],[2,7],[4,7],[5,7]];
const palette=['di-color-a','di-color-b','di-color-c','di-color-d'];
const pairList=n=>Array.from({length:n},(_,a)=>Array.from({length:n-a-1},(_,i)=>[a,a+i+1])).flat();
const diagrams={};

diagrams.corners=()=>{
  let s=''; for(let x=0;x<9;x++)for(let y=0;y<6;y++)s+=circle(87+x*33,38+y*33,2,'di-dot');
  const pts=[[153,71],[252,71],[153,170]];
  return s+edges(pts,[[0,1],[0,2]],'di-hot')+nodes(pts,[0,1,2])+text(202,59,'d')+text(137,125,'d')+text(144,193,'(x, y+d)')+text(270,57,'(x+d, y)')+text(122,58,'(x, y)');
};
diagrams.path=()=>{
  const ps=[[65,128],[135,57],[134,198],[225,126],[294,58],[373,117],[325,200]],es=[[0,1],[0,2],[1,3],[1,4],[2,3],[3,4],[3,6],[4,5],[5,6]];
  const directed=(a,b,cls='di-line')=>{const u=ps[a],v=ps[b],d=Math.hypot(v[0]-u[0],v[1]-u[1]),r=[0,6].includes(b)?9:7;return arrow(u,[v[0]-r*(v[0]-u[0])/d,v[1]-r*(v[1]-u[1])/d],cls);};
  return es.map(([a,b])=>directed(a,b)).join('')+[[0,1],[1,3],[3,6]].map(([a,b])=>directed(a,b,'di-hot di-flow')).join('')+nodes(ps,[0,6])+text(65,132,'s','di-white')+text(325,204,'t','di-white')+[[94,83,'2'],[181,78,'4'],[88,174,'3'],[264,82,'2'],[340,75,'3']].map(a=>text(...a)).join('')+text(220,242,'one source · nonnegative edge lengths');
};
function matrix(rows=5,cols=6,kind='sparse'){
  let s=''; for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
    const on=kind==='sparse'?(r+c*2)%4<2:kind==='hilbert'?(r===1&&c===3)||(r===3&&c===1):((r*c+r+c)%3===1);
    s+=rect(79+c*34,44+r*32,29,27,on?'di-tile':'di-cell',2);
    const v=kind==='hilbert'?`1/${r+c+1}`:kind==='sparse'?(on?(c%2?'+1':'−1'):'0'):(on?'1':'0');
    s+=text(93+c*34,62+r*32,v,'di-mono');
  }return s;
}
diagrams['sparse-matrix']=()=>{
  const signs=[1,-1,1,1,-1,1],sums=Array.from({length:5},(_,r)=>signs.reduce((sum,v,c)=>sum+((r+c*2)%4<2?(c%2?1:-1):0)*v,0));
  return matrix()+signs.map((v,i)=>text(93+i*34,29,v>0?'+':'−','di-mark')).join('')+arrow([298,121],[329,121])+sums.map((v,i)=>rect(343,44+i*32,30,27,'di-tile',2)+text(358,62+i*32,v,'di-mono')).join('')+text(188,232,'choose column signs')+text(357,232,'row sums');
};
diagrams.bidding=()=>{
  const ps=[[165,56],[295,83],[308,181],[181,210],[105,134]];
  return edges(ps,[[0,1],[1,2],[2,3],[3,4],[4,0]])+arrow([165,56],[295,83])+nodes(ps,[0])+text(229,57,'+2')+text(328,138,'−1')+text(230,233,'+3')+circle(211,128,18,'di-tile')+text(211,133,'E')+text(43,112,'A')+text(397,112,'B')+[0,1,2].map(i=>rect(24+i*13,126,8,28,'di-tile')+rect(378+i*13,126,8,28,'di-tile')).join('');
};
diagrams.folded=()=>{
  let s=''; for(let i=0;i<8;i++){s+=rect(40+i*45,82,38,52,i<4?'di-tile':'di-cell')+text(59+i*45,113,`f${i}`,'di-mono');}
  return s+p('M40 145V160H213V145M220 145V160H393V145','di-hot')+text(126,188,'one folded symbol')+text(306,188,'one folded symbol')+text(220,45,'consecutive polynomial evaluations');
};
diagrams.proximity=()=>{
  const ps=[[72,171],[139,83],[203,149],[270,66],[350,144]];
  return ps.map(([x,y])=>circle(x,y,31,'di-region')+circle(x,y,5,'di-solid')).join('')+p('M35 206C120 4 120 191 210 126S285 40 402 191','di-hot di-flow')+text(220,232,'a curve of words near a code')+text(340,91,'codeword');
};
diagrams['local-code']=()=>{
  const xs=[55,102,149,196,243,290,337,384];
  return xs.map((x,i)=>rect(x-16,74,32,38,[1,4,6].includes(i)?'di-tile':'di-cell')+text(x,98,i===3?'?':i%2,'di-mono')).join('')+[1,4,6].map(i=>p(`M${xs[i]} 119Q${xs[i]} 167 196 172`,'di-hot')).join('')+circle(196,177,19,'di-solid')+text(196,183,'⊕','di-white')+arrow([196,156],[196,121])+text(220,232,'three queried bits recover one coordinate');
};
diagrams.cube=()=>{
  const ps=[[109,90],[235,90],[235,204],[109,204],[175,39],[301,39],[301,153],[175,153]],es=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  return edges(ps,es)+arrow(ps[3],ps[2],'di-danger')+nodes(ps,[3])+text(101,229,'1')+text(241,229,'0')+text(220,254,'a monotonicity violation');
};
diagrams.chase=()=>[ [100,135,52],[210,95,46],[320,155,50] ].map(([x,y,r],i)=>circle(x,y,r,'di-region')+text(x,y-r-14,`S${i+1}`)).join('')+p('M78 153L179 111L310 149','di-hot di-flow')+nodes([[78,153],[179,111],[310,149]],[0,1,2])+text(220,235,'move into each requested set');
diagrams.cactus=()=>{
  const ps=[[58,129],[112,57],[170,129],[112,200],[235,129],[292,57],[351,129],[292,200]];
  return edges(ps,[[0,1],[1,2],[2,3],[3,0],[2,4],[4,5],[5,6],[6,7],[7,4]])+line(ps[2],ps[4],'di-danger di-dash')+nodes(ps)+text(220,237,'cut edges · bound component diameters');
};
function tree(symbols=['+','×','−']){
  const ps=[[220,48],[130,114],[310,114],[80,192],[173,192],[267,192],[360,192]],es=[[0,1],[0,2],[1,3],[1,4],[2,5],[2,6]];
  return edges(ps,es)+ps.map(([x,y],i)=>circle(x,y,i<3?19:14,i<3?'di-tile':'di-node')+text(x,y+5,i<3?symbols[i]:`x${i-2}`,i<3?'di-mark':'di-mono')).join('');
}
diagrams.arithmetic=()=>tree()+text(220,244,'subtraction allows cancellation');
diagrams.subspace=()=>p('M46 151L219 29L394 103L221 226Z','di-region')+p('M114 144L219 70L325 115L221 190Z','di-tile')+line([162,137],[275,132],'di-hot')+text(365,99,'W','di-mark')+text(300,134,'L','di-mark')+text(220,123,'Q','di-mark');
diagrams.independent=()=>{
  const ps=ring(7),es=Array.from({length:7},(_,i)=>[i,(i+1)%7]);
  return edges(ps,es)+nodes(ps,[0,3])+p(`M${ps[3]}Q95 139 ${ps[4]}`,'di-hot di-dash')+circle(...ps[4],12,'di-outline')+text(220,242,'move one token · keep independence');
};
diagrams.halfspace=()=>arrow([68,211],[382,211],'di-line')+arrow([68,211],[68,30],'di-line')+p('M107 211L257 47L372 75L372 211Z','di-region')+p('M128 211L327 86','di-hot')+p('M135 184L188 156L245 139','di-hot di-flow')+nodes([[135,184],[188,156],[245,139]],[0,1,2])+text(300,59,'feasible region')+text(405,216,'x₁')+text(62,22,'x₂');
diagrams.quantum=()=>{
  let s='';[89,170].forEach((y,i)=>{s+=line([43,y],[385,y])+rect(77,y-25,80,50,'di-tile')+text(117,y+6,i?'bits':'|ψ⟩','di-mark')+rect(221,y-25,104,50,'di-cell')+text(273,y+5,i?'QCMA verifier':'QMA verifier')+text(373,y-16,'0 / 1');});
  return s+text(117,42,'witness')+text(273,42,'quantum computation')+text(220,233,'quantum state vs classical string');
};
diagrams.parity=()=>{
  const ps=ring(6);return edges(ps,[[0,1],[1,2],[2,0],[2,3],[3,4],[4,5],[5,3],[5,0]])+ps.map(([x,y],i)=>(i%2?rect(x-16,y-16,32,32,'di-tile'):circle(x,y,17,'di-node'))+text(x,y+5,i,'di-mono')).join('')+text(220,237,'priorities determine the infinite-play winner');
};
diagrams.taxis=()=>{
  const ps=[[76,57],[355,69],[152,204]],pickup=[213,116],drop=[338,185];
  return ps.map(([x,y],i)=>rect(x-19,y-11,38,24,'di-tile')+text(x,y+5,`T${i+1}`,'di-mono')).join('')+arrow(ps[0],pickup)+arrow(pickup,drop,'di-dash')+nodes([pickup,drop],[0])+text(226,96,'pickup')+text(357,208,'drop-off')+text(111,108,'paid')+text(291,139,'free');
};
diagrams.query=()=>line([29,132],[410,132])+[[76,'|ψ⟩'],[174,'V'],[272,'Oᶠ'],[370,'P']].map(([x,label],i)=>rect(x-31,99,62,66,i===2?'di-tile':'di-cell')+text(x,139,label,'di-mark')).join('')+text(272,85,'one query')+text(220,224,'prepare → query → measure');
diagrams.xor=()=>{
  const ps=[[90,63],[220,63],[350,63]],v=[220,191];
  return ps.map((a,i)=>arrow(a,v,'di-line')+circle(...a,25,'di-tile')+text(a[0],69,['f(x)','g(y)','h(z)'][i],'di-mono')).join('')+rect(160,170,120,43,'di-tile')+text(220,197,'sum = target')+text(220,244,'all repeated copies must accept');
};
diagrams.spectrum=()=>{
  const hs=[22,35,14,96,29,153,47,19,105,31,23,60];
  return line([46,206],[404,206])+hs.map((h,i)=>rect(54+i*29,205-h,18,h,i===5||i===3||i===8?'di-solid':'di-tile',2)).join('')+text(220,240,'Fourier coefficients')+text(220,29,'structure in the spectrum');
};
diagrams.factory=()=>{
  const labels=['L3','L2','L1','L0','●'];
  return labels.map((label,i)=>rect(25+i*78,78,60,67,'di-tile')+text(55+i*78,119,label,'di-mark')+(i<4?arrow([88+i*78,111],[100+i*78,111]):'')).join('')
    +text(172,168,'four machine levels')+text(367,168,'apples')
    +p('M55 189V207H367V189','di-dash')+text(220,234,'one upgrade per turn · production from L0 upward');
};
function bins(online=false){
  const heights=[[50,31,42],[34,62,20],[75,40]],w=68;let s='';
  heights.forEach((hs,i)=>{const x=96+i*99;let y=206;s+=p(`M${x} 54V211H${x+w}V54`,'di-line');hs.forEach((h,j)=>{y-=h+3;s+=rect(x+6,y,w-12,h,palette[(i+j)%4],2);});});
  return s+text(220,239,'equal capacity · whole items')+(online?arrow([43,36],[152,36])+text(270,40,'items arrive in order'):text(220,33,'minimize the number of bins'));
}
diagrams.bins=()=>bins();diagrams['online-bins']=()=>bins(true);
diagrams.cluster=()=>{
  const ps=[[67,88],[141,69],[115,158],[271,80],[349,84],[310,163]],es=[[0,1],[0,2],[3,4],[3,5],[4,5]];
  return edges(ps,es)+line(ps[1],ps[2],'di-hot di-dash')+line(ps[2],ps[3],'di-danger di-dash')+nodes(ps)+text(151,136,'+','di-mark')+text(204,111,'−','di-mark')+text(220,227,'edit edges to form separate cliques');
};
diagrams.frequency=()=>{
  const ys=[70,111,152,193],xs=[126,280,178,343];let s='';ys.forEach((y,i)=>{s+=line([66,y],[383,y],'di-dash')+circle(xs[i],y,8,'di-solid')+text(40,y+5,`f${i+1}`,'di-mono');});return s+text(220,234,'assign frequencies · separate interfering links');
};
diagrams.forest=()=>tree(['r','v','w'])+text(220,242,'adjacent parents · bounded depth');
function graph(kind){
  let ps=graphPoints,es=graphEdges,s='';
  if(kind==='coloring')return edges(ps,es)+ps.map(([x,y],i)=>circle(x,y,10,palette[[0,1,0,1,0,1,2,3][i]])).join('');
  if(kind==='totalcolor'){
    // A triangle has a valid three-color total coloring.
    ps=ring(3,88);es=[[0,1],[1,2],[2,0]];
    return es.map(([a,b],i)=>line(ps[a],ps[b],`di-edge-${(i+2)%3}`)).join('')+ps.map(([x,y],i)=>circle(x,y,13,palette[i])).join('')+text(220,246,'color vertices and incident edges');
  }
  if(kind==='clique'){es=[...es,[1,5]];s+=edges(ps,[[1,5],[1,7],[5,7]],'di-hot');}
  if(kind==='partition'){
    ps=[[91,65],[170,90],[279,65],[355,90],[91,171],[170,196],[279,171],[355,196]];
    const block=v=>Math.floor(v/2);
    return [[53,35],[241,35],[53,141],[241,141]].map(([x,y],i)=>rect(x,y,146,92,'di-region',10)+text(x+73,y+78,`V${i+1}`)).join('')+edges(ps,es)+edges(ps,es.filter(([a,b])=>block(a)!==block(b)),'di-hot')+nodes(ps);
  }
  if(kind==='cut'){ps=ps.map((pt,i)=>i===7?[195,126]:pt);s+=rect(47,23,163,216,'di-region',18)+rect(230,23,167,216,'di-region',18);}
  if(kind==='dominating'){[0,2,4].forEach(i=>s+=circle(...ps[i],44,'di-region'));}
  s+=edges(ps,es);
  if(kind==='cut'||kind==='partition')s+=edges(ps,es.filter(([a,b])=>(ps[a][0]<220)!==(ps[b][0]<220)),'di-hot');
  if(kind==='clique')s+=edges(ps,[[1,5],[1,7],[5,7]],'di-hot');
  const sel=kind==='clique'?[1,5,7]:kind==='dominating'?[0,2,4]:kind==='vertexcover'?[0,2,4,5,7]:[];
  s+=nodes(ps,sel); return s;
}
['coloring','clique','cut','partition','dominating','vertexcover','totalcolor'].forEach(k=>diagrams[k]=()=>graph(k));
function schedule(kind){
  let s=''; const labels=kind==='nurse'?['N1','N2','N3','N4']:kind==='sports'?['A','B','C','D']:['R1','R2','R3','R4'];
  for(let r=0;r<4;r++){s+=text(65,78+r*40,labels[r],'di-mono');for(let c=0;c<6;c++){const on=(r+c)%3!==0;s+=rect(91+c*46,54+r*40,40,33,on?palette[(r+c)%4]:'di-cell',3);if(on)s+=text(111+c*46,76+r*40,kind==='nurse'?['D','N','E'][(r+c)%3]:kind==='sports'?['A','B','C','D'][(r+c+1)%4]:String((r+c)%5+1),'di-mono');}}
  return s+text(220,238,kind==='sports'?'illustrative round assignments':kind==='nurse'?'days →':'periods →');
}
diagrams.schedule=()=>schedule('course');diagrams.nurse=()=>schedule('nurse');
diagrams.sports=()=>{
  // Three rounds of K4, followed by the same pairings with venues reversed.
  const opponents=['BCD BCD','ADC ADC','DAB DAB','CBA CBA'].map(s=>s.replace(' ',''));
  let s='';
  for(let r=0;r<4;r++){
    s+=text(65,78+r*40,'ABCD'[r],'di-mono');
    for(let c=0;c<6;c++)s+=rect(91+c*46,54+r*40,40,33,c<3?'di-tile':'di-cell',3)+text(111+c*46,76+r*40,opponents[r][c],'di-mono');
  }
  return s+text(156,33,'first meetings')+text(296,33,'reverse venues')+text(220,238,'opponent in each round →');
};
diagrams.routing=()=>{
  const ps=[[220,128],[87,51],[66,169],[142,210],[320,43],[382,118],[326,205]];
  return edges(ps,[[0,1],[1,2],[2,3],[3,0]],'di-hot')+edges(ps,[[0,4],[4,5],[5,6],[6,0]],'di-secondary')+nodes(ps)+rect(208,116,24,24,'di-solid')+text(220,160,'depot')+text(220,242,'serve each customer once');
};
diagrams.feedback=()=>{
  const ps=ring(5);return ps.map((a,i)=>arrow(a,ps[(i+1)%5],i===0||i===4?'di-dash':'di-line')).join('')+nodes(ps)+circle(...ps[0],16,'di-outline')+text(ps[0][0],ps[0][1]+5,'×','di-mark')+text(220,239,'remove vertices to break every directed cycle');
};
diagrams.cutting=()=>rect(71,32,296,184,'di-region',0)+rect(71,32,106,100,'di-tile',0)+rect(71,132,106,84,'di-cell',0)+rect(177,32,121,69,'di-cell',0)+rect(177,101,121,115,'di-tile',0)+rect(298,32,69,184,'di-cell',0)+rect(323,143,15,18,'di-defect',0)+text(330,137,'defect')+text(220,244,'ordered pieces · guillotine cuts');
diagrams.hypergraph=()=>{
  const ps=[[104,128],[171,70],[213,145],[290,87],[326,171]];
  return p('M71 144Q55 68 167 41Q222 35 234 83Q256 156 71 144Z','di-region')+p('M145 62Q233 34 337 65Q383 94 329 142Q241 177 145 62Z','di-region')+p('M174 124Q290 71 352 153Q388 219 291 216Q193 211 174 124Z','di-region')+nodes(ps,[1,2])+text(220,249,'select vertices meeting every set');
};
diagrams.jobs=()=>{
  const jobs=[[[0,3,0],[4,2,2],[7,3,1]],[[0,2,1],[3,3,0],[6,2,2]],[[1,2,2],[3,3,1],[7,2,0]]];let s='';jobs.forEach((row,r)=>{s+=text(46,80+r*62,`M${r+1}`,'di-mono')+line([72,103+r*62],[390,103+r*62],'di-line');row.forEach(([start,dur,id])=>s+=rect(72+start*30,54+r*62,dur*30-4,39,palette[id],3)+text(72+(start+dur/2)*30,79+r*62,`J${id+1}`,'di-mono'));});return s+text(220,255,'time →');
};
diagrams.circuit=()=>{
  const ys=[65,107,153,195];let s=ys.map((y,i)=>text(42,y+5,`x${i+1}`,'di-mono')+line([60,y],[140,y])).join('');
  s+=p('M140 56H162A31 31 0 0 1 162 118H140Z','di-tile')+p('M140 144H162A31 31 0 0 1 162 206H140Z','di-cell')+text(164,94,'∧','di-mark')+text(164,182,'∧','di-mark');
  s+=p('M193 87H232V116H280M193 175H232V147H280','di-line')+p('M280 100H306A31 31 0 0 1 306 162H280Z','di-tile')+text(305,138,'∧','di-mark')+arrow([343,131],[395,131])+circle(273,116,5,'di-node')+circle(273,147,5,'di-node')+circle(342,131,5,'di-node')+text(220,244,'AND gates · circles mark inversion');return s;
};
diagrams.sat=()=>{
  const clauses=['x₁ ∨ ¬x₂','x₂ ∨ x₃','¬x₁ ∨ x₃'];return clauses.map((s,i)=>rect(98,43+i*62,242,44,i===0?'di-cell':'di-tile')+text(219,72+i*62,s,'di-mark')+text(68,72+i*62,i===0?'hard':'soft')).join('')+text(220,249,'choose one assignment for all clauses');
};
diagrams.assignment=()=>{
  let s='';for(let i=0;i<3;i++){s+=rect(62+i*120,67,76,130,'di-cell');for(let j=0;j<3;j++)s+=rect(73+i*120,80+j*34,54,24,palette[(i+j)%4]);}return s+p('M100 58C130 18 187 18 220 58','di-hot')+text(220,239,'capacity · service constraints · move cost');
};
diagrams.crossing=()=>{
  const a=[80,170,260,350].map(x=>[x,58]),b=[80,170,260,350].map(x=>[x,190]);
  return [[0,2],[1,0],[1,3],[2,1],[3,3]].map(([i,j])=>line(a[i],b[j],'di-hot')).join('')+nodes([...a,...b])+text(220,30,'fixed order')+arrow([130,224],[309,224])+text(220,251,'reorder only this layer');
};
diagrams.qap=()=>{
  const a=[[87,65],[87,132],[87,199]],b=[[329,65],[329,132],[329,199]];return [[0,2],[1,0],[2,1]].map(([i,j])=>arrow(a[i],b[j],'di-dash')).join('')+a.map((pt,i)=>circle(...pt,19,'di-tile')+text(pt[0],pt[1]+5,`F${i+1}`,'di-mono')).join('')+b.map((pt,i)=>rect(pt[0]-19,pt[1]-19,38,38,'di-cell')+text(pt[0],pt[1]+5,`L${i+1}`,'di-mono')).join('')+text(87,31,'facilities')+text(329,31,'locations');
};
diagrams.qbf=()=>{
  const ps=[[220,48],[121,135],[319,135]];
  return edges(ps,[[0,1],[0,2]])+circle(220,48,25,'di-tile')+text(220,54,'∀x','di-mark')+text(149,84,'x = 0')+text(291,84,'x = 1')+[1,2].map((i)=>rect(ps[i][0]-40,114,80,42,'di-tile')+text(ps[i][0],141,i===1?'y = 1':'y = 0','di-mono')+line([ps[i][0],156],[ps[i][0],184])+text(ps[i][0],204,'TRUE','di-mono')).join('')+text(220,248,'the response depends on the universal choice');
};
export const radiationExample = {
  intensity: [[1,3,2],[2,3,1]],
  shapes: [[[1,1,0],[0,1,1]],[[0,1,1],[1,1,0]]],
  times: [1,2],
};
diagrams.radiation=()=>{
  const matrices=[radiationExample.intensity,...radiationExample.shapes];
  let s='';
  matrices.forEach((rows,k)=>{
    const left=30+k*147;
    s+=text(left+43,49,k===0?'I':`${radiationExample.times[k-1]} × S${k===1?'₁':'₂'}`,'di-mark');
    rows.forEach((row,r)=>row.forEach((v,c)=>{
      s+=rect(left+c*30,80+r*38,26,32,k===0?'di-tile':v?'di-solid':'di-cell',2);
      s+=text(left+c*30+13,101+r*38,v,k>0&&v?'di-white':'di-mono');
    }));
  });
  return s+text(145,122,'=','di-mark')+text(292,122,'+','di-mark')
    +text(220,201,'same matrix dimensions · exact dose')
    +text(220,234,'two shapes · total beam-on time = 3');
};
diagrams.setcover=()=>{
  let s='';for(let r=0;r<5;r++)for(let c=0;c<7;c++){const v=(r+c)%3===0;s+=rect(83+c*39,43+r*34,31,27,c===1||c===3||c===5?'di-tile':'di-cell',1)+(v?circle(98+c*39,56+r*34,3,'di-solid'):'');}
  return s+text(220,236,'choose columns · cover every row');
};
diagrams.synthesis=()=>{
  const ps=[[220,53],[91,153],[220,153],[349,153]];
  return edges(ps,[[0,1],[0,2],[0,3]])+rect(190,30,60,45,'di-tile')+text(220,59,'ite','di-mark')+[[91,'x₁ < x₂'],[220,'x₂'],[349,'x₁']].map(([x,label])=>rect(x-42,132,84,42,'di-cell')+text(x,159,label,'di-mono')).join('')+text(91,197,'condition')+text(220,197,'then')+text(349,197,'else')+text(220,242,'a grammar expression for max(x₁, x₂)');
};
diagrams.tour=()=>{
  const ps=[[75,82],[174,43],[304,65],[368,156],[270,210],[176,166],[82,197]],es=ps.map((_,i)=>[i,(i+1)%ps.length]);
  return edges(ps,pairList(ps.length),'di-faint')+edges(ps,es,'di-hot di-flow')+nodes(ps)+text(220,244,'one closed tour');
};
diagrams.treewidth=()=>{
  const ps=[[220,52],[113,134],[326,134],[113,214]];let s=edges(ps,[[0,1],[0,2],[1,3]]);ps.forEach(([x,y],i)=>s+=rect(x-48,y-23,96,46,'di-tile')+text(x,y+5,['a, b, c','b, c, d','a, c, e','c, d, f'][i],'di-mono'));return s;
};
diagrams.ramsey=()=>{
  const ps=ring(7,88),es=pairList(7);return es.map(([a,b])=>line(ps[a],ps[b],b-a===1||b-a===6?'di-ramsey-red':'di-ramsey-blue')).join('')+nodes(ps)+text(220,246,'every edge gets one of two colors');
};
diagrams.progression=()=>{
  let s='';for(let i=0;i<21;i++)s+=circle(40+i*18,127,5,i%3?'di-blue-dot':'di-red-dot');for(let i=0;i<7;i++)s+=circle(58+i*54,127,11,'di-outline');
  return s+p('M58 104V88H112V104M112 104V88H166V104','di-line')+text(85,76,'d')+text(139,76,'d')+text(220,197,'seven equally spaced positions');
};
diagrams.cap=()=>{
  let s='';for(let r=0;r<3;r++)for(let c=0;c<3;c++)s+=circle(130+c*90,46+r*80,5,'di-dot');
  return s+line([130,46],[310,206],'di-danger di-dash')+nodes([[130,46],[220,126],[310,206]],[0,1,2])+text(220,240,'exclude distinct triples with x + y + z = 0');
};
diagrams.covercode=()=>{
  const ps=[[97,61],[213,61],[213,182],[97,182],[173,24],[329,24],[329,145],[173,145]],es=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  const first=new Set([0,1,3,4]);
  return edges(ps,es,'di-faint')
    +edges(ps,es.filter(([a,b])=>a===0||b===0),'di-hot')
    +edges(ps,es.filter(([a,b])=>a===6||b===6),'di-secondary')
    +ps.map(([x,y],i)=>circle(x,y,[0,6].includes(i)?8:5,first.has(i)?'di-color-a':'di-color-b')).join('')
    +circle(...ps[0],12,'di-outline')+circle(...ps[6],12,'di-outline')
    +text(80,40,'c₁')+text(350,135,'c₂')
    +text(220,243,'two graph-distance-one neighborhoods');
};
diagrams.binarycode=()=>{
  const words=['101100101101','010011010010','110010100001'];return words.map((w,r)=>[...w].map((b,c)=>rect(46+c*29,62+r*52,24,34,r<2&&w[c]!==words[1-r][c]?'di-tile':'di-cell',2)+text(58+c*29,85+r*52,b,'di-mono')).join('')).join('')+text(220,240,'count positions where words differ');
};
diagrams.stabilizer=()=>{
  const words=['XZZXI','IXZZX','XIXZZ','ZXIXZ'];return words.map((w,r)=>[...w].map((b,c)=>rect(102+c*48,39+r*44,39,34,b==='I'?'di-cell':'di-tile',3)+text(121+c*48,62+r*44,b,'di-mono')).join('')).join('')+text(220,242,'illustrative commuting Pauli generators');
};
diagrams.latin=()=>{
  let s='';for(let r=0;r<3;r++)for(let c=0;c<3;c++)s+=rect(109+c*74,34+r*68,65,59,palette[(r+c)%3],3)+text(141+c*74,71+r*68,`${(r+c)%3},${(r+2*c)%3}`,'di-mark');return s+text(220,252,'nine distinct pairs in this order-three example');
};
function petersen(){const a=ring(5,91),b=ring(5,42);return {ps:[...a,...b],es:[...a.map((_,i)=>[i,(i+1)%5]),...a.map((_,i)=>[i,i+5]),...a.map((_,i)=>[i+5,(i+2)%5+5])]};}
diagrams.cage=()=>{const {ps,es}=petersen();return edges(ps,es)+nodes(ps)+text(220,246,'the Petersen graph: degree 3, girth 5');};
diagrams.sort=()=>{
  let s='';[60,104,148,192].forEach((y,i)=>s+=line([50,y],[390,y])+text(31,y+5,[1,0,1,0][i],'di-mono')+text(409,y+5,i<2?0:1,'di-mono'));
  [[105,0,1],[105,2,3],[195,0,2],[195,1,3],[294,1,2]].forEach(([x,a,b])=>s+=line([x,60+a*44],[x,60+b*44],'di-hot')+circle(x,60+a*44,4,'di-solid')+circle(x,60+b*44,4,'di-solid'));
  return s+text(220,241,'a complete four-wire sorting example');
};
diagrams.c5=()=>{
  const ps=ring(5,66),extra=ring(15,108);return extra.map((a,i)=>line(a,ps[Math.floor(i/3)],'di-faint')+circle(...a,3,'di-dot')).join('')+edges(ps,ps.map((_,i)=>[i,(i+1)%5]),'di-hot di-flow')+nodes(ps,[0,1,2,3,4]);
};
diagrams.kissing=()=>{
  const ps=ring(6,68),center=[220,125];return ps.map(a=>circle(...a,34,'di-region')).join('')+circle(...center,34,'di-tile')+line(center,ps[0],'di-hot')+line(center,ps[1],'di-hot')+p('M220 102A23 23 0 0 1 240 113','di-hot')+text(246,96,'60°')+circle(...center,3,'di-solid');
};
diagrams.circles=()=>{
  let s=rect(121,24,198,198,'di-outline',0);for(let i=0;i<5;i++)for(let j=0;j<5;j++)s+=circle(141+i*39,44+j*39,19,'di-region');return s+text(220,251,'inside the square · pairwise non-overlap');
};
diagrams.sphere=()=>{
  let s=circle(220,124,95,'di-region')+'<ellipse cx="220" cy="124" rx="95" ry="29" class="di-dash"/><ellipse cx="220" cy="124" rx="40" ry="95" class="di-dash"/>';
  for(let i=0;i<50;i++){const y=-1+2*(i+.5)/50,a=i*2.39996,x=Math.sqrt(1-y*y)*Math.cos(a);s+=circle(220+x*89,124+y*89,3.5,'di-solid');}
  return s+text(220,248,'maximize the smallest pairwise angle');
};
diagrams.integrality=()=>{
  const a=ring(6,60,112,125),b=ring(6,60,326,125);return edges(a,pairList(6),'di-faint')+edges(a,a.map((_,i)=>[i,(i+1)%6]),'di-hot')+nodes(a)+edges(b,[[0,2],[2,4],[4,0],[1,3],[3,5],[5,1]],'di-hot di-dash')+edges(b,[[0,1],[2,3],[4,5]],'di-line')+nodes(b)+text(112,229,'whole edges')+text(326,229,'fractional weights')+text(220,129,'/','di-mark');
};
diagrams['graph-gap']=()=>{
  const a=[57,127],b=[382,127];let s='';for(const y of [52,127,202]){const ps=[a,[138,y],[220,y],[301,y],b];s+=edges(ps,[[0,1],[1,2],[2,3],[3,4]])+nodes(ps);}return s+text(220,243,'graph distances define the metric');
};
diagrams.rectilinear=()=>{
  const ps=[[70,186],[140,72],[220,175],[300,54],[371,184]];let s='';for(let x=70;x<=371;x+=30)s+=line([x,30],[x,218],'di-faint');for(let y=38;y<=218;y+=30)s+=line([45,y],[400,y],'di-faint');
  return s+p('M70 186V72H140V175H220V54H300V184H371','di-hot')+nodes(ps)+text(220,249,'horizontal distance + vertical distance');
};
diagrams.influence=()=>rect(55,74,133,66,'di-cell')+text(122,115,'0101','di-mono')+rect(253,74,133,66,'di-tile')+text(320,115,'0111','di-mono')+arrow([197,107],[244,107])+text(220,59,'flip coordinate i')+text(122,178,'p(x)')+text(320,178,'p(xⁱ)')+text(220,231,'measure the squared change');
diagrams.nonzero=()=>rect(66,65,124,124,'di-region',3)+text(128,138,'A','di-question')+text(216,135,'×','di-mark')+[0,1,2,3].map((v,i)=>rect(239,65+i*32,33,27,'di-tile')+text(255,83+i*32,`x${['₁','₂','₃','₄'][i]}`,'di-mono')).join('')+text(303,135,'=','di-mark')+[0,1,2,3].map((v,i)=>rect(329,65+i*32,39,27,'di-cell')+text(349,83+i*32,'≠0','di-mono')).join('')+text(128,51,'invertible')+text(255,51,'xᵢ ≠ 0')+text(220,231,'both vectors avoid zero in every coordinate');
diagrams['directed-cycle']=()=>{
  const ps=ring(7,85);return ps.map((a,i)=>arrow(a,ps[(i+1)%7],'di-hot')+arrow(a,ps[(i+2)%7],'di-faint')).join('')+nodes(ps)+text(220,250,'out-degree forces a short directed cycle?');
};
diagrams.decision=()=>tree(['x₁','x₂','x₃']).replace(/x[1-4](?=<\/text>)/g,match=>Number(match[1])%2)+text(161,79,'0')+text(281,79,'1')+text(220,245,'query one bit · choose the next branch');
diagrams['edge-query']=()=>{const ps=ring(6,86);return edges(ps,pairList(6),'di-dash')+line(ps[0],ps[2],'di-hot')+nodes(ps)+text(220,134,'?','di-question')+text(220,248,'does this edge exist?');};
diagrams.paley=()=>{
  const ps=ring(13,91),es=pairList(13).filter(([a,b])=>[1,3,4,9,10,12].includes((b-a+13)%13));return edges(ps,es,'di-faint')+nodes(ps)+text(220,131,'P₁₃','di-mark')+text(220,248,'adjacency from quadratic residues');
};
diagrams.rigidity=()=>group(matrix(5,5,'hilbert'),54,0)+text(220,238,'how many entries must change to lower rank?');
diagrams.frege=()=>[0,1,2,3].map((i)=>rect(86,31+i*51,268,37,i===3?'di-tile':'di-cell')+text(220,55+i*51,['φ','φ → ψ','ψ','⋮  conclusion'][i],'di-mark')).join('');
diagrams.extension=()=>tree(['∧','D','D'])+rect(166,218,108,32,'di-tile')+text(220,240,'p ↔ D','di-mark');
diagrams.composition=()=>{
  const ps=[[82,174],[220,174],[358,174]],out=[220,58];return ps.map(a=>line(a,out)+rect(a[0]-32,a[1]-24,64,48,'di-cell')+text(a[0],a[1]+6,'g','di-mark')).join('')+rect(188,34,64,48,'di-tile')+text(220,65,'f','di-mark')+[82,220,358].map((x,i)=>text(x,224,`block ${i+1}`)).join('');
};
export const communicationExample = [[0,0,0,0],[0,1,0,1],[0,0,1,1],[0,1,1,0]];
diagrams.communication=()=>{
  let s='';for(let r=0;r<4;r++)for(let c=0;c<4;c++){const v=communicationExample[r][c];s+=rect(220+c*38,42+r*39,33,33,v?'di-tile':'di-cell',2)+text(236+c*38,64+r*39,v,'di-mono');}
  return s+circle(76,78,24,'di-tile')+text(76,83,'A','di-mark')+circle(76,178,24,'di-cell')+text(76,183,'B','di-mark')+arrow([68,109],[68,147])+arrow([86,147],[86,109])+line([109,78],[205,78],'di-dash')+text(128,121,'bits')+text(296,232,'communication matrix');
};
diagrams.hamilton=()=>{
  const {ps,es}=petersen(),route=[0,1,2,3,4,9,6,8,5,7];return edges(ps,es)+edges(ps,route.slice(1).map((v,i)=>[route[i],v]),'di-hot di-flow')+nodes(ps)+text(220,247,'a Hamiltonian path in the Petersen graph');
};
diagrams.mds=()=>{
  let s='';
  for(let i=0;i<4;i++)s+=rect(148+i*37,34,30,37,'di-tile')+text(163+i*37,59,`m${i+1}`,'di-mono');
  s+=arrow([220,80],[220,120]);
  for(let i=0;i<8;i++)s+=rect(72+i*37,134,30,37,[1,3,4,7].includes(i)?'di-tile':'di-cell')+text(87+i*37,159,[1,3,4,7].includes(i)?`c${i+1}`:'?','di-mono');
  return s+text(220,206,'any k known coordinates recover the message')+text(220,243,'a schematic [n, k] MDS code');
};
diagrams.threshold=()=>gate('≥ k');diagrams.modular=()=>gate('mod m');
function gate(label){return [68,107,146,185].map(y=>line([69,y],[176,126])+circle(69,y,4,'di-node')).join('')+rect(176,89,110,74,'di-tile')+text(231,134,label,'di-mark')+arrow([286,126],[374,126])+text(220,232,'combine many input bits in one gate');}
diagrams.branching=()=>{
  let s='';for(let c=0;c<6;c++)for(let r=0;r<4;r++){if(c<5){s+=line([62+c*63,53+r*49],[125+c*63,53+((r+c)%4)*49],'di-faint')+line([62+c*63,53+r*49],[125+c*63,53+((r+1)%4)*49],'di-dash');}}
  for(let c=0;c<6;c++)for(let r=0;r<4;r++)s+=circle(62+c*63,53+r*49,5,c===0&&r===0?'di-solid':'di-node');return s+text(220,240,'four states per layer · read each bit once');
};
function smallMatrix(x,y,name){let s='';for(let i=0;i<3;i++)for(let j=0;j<3;j++)s+=rect(x+j*22,y+i*22,19,19,(i+j)%3?'di-tile':'di-cell',1);return s+text(x+31,y-13,name,'di-mark');}
diagrams.multiply=()=>smallMatrix(53,90,'A')+text(147,134,'×','di-mark')+smallMatrix(184,90,'B')+text(278,134,'=','di-mark')+smallMatrix(314,90,'C')+text(220,218,'how close can the exponent get to two?');
diagrams.matching=()=>{
  const a=[52,106,160,214].map(y=>[105,y]),b=[52,106,160,214].map(y=>[328,y]);return [[0,0],[0,1],[1,0],[2,1],[2,3],[3,2]].map(([i,j])=>line(a[i],b[j],'di-faint')).join('')+[[0,1],[1,0],[3,2]].map(([i,j])=>line(a[i],b[j],'di-hot')).join('')+nodes([...a,...b])+text(105,28,'arriving')+text(328,28,'available');
};
diagrams.permanent=()=>smallMatrix(67,84,'A')+arrow([159,116],[223,116])+text(321,101,'a₁₁a₂₂a₃₃','di-mono')+text(321,137,'+ a₁₂a₂₃a₃₁','di-mono')+text(321,173,'+ ⋯','di-mark')+text(220,228,'one entry from each row and column');
diagrams.sumset=()=>{
  const a=[1,3,5,7],b=[2,4,6,8,10,12,14];return text(40,90,'A','di-mark')+a.map(v=>circle(102+v*18,86,6,'di-solid')).join('')+text(40,178,'A+A','di-mark')+b.map(v=>circle(76+v*18,174,6,'di-node')).join('')+arrow([220,109],[220,144])+text(220,235,'small doubling · additive structure');
};
diagrams.embedding=()=>{
  const ps=[[60,126],[111,65],[165,126],[110,190]];return edges(ps,[[0,1],[1,2],[2,3],[3,0],[0,2]])+nodes(ps)+arrow([188,126],[242,126])+p('M274 186V65M274 186H390','di-line')+p('M291 159H362V94','di-hot')+nodes([[291,159],[362,94]],[0,1])+text(110,232,'graph metric')+text(332,232,'ℓ₁ distance');
};
diagrams.polar=()=>{
  let s=circle(58,129,16,'di-tile')+text(58,134,'W');for(let i=0;i<2;i++){const y=75+i*109;s+=line([76,129],[174,y])+circle(186,y,19,'di-node')+text(186,y+5,i?'W⁺':'W⁻');for(let j=0;j<2;j++){const z=47+i*123+j*57;s+=line([207,y],[323,z])+circle(336,z,13,j?'di-solid':'di-node');}}return s+text(220,246,'recursive channel polarization');
};
diagrams.ryser=()=>{
  let s='';const ps=[];for(let c=0;c<3;c++){s+=rect(73+c*121,29,53,191,'di-region',20);for(let r=0;r<3;r++)ps.push([100+c*121,60+r*63]);}s+=p(`M${ps[0]}L${ps[4]}L${ps[8]}L${ps[0]}`,'di-hot')+p(`M${ps[1]}L${ps[5]}L${ps[6]}L${ps[1]}`,'di-secondary');return s+nodes(ps,[4,5])+text(220,248,'one vertex from each part per hyperedge');
};
diagrams.triangles=()=>{
  const ps=[[69,168],[143,50],[220,168],[295,50],[370,168]];return edges(ps,[[0,1],[1,2],[2,0],[2,3],[3,4],[4,2]])+edges(ps,[[0,1],[3,4]],'di-hot')+nodes(ps)+text(220,238,'pack triangles · cover triangles with edges');
};
diagrams['parity-tree']=()=>{
  const ps=[[220,45],[121,119],[319,119],[75,196],[165,196],[275,196],[365,196]];
  return edges(ps,[[0,1],[0,2],[1,3],[1,4],[2,5],[2,6]])+ps.map(([x,y],i)=>i<3?rect(x-46,y-18,92,36,'di-tile')+text(x,y+5,['x₁⊕x₂','x₃⊕x₄','x₁⊕x₃'][i],'di-mono'):circle(x,y,14,'di-node')+text(x,y+5,i%2,'di-mono')).join('')+text(220,246,'each query asks for the parity of a subset');
};

export function renderIllustration(task,{thumbnail=false,motion=false}={}) {
  const draw=diagrams[task.drawing];
  if(!draw)throw new Error(`Missing illustration ${task.id}: ${task.drawing}`);
  const content = draw();
  return `<svg class="task-illustration" viewBox="0 0 440 270" ${thumbnail?'aria-hidden="true"':`role="img" aria-label="${esc(task.diagramCaption)}"`} focusable="false">${motion?`<g class="pv-scene">${content}</g>`:content}</svg>`;
}
export const drawingNames=Object.keys(diagrams);
