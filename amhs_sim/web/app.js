const canvas = document.getElementById('fab-canvas');
const ctx = canvas.getContext('2d');
let state = null;

function resize() { const dpr = devicePixelRatio || 1; canvas.width = canvas.clientWidth*dpr; canvas.height = canvas.clientHeight*dpr; ctx.setTransform(dpr,0,0,dpr,0,0); }
addEventListener('resize', resize); resize();

async function command(action, extra={}) { await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})}); }
document.getElementById('pause').onclick=()=>command(state?.paused?'resume':'pause');
document.getElementById('reset').onclick=()=>command('reset');
document.querySelectorAll('[data-speed]').forEach(b=>b.onclick=()=>command('speed',{speed:Number(b.dataset.speed)}));

function draw() {
  if (!state) return;
  const w=canvas.clientWidth,h=canvas.clientHeight, pad=65, railY=135, max=Math.max(...state.stations.map(s=>s.position_m));
  ctx.clearRect(0,0,w,h); ctx.strokeStyle='#315249'; ctx.lineWidth=8; ctx.beginPath();ctx.moveTo(pad,railY);ctx.lineTo(w-pad,railY);ctx.stroke();
  ctx.strokeStyle='#142c26';ctx.lineWidth=2;
  for(let i=0;i<22;i++){let x=pad+i*(w-2*pad)/21;ctx.beginPath();ctx.moveTo(x,railY-12);ctx.lineTo(x+7,railY+12);ctx.stroke();}
  state.stations.forEach((s,i)=>{const x=pad+s.position_m/max*(w-2*pad);ctx.strokeStyle='#4f756a';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,railY);ctx.lineTo(x,245);ctx.stroke();ctx.fillStyle='#0b1715';ctx.fillRect(x-44,245,88,38);ctx.strokeRect(x-44,245,88,38);ctx.fillStyle='#7fffc4';ctx.font='10px ui-monospace';ctx.textAlign='center';ctx.fillText(s.name,x,269);ctx.fillStyle='#78958b';ctx.fillText(`${s.position_m.toFixed(1)} m`,x,300);});
  state.vehicles.forEach((v,i)=>{const x=pad+v.position_m/max*(w-2*pad), y=railY-18-i*47;ctx.shadowColor=v.fault?'#ff5f6d':'#27d7ae';ctx.shadowBlur=15;ctx.fillStyle=v.fault?'#ff5f6d':'#27d7ae';ctx.fillRect(x-25,y-11,50,22);ctx.shadowBlur=0;ctx.fillStyle='#07100f';ctx.font='bold 10px ui-monospace';ctx.fillText(v.id,x,y+4);if(v.carrying){ctx.fillStyle='#ffb84d';ctx.beginPath();ctx.moveTo(x,y+16);ctx.lineTo(x+9,y+26);ctx.lineTo(x,y+36);ctx.lineTo(x-9,y+26);ctx.closePath();ctx.fill();}});
}

function updateUI(){
  document.getElementById('sim-time').textContent=`${state.time_s.toFixed(2)} s`;document.getElementById('completed').textContent=`${state.completed} FOUPs`;document.getElementById('queued').textContent=`${state.queue.length} lots`;
  document.getElementById('system-state').textContent=state.paused?'PAUSED':state.vehicles.some(v=>v.fault)?'INTERLOCK':'RUNNING';document.getElementById('pause').textContent=state.paused?'Resume system':'Pause system';
  document.getElementById('vehicles').innerHTML=state.vehicles.map(v=>`<div class="vehicle"><b>${v.id}</b><span class="state ${v.fault?'fault':''}">${v.state}</span><div><small>${v.position_m.toFixed(2)} m · ${v.velocity_mps.toFixed(2)} m/s</small><div class="bar"><i style="width:${Math.min(100,Math.abs(v.velocity_mps)/2*100)}%"></i></div></div><span>${v.foup_id||'NO LOAD'}</span><button class="estop" data-id="${v.id}" data-fault="${!!v.fault}">${v.fault?'RESET':'E-STOP'}</button></div>`).join('');
  document.querySelectorAll('.estop').forEach(b=>b.onclick=()=>command(b.dataset.fault==='true'?'clear_fault':'fault',{vehicle_id:b.dataset.id}));draw();
}

async function poll(){try{const r=await fetch('/api/state');state=await r.json();document.getElementById('connection').textContent='LIVE PLANT DATA';updateUI();}catch(e){document.getElementById('connection').textContent='CONNECTION LOST';}setTimeout(poll,100);}poll();
