(function(){
if(window.__DJAEGER_WORK_SKIN__) return;
window.__DJAEGER_WORK_SKIN__=true;
document.title='DJAEGER WORK';

const css=`
:root{--bg:#020812!important;--panel:#071a2d!important;--panel2:#091827!important;--line:#173a5d!important;--text:#f5f7fb!important;--muted:#97a5ba!important;--ok:#39e77a!important;--accent:#3f91ff!important;--warn:#e4b54d!important;--bad:#ff6975!important}
html,body{background:radial-gradient(circle at 55% -10%,#0b1c31 0,#020812 46%,#01050b 100%)!important;color:var(--text)!important}
body{padding-bottom:78px!important}
main{max-width:520px!important;padding:12px 17px 24px!important;margin:0 auto!important}
.dw-top{display:grid!important;grid-template-columns:66px minmax(0,1fr) 38px auto!important;align-items:center!important;gap:8px!important;margin:0!important;padding:10px 0 13px!important;position:sticky!important;top:0!important;z-index:30!important;background:linear-gradient(#020812 78%,rgba(2,8,18,.94))!important}
.dw-logo{width:66px!important;height:58px!important;object-fit:contain!important}
.dw-brand{min-width:0!important}
.dw-brandline{font-size:21px!important;font-weight:900!important;line-height:1.05!important;white-space:nowrap!important;color:#f7f9fd!important}
.dw-brandline b{color:#3f91ff!important}
.dw-tag{font-size:7px!important;font-weight:800!important;letter-spacing:3px!important;color:#c0c8d6!important;margin-top:6px!important;white-space:nowrap!important}
.dw-refresh{width:38px!important;height:38px!important;border:1px solid #1b416a!important;border-radius:10px!important;background:linear-gradient(160deg,#10223a,#091525)!important;color:#dce7f5!important;font-size:21px!important;padding:0!important;margin:0!important}
.dw-refresh.spin{animation:dwspin .7s linear infinite!important}
@keyframes dwspin{to{transform:rotate(360deg)}}
#online{min-width:82px!important;height:38px!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0 9px!important;border-radius:22px!important;font-size:11px!important;font-weight:900!important;margin:0!important;border:1px solid #155137!important;background:#062218!important;color:var(--ok)!important;white-space:nowrap!important}
#online.bad{border-color:#542b34!important;background:#2a1119!important;color:var(--bad)!important}
#online.warn{border-color:#5b4a20!important;background:#271f0d!important;color:var(--warn)!important}
.sub,.nav{display:none!important}
.dw-hero{padding:24px 4px 18px!important}
.dw-greet{color:#9aa7ba!important;font-size:16px!important;margin-bottom:6px!important}
.dw-hero h2{font-size:29px!important;line-height:1.08!important;margin:0 0 7px!important;letter-spacing:-.5px!important}
.dw-hero p{margin:0!important;color:#8e9db2!important;font-size:17px!important}
section.card{background:linear-gradient(145deg,rgba(12,34,57,.98),rgba(5,18,31,.98))!important;border:1px solid #173a5d!important;border-radius:18px!important;padding:16px!important;margin:14px 0!important;box-shadow:0 12px 28px #0005!important}
section.card h3{font-size:18px!important;margin:0 0 13px!important;color:#f4f7fb!important}
.grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}
.box{background:#071522!important;border:1px solid #102d48!important;border-radius:11px!important;padding:11px!important;min-width:0!important}
.k{font-size:9px!important;color:#94a2b6!important;letter-spacing:.07em!important}
.v{font-size:16px!important;margin-top:4px!important;overflow-wrap:anywhere!important}
.small{font-size:10px!important}
button,input{border-radius:10px!important}
button{padding:10px 11px!important;font-size:11px!important}
button.primary{background:linear-gradient(90deg,#276edb,#398eff)!important;border-color:#3d86f1!important}
button.danger{background:#54202a!important}
input{width:100%!important;margin:4px 0 8px!important;background:#061321!important;border-color:#234463!important}
pre{font-size:10px!important;max-height:220px!important;background:#02070d!important;border:1px solid #102c47!important}
table{font-size:10px!important}
td,th{padding:7px 5px!important}
.pipeline{gap:5px!important}
.step{font-size:9px!important;padding:6px 7px!important}
.dw-daily{display:none}
.dw-daily h3{display:flex!important;align-items:center!important;gap:8px!important}
.dw-daily .dw-brief-text{color:#c5cfdd!important;line-height:1.5!important;font-size:12px!important}
.dw-research-summary{display:none}
.dw-summary-grid{display:grid!important;grid-template-columns:repeat(3,1fr)!important;gap:8px!important}
.dw-summary-cell{text-align:center!important;padding:10px 4px!important;background:#071522!important;border:1px solid #102d48!important;border-radius:11px!important}
.dw-summary-cell strong{display:block!important;font-size:20px!important}
.dw-summary-cell span{display:block!important;font-size:9px!important;color:#98a6b9!important;margin-top:3px!important}
.dw-bottom{position:fixed!important;left:0!important;right:0!important;bottom:0!important;height:70px!important;background:rgba(4,15,27,.96)!important;border-top:1px solid #18324f!important;display:flex!important;z-index:50!important;backdrop-filter:blur(12px)!important}
.dw-tab{position:relative!important;flex:1!important;border:0!important;background:transparent!important;color:#8e9bb0!important;padding:7px 1px 5px!important;margin:0!important;font-size:9px!important;font-weight:700!important;border-radius:0!important}
.dw-tab svg{display:block!important;width:21px!important;height:21px!important;margin:0 auto 4px!important;stroke:currentColor!important;fill:none!important;stroke-width:2!important}
.dw-tab.active{color:#4c9aff!important}
.dw-tab.active:after{content:'';position:absolute;left:31%;right:31%;bottom:3px;height:2px;border-radius:3px;background:#3d8cff}
.dw-hidden{display:none!important}
@media(max-width:350px){.dw-top{grid-template-columns:57px minmax(0,1fr) 35px auto!important;gap:6px!important}.dw-logo{width:57px!important;height:50px!important}.dw-brandline{font-size:18px!important}.dw-tag{font-size:6px!important;letter-spacing:2.2px!important}.dw-refresh{width:35px!important;height:35px!important}#online{min-width:72px!important;height:35px!important;font-size:10px!important}.dw-hero h2{font-size:26px!important}}
`;
const style=document.createElement('style');style.id='djaeger-work-skin';style.textContent=css;document.head.appendChild(style);

const main=document.querySelector('main');
if(!main)return;
const oldTitle=main.querySelector('h1');
const online=document.getElementById('online');
if(oldTitle&&online){
  oldTitle.className='dw-top';
  oldTitle.innerHTML='';
  const logo=document.createElement('img');logo.className='dw-logo';
  try{logo.src=DjaegerNative.logoData()}catch(e){}
  const brand=document.createElement('div');brand.className='dw-brand';brand.innerHTML='<div class="dw-brandline">DJAEGER <b>WORK</b></div><div class="dw-tag">WORK · RESEARCH · GROW</div>';
  const refresh=document.createElement('button');refresh.className='dw-refresh';refresh.setAttribute('aria-label','Refresh all');refresh.textContent='↻';
  refresh.onclick=function(){refresh.classList.add('spin');location.reload()};
  oldTitle.appendChild(logo);oldTitle.appendChild(brand);oldTitle.appendChild(refresh);oldTitle.appendChild(online);
}
const sub=main.querySelector('.sub');if(sub)sub.style.display='none';
const oldNav=main.querySelector('.nav');if(oldNav)oldNav.style.display='none';

const hero=document.createElement('div');hero.className='dw-hero';hero.innerHTML='<div class="dw-greet">Good Afternoon</div><h2>Let’s Make Progress</h2><p>Smarter work ahead.</p>';
if(oldTitle)oldTitle.insertAdjacentElement('afterend',hero);
const hour=new Date().getHours();hero.querySelector('.dw-greet').textContent=hour<11?'Good Morning':hour<17?'Good Afternoon':'Good Evening';

const today=document.getElementById('today');
const daily=document.createElement('section');daily.className='card dw-daily';daily.id='dw-daily';daily.innerHTML='<h3>Daily Brief</h3><div class="dw-brief-text">Loading latest brief…</div>';
if(today)today.insertAdjacentElement('afterend',daily);

const trends=document.getElementById('trends');
const researchSummary=document.createElement('section');researchSummary.className='card dw-research-summary';researchSummary.id='dw-research-summary';
researchSummary.innerHTML='<h3>Research Summary</h3><div class="dw-summary-grid"><div class="dw-summary-cell"><strong id="dw-total">–</strong><span>TOTAL ITEMS</span></div><div class="dw-summary-cell"><strong id="dw-cats">–</strong><span>CATEGORIES</span></div><div class="dw-summary-cell"><strong id="dw-last">–</strong><span>LAST RUN</span></div></div>';
if(trends)trends.insertAdjacentElement('beforebegin',researchSummary);

async function dwExtras(){
 try{
   const b=await fetch('/api/work/brief').then(r=>r.json());
   const ideas=Array.isArray(b.ideas)?b.ideas:[];
   let txt='';
   if(ideas.length){
     txt=ideas.slice(0,3).map((x,i)=>(i+1)+'. '+(x.title||x.topic||x.name||'Idea')+(x.category?' · '+x.category:'')).join('\n');
   }else if(b.top_opportunity){
     txt=typeof b.top_opportunity==='string'?b.top_opportunity:JSON.stringify(b.top_opportunity);
   }else txt='No daily brief yet.';
   daily.querySelector('.dw-brief-text').textContent=txt;
 }catch(e){daily.querySelector('.dw-brief-text').textContent='Daily brief unavailable.'}
 try{
   const r=await fetch('/api/work/research').then(x=>x.json());
   document.getElementById('dw-total').textContent=r.total_items??'–';
   document.getElementById('dw-cats').textContent=r.categories?Object.keys(r.categories).length:'–';
   const lr=String(r.last_research||'–');document.getElementById('dw-last').textContent=lr==='–'?'–':lr.replace('T',' ').slice(5,16);
 }catch(e){}
}
dwExtras();

try{
 const recovery=document.getElementById('recovery');
 if(recovery){
   const conn=document.createElement('div');conn.className='box';conn.style.marginBottom='10px';
   conn.innerHTML='<div class="k">CONNECTION</div><input id="dw-runtime-url" placeholder="Runtime URL"><button id="dw-save-runtime">SAVE CONNECTION</button><button id="dw-copy-result">COPY RESULT FOR CHATGPT</button>';
   const h=recovery.querySelector('h3');if(h)h.insertAdjacentElement('afterend',conn);else recovery.prepend(conn);
   const ru=conn.querySelector('#dw-runtime-url');ru.value=DjaegerNative.getRuntimeUrl();
   conn.querySelector('#dw-save-runtime').onclick=()=>{const ok=DjaegerNative.setRuntimeUrl(ru.value.trim());if(ok){location.href=DjaegerNative.getRuntimeUrl()+'/'}else alert('URL harus dimulai http:// atau https://')};
   conn.querySelector('#dw-copy-result').onclick=async()=>{let text='';try{const d=document.getElementById('out');text=d?d.textContent:'';if(!text||text==='Ready.'){const j=await fetch('/api/work/diagnostics',{headers:{'X-Hermes-Token':(document.getElementById('token')||{}).value||''}}).then(r=>r.text());text=j}DjaegerNative.copyText(text||'No result.');}catch(e){DjaegerNative.copyText(String(e))}};
 }
 const token=document.getElementById('token');
 if(token){
   const saved=DjaegerNative.getAdminToken();if(saved)token.value=saved;
   token.addEventListener('input',()=>{try{DjaegerNative.setAdminToken(token.value)}catch(e){}});
 }
}catch(e){}

const groups={
 work:['system','today','dw-daily'],
 research:['dw-research-summary','trends'],
 planner:['planner','desk'],
 insights:['channel','knowledge'],
 system:['automation','recovery']
};
const labels=[
 ['work','WORK','<svg viewBox="0 0 24 24"><path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z"/></svg>'],
 ['research','RESEARCH','<svg viewBox="0 0 24 24"><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6A2 2 0 0 0 19 18l-5-9V3"/><path d="M8 15h8"/></svg>'],
 ['planner','PLANNER','<svg viewBox="0 0 24 24"><path d="M7 4h14M7 10h14M7 16h14M3 4h.01M3 10h.01M3 16h.01"/></svg>'],
 ['insights','INSIGHTS','<svg viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-7M22 19V2"/></svg>'],
 ['system','SYSTEM','<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.86 2.86-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.09A1.7 1.7 0 0 0 8 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.86-2.86.06-.06A1.7 1.7 0 0 0 3.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2V9.6h.09A1.7 1.7 0 0 0 3.6 8a1.7 1.7 0 0 0-.34-1.88L3.2 6.06 6.06 3.2l.06.06A1.7 1.7 0 0 0 8 3.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V2h4v.09A1.7 1.7 0 0 0 15 3.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.86 2.86-.06.06A1.7 1.7 0 0 0 19.4 8c.2.4.6.8 1 1 .3.2.7.3 1.1.3H22v4h-.09A1.7 1.7 0 0 0 20.4 15z"/></svg>']
];
const bottom=document.createElement('div');bottom.className='dw-bottom';
labels.forEach(([id,label,icon])=>{const b=document.createElement('button');b.className='dw-tab';b.dataset.tab=id;b.innerHTML=icon+label;b.onclick=()=>activate(id);bottom.appendChild(b)});
document.body.appendChild(bottom);

function activate(name){
 Object.keys(groups).forEach(g=>groups[g].forEach(id=>{const e=document.getElementById(id);if(e)e.style.display=(g===name?'block':'none')}));
 hero.style.display=name==='work'?'block':'none';
 bottom.querySelectorAll('.dw-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
 window.scrollTo(0,0);
 try{DjaegerNative.setLastTab(name)}catch(e){}
}
let initial='work';try{initial=DjaegerNative.getLastTab()||'work'}catch(e){}
if(!groups[initial])initial='work';activate(initial);

if(document.getElementById('system'))document.getElementById('system').querySelector('h3').textContent='Worker Status';
if(document.getElementById('today'))document.getElementById('today').querySelector('h3').textContent="Today’s Work";
if(document.getElementById('trends'))document.getElementById('trends').querySelector('h3').textContent='Research Intelligence';
if(document.getElementById('planner'))document.getElementById('planner').querySelector('h3').textContent='Content Planner';
if(document.getElementById('knowledge'))document.getElementById('knowledge').querySelector('h3').textContent='Insights & Memory';
if(document.getElementById('recovery'))document.getElementById('recovery').querySelector('h3').textContent='System & Recovery';

setInterval(dwExtras,30000);
})();