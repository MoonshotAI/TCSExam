// Credits for the original competitions and benchmark collections.
// Task membership follows the paper catalogue; these links identify upstream
// sources and do not imply affiliation or endorsement.
export const benchmarkSources = [
  {key:'pace',label:'PACE Challenge',url:'https://pacechallenge.org/'},
  {key:'dimacs',label:'DIMACS Challenges',url:'https://dimacs.rutgers.edu/programs/implementation-challenges'},
  {key:'roadef',label:'ROADEF / EURO Challenge',url:'https://roadef.org/app/pages/le-challenge-roadef'},
  {key:'atcoder',label:'AtCoder Heuristic Contests',url:'https://atcoder.jp/contests/'},
  {key:'iwls',label:'IWLS Programming Contest',url:'https://iwls.org/iwls2023/'},
  {key:'itc2007',label:'ITC 2007',url:'https://www.eeecs.qub.ac.uk/itc2007/'},
  {key:'itc2021',label:'ITC 2021',url:'https://robinxval.ugent.be/ITC2021/'},
  {key:'inrc',label:'INRC-I',url:'https://patatconference.org/patat2010/proceedings/3_9.pdf'},
  {key:'maxsat',label:'MaxSAT Evaluation',url:'https://maxsat-evaluations.github.io/'},
  {key:'qbf',label:'QBFEVAL',url:'https://www.qbflib.org/qbfeval20.php'},
  {key:'sygus',label:'SyGuS-Comp',url:'https://github.com/SyGuS-Org/benchmarks'},
  {key:'minizinc',label:'MiniZinc Challenge',url:'https://www.minizinc.org/challenge/'},
  {key:'bpplib',label:'BPPLIB',url:'https://github.com/mdelorme2/BPPLIB'},
  {key:'cvrplib',label:'CVRPLIB',url:'https://galgos.inf.puc-rio.br/cvrplib/'},
  {key:'qaplib',label:'QAPLIB',url:'https://qaplib.mgi.polymtl.ca/'},
  {key:'tsplib',label:'TSPLIB',url:'https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/'},
  {key:'orlib',label:'OR-Library',url:'https://people.brunel.ac.uk/~mastjjb/jeb/info.html'},
  {key:'jsplib',label:'JSPLib / ScheduleOpt',url:'https://github.com/ScheduleOpt/benchmarks/tree/main/jobshop'},
  {key:'mqlib',label:'MQLib',url:'https://github.com/MQLib/MQLib'},
  {key:'calma',label:'CALMA / CELAR',url:'https://fap.zib.de/problems/CALMA/'},
  {key:'color',label:'COLOR02',url:'https://mat.tepper.cmu.edu/COLOR02/'},
  {key:'walshaw',label:'Walshaw Partition Archive',url:'https://chriswalshaw.co.uk/partition/'},
];
const original = Object.fromEntries(benchmarkSources.map(s=>[s.key,s]));
const source=(key,label,url)=>({label:label||original[key].label,url:url||original[key].url});
const solverSources = {
  'ahc058-atcoder':source('atcoder','AtCoder Heuristic Contest 058','https://atcoder.jp/contests/ahc058'),
  'bpp-bpplib':source('bpplib'),
  'ce-pace2021':source('pace','PACE 2021','https://pacechallenge.org/2021/'),
  'celar-rlfap':source('calma'),
  'christmas-tree-ahc041':source('atcoder','AtCoder Heuristic Contest 041','https://atcoder.jp/contests/ahc041'),
  'coloring-dimacs':source('color','DIMACS / COLOR02'),
  'curriculum-itc2007':source('itc2007'),
  'cvrp-cvrplib':source('cvrplib'),
  'dfvs-pace2022':source('pace','PACE 2022','https://pacechallenge.org/2022/'),
  'ds-pace2025':source('pace','PACE 2025','https://pacechallenge.org/2025/'),
  'glasscut-roadef2018':source('roadef','ROADEF / EURO Challenge 2018','https://roadef.org/challenge/2018/en/'),
  'gp-dimacs10':source('walshaw','DIMACS10 / Walshaw Partition Archive'),
  'hs-pace2025':source('pace','PACE 2025','https://pacechallenge.org/2025/'),
  'itc2021-sports-timetabling':source('itc2021'),
  'jsplib-jssp':source('jsplib'),
  'logic-syn-iwls2023':source('iwls','IWLS 2023 Programming Contest'),
  'maxclique-dimacs':source('dimacs','DIMACS Clique Benchmarks','https://dimacs.rutgers.edu/programs/implementation-challenges'),
  'maxcut-mqlib':source('mqlib'),
  'maxsat-mse':source('maxsat','MaxSAT Evaluation 2026'),
  'mr-roadef2012':source('roadef','ROADEF / EURO Challenge 2012','https://roadef.org/challenge/2012/en/'),
  'nurse-inrc':source('inrc'),
  'oscm-pace2024':source('pace','PACE 2024','https://pacechallenge.org/2024/'),
  'qap-qaplib':source('qaplib'),
  'qbf-qbfeval':source('qbf',"QBFEVAL ’20"),
  'radiation-mznchallenge':source('minizinc'),
  'scp-orlib':source('orlib'),
  'sygus-comp':source('sygus','SyGuS-Comp 2017–2019'),
  'tsp-tsplib':source('tsplib'),
  'tw-heuristic':source('pace','PACE 2017','https://pacechallenge.org/2017/'),
  'vc-pace2019':source('pace','PACE 2019','https://pacechallenge.org/2019/'),
};
export function taskSource(task) {
  if(task.track==='solver') return solverSources[task.id];
  if(task.citation_url) return {label:'Original paper',url:task.citation_url};
  return null;
}
