import graph from "../public/paper/research-graph.json" with { type: "json" };

// Original illustrations of research objects. The corners and circuit are
// explanatory examples, the graph neighborhood is from the submitted result,
// and the communication matrix is the one used in paper Figure 1.
const circle = (x,y,r,cls,attrs="") => `<circle cx="${x}" cy="${y}" r="${r}" class="${cls}" ${attrs}/>`;
const path = (d,cls,attrs="") => `<path d="${d}" class="${cls}" ${attrs}/>`;
const text = (x,y,value,cls) => `<text x="${x}" y="${y}" class="${cls}">${value}</text>`;
const line = (a,b,cls) => path(`M${a.join(" ")}L${b.join(" ")}`,cls);
const gridPoint = (i,j) => [64+i*24,29+j*24];
const matrix = [[0,0,0,0],[0,1,0,1],[0,0,1,1],[0,1,1,0]];

function corners() {
  let art="";
  for(let i=0;i<9;i++) {
    for(let j=0;j<9;j++) {
      const [x,y]=gridPoint(i,j);
      art+=circle(x,y,2.5,"plate-grid-node",`data-grid-i="${i}" data-grid-j="${j}"`);
    }
  }
  return art+[[1,2,3],[4,4,3],[2,5,2]].map(([i,j,d],index)=>{
    const points=[[i+d,j],[i,j],[i,j+d]].map(([a,b])=>gridPoint(a,b));
    const route=points.map((p,i)=>`${i?"L":"M"}${p.join(" ")}`).join("");
    return `<g class="plate-corner" style="--step:${index}">
      ${path(route,"plate-corner-base")}
      <g class="plate-corner-active">${path(route,"plate-corner-line")}${points.map(([x,y])=>circle(x,y,5.3,"plate-corner-dot")).join("")}</g>
    </g>`;
  }).join("");
}

function circuit() {
  // (x0 AND x1) OR (x2 AND x3), illustrated with input 1101 and output 1.
  const wires=[
    ["M35 58H64Q76 58 76 70V76Q76 84 84 84H107",1],
    ["M35 105H107",1],
    ["M35 153H67Q76 153 76 161V166Q76 174 84 174H107",0],
    ["M35 200H67Q76 200 80 195H107",1],
    ["M151 94H172Q182 94 182 104V116Q182 125 191 125H223",1],
    ["M151 184H172Q182 184 182 174V157Q182 148 191 148H223",0],
    ["M259 137H285",1],
  ];
  let art=wires.map(([d,active],i)=>path(d,"plate-wire")+(active?path(d,"plate-signal",`pathLength="1" style="--step:${i}"`):"")).join("");
  [[35,58,1],[35,105,1],[35,153,0],[35,200,1],[285,137,1]].forEach(([x,y,value])=>{
    art+=circle(x,y,10,value?"plate-terminal on":"plate-terminal off")+text(x,y+4,value,"plate-bit");
  });
  [[107,70,"∧",1],[107,160,"∧",0],[215,113,"∨",1]].forEach(([x,y,op,value])=>{
    const shape=op==="∧" ? `M${x} ${y}H${x+20}A24 24 0 0 1 ${x+20} ${y+48}H${x}Z` :
      `M${x} ${y}Q${x+30} ${y} ${x+44} ${y+24}Q${x+30} ${y+48} ${x} ${y+48}Q${x+14} ${y+24} ${x} ${y}Z`;
    art+=`<g class="plate-gate" data-operation="${op}" data-output="${value}">${path(shape,`plate-gate-face ${value?"on":"off"}`)}${text(x+22,y+31,op,"plate-gate-symbol")}</g>`;
  });
  return art;
}

function construction() {
  // Show the five-cycle and its incident edges, preserving real vertex IDs.
  // The full 124-vertex / 630-edge graph remains available in the result case.
  const cycle=graph.highlighted_cycle, selected=new Set(cycle);
  const edges=graph.edges.filter(([a,b])=>selected.has(a)||selected.has(b));
  const positions=new Map();
  cycle.forEach((id,index)=>{
    const angle=-Math.PI/2+index*2*Math.PI/5;
    positions.set(id,[160+47*Math.cos(angle),125+47*Math.sin(angle)]);
    const neighbors=edges.flatMap(([a,b])=>a===id?[b]:b===id?[a]:[]).filter(v=>!selected.has(v));
    neighbors.forEach((v,i)=>{
      const theta=angle+(i-(neighbors.length-1)/2)*.108;
      const radius=103;
      positions.set(v,[160+radius*Math.cos(theta),125+radius*Math.sin(theta)]);
    });
  });
  let art=`<g class="plate-network-edges">${edges.map(([a,b])=>path(`M${positions.get(a).join(" ")}L${positions.get(b).join(" ")}`,"",`data-a="${a}" data-b="${b}"`)).join("")}</g>`;
  art+=`<g class="plate-network-nodes">${[...positions].map(([id,[x,y]])=>circle(x,y,selected.has(id)?5:2.6,"",`data-vertex="${id}"`)).join("")}</g>`;
  const route=cycle.map((id,i)=>`${i?"L":"M"}${positions.get(id).join(" ")}`).join("")+"Z";
  art+=path(route,"plate-cycle-back")+path(route,"plate-cycle",'pathLength="1"');
  art+=cycle.map(id=>circle(...positions.get(id),5,"plate-cycle-node",`data-cycle-vertex="${id}"`)).join("");
  return art;
}

function communication() {
  let art=path("M127 48H121V202H127M283 48H289V202H283","plate-matrix-bracket");
  art+=matrix.map((row,r)=>row.map((value,c)=>{
    const x=135+c*36,y=57+r*36;
    return `<g class="plate-matrix-cell" data-row="${r}" data-col="${c}" data-value="${value}" style="--step:${r}">
      <rect x="${x}" y="${y}" width="31" height="31" rx="2" class="plate-matrix-square ${value?"one":"zero"}"/>
      ${text(x+15.5,y+21,value,`plate-matrix-digit ${value?"one":"zero"}`)}
    </g>`;
  }).join("")).join("");
  art+=path("M63 76H101M63 174H101","plate-matrix-link");
  const routes=["M36 96V151","M58 151V96"];
  art+=routes.map((d,i)=>path(d,"plate-channel")+path(d,"plate-channel-bit",`pathLength="1" style="--step:${i}"`)).join("");
  art+=path("M32 146L36 151L40 146M54 101L58 96L62 101","plate-channel-arrow");
  [[47,76,"A"],[47,174,"B"]].forEach(([x,y,letter])=>{
    art+=circle(x,y,15,"plate-party")+text(x,y+5,letter,"plate-party-letter");
  });
  return art;
}

const drawings={theorem:corners,solver:circuit,construction,open:communication};
export function renderPlate(track) {
  return `<svg viewBox="0 0 320 250" aria-hidden="true" focusable="false">${drawings[track]()}</svg>`;
}
