const downloads = [
  { name:"ubuntu-24.04-desktop-amd64.iso", size:"5.2 GB", pct:64, state:"dl",  speed:"4.2 MB/s", eta:"8m 12s", cat:"cp-prog" , catName:"Program" },
  { name:"Interstellar.2014.2160p.mkv",    size:"28.4 GB",pct:31, state:"dl",  speed:"6.1 MB/s", eta:"1h 14m", cat:"cp-video", catName:"Video"   },
  { name:"Pink Floyd - Wish You Were.flac", size:"412 MB", pct:87, state:"dl",  speed:"2.8 MB/s", eta:"45s",    cat:"cp-audio", catName:"Audio"   },
  { name:"Adobe Premiere Pro 2024.zip",    size:"3.8 GB", pct:45, state:"ps",  speed:"—",         eta:"—",      cat:"cp-arc",   catName:"Archive" },
  { name:"deep_learning_book.pdf",         size:"18 MB",  pct:100,state:"ok",  speed:"—",         eta:"done",   cat:"cp-doc",   catName:"Document"},
  { name:"Blender-4.1-linux-x64.tar.xz",  size:"221 MB", pct:100,state:"ok",  speed:"—",         eta:"done",   cat:"cp-prog",  catName:"Program" },
  { name:"bohemian_rhapsody_4k.mp4",       size:"7.1 GB", pct:22, state:"q",   speed:"—",         eta:"—",      cat:"cp-video", catName:"Video"   },
  { name:"python-3.12.3-amd64.exe",        size:"25 MB",  pct:0,  state:"er",  speed:"!",         eta:"error",  cat:"cp-prog",  catName:"Program" },
  { name:"Dune.Part.Two.2024.mkv",         size:"22.8 GB",pct:100,state:"ok",  speed:"—",         eta:"done",   cat:"cp-video", catName:"Video"   },
  { name:"nodejs-v22.0.0-win-x64.zip",     size:"29 MB",  pct:100,state:"ok",  speed:"—",         eta:"done",   cat:"cp-arc",   catName:"Archive" },
  { name:"arch-linux-2024.iso",            size:"874 MB", pct:55, state:"ps",  speed:"—",         eta:"—",      cat:"cp-prog",  catName:"Program" },
  { name:"lofi_study_mix_8hr.mp3",         size:"890 MB", pct:100,state:"ok",  speed:"—",         eta:"done",   cat:"cp-audio", catName:"Audio"   },
];

const stateMap = {
  dl: ['si-dl','▶'], ok: ['si-ok','✓'], ps: ['si-ps','⏸'], er: ['si-er','!'], q: ['si-q','…']
};

function renderTable() {
  const tbody = document.getElementById('dlTable');
  tbody.innerHTML = downloads.map((d,i) => {
    const [cls, icon] = stateMap[d.state];
    const fillCls = d.state==='ok'?'complete':d.state==='er'?'error':'';
    const errColor = d.state==='er' ? 'color:var(--org)' : '';
    return `<tr${i===0?' class="selected"':''}  onclick="this.closest('tbody').querySelectorAll('tr').forEach(r=>r.className='');this.className='selected'">
      <td><div class="status-icon ${cls}">${icon}</div></td>
      <td><div class="fname" title="${d.name}">${d.name}</div></td>
      <td class="fsize">${d.size}</td>
      <td>
        <div class="prog-wrap">
          <div class="prog-bar"><div class="prog-fill ${fillCls}" style="width:${d.pct}%"></div></div>
          <div class="prog-pct" style="${errColor}">${d.state==='er'?'Error':d.pct+'%'}</div>
        </div>
      </td>
      <td class="speed-cell${d.speed==='—'?' none':''}">${d.speed}</td>
      <td class="eta-cell">${d.eta}</td>
      <td><span class="cat-pill ${d.cat}">${d.catName}</span></td>
      <td><div class="row-actions">
        ${d.state==='dl'?'<button class="row-btn">⏸</button>':''}
        ${d.state==='ps'?'<button class="row-btn">▶</button>':''}
        <button class="row-btn">📁</button>
        <button class="row-btn">✕</button>
      </div></td>
    </tr>`;
  }).join('');
}

// Speed Graph
const canvas = document.getElementById('speedCanvas');
function resizeCanvas() {
  canvas.width = canvas.offsetWidth * (window.devicePixelRatio||1);
  canvas.height = canvas.offsetHeight * (window.devicePixelRatio||1);
}
const graphData = Array.from({length:60}, (_,i) => {
  const t = i/59;
  return 2 + Math.sin(t*8)*1.5 + Math.cos(t*13+1)*1 + Math.random()*0.8;
});
function drawGraph() {
  resizeCanvas();
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const dpr = window.devicePixelRatio||1;
  ctx.clearRect(0,0,W,H);
  const max = Math.max(...graphData,1);
  const pts = graphData.map((v,i)=>[i/(graphData.length-1)*W, H - v/max*H*0.9 - H*0.05]);

  // Fill
  const grad = ctx.createLinearGradient(0,0,0,H);
  grad.addColorStop(0, 'rgba(88,166,255,0.25)');
  grad.addColorStop(1, 'rgba(88,166,255,0)');
  ctx.beginPath();
  ctx.moveTo(0,H);
  pts.forEach(([x,y])=>ctx.lineTo(x,y));
  ctx.lineTo(W,H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  pts.forEach(([x,y],i)=>i===0?ctx.moveTo(x,y):ctx.lineTo(x,y));
  ctx.strokeStyle = '#58a6ff';
  ctx.lineWidth = 1.5 * dpr;
  ctx.lineJoin = 'round';
  ctx.stroke();

  // Grid lines
  ctx.strokeStyle = 'rgba(48,54,61,0.6)';
  ctx.lineWidth = 0.5 * dpr;
  [0.25,0.5,0.75].forEach(f => {
    const y = H - f*H*0.9 - H*0.05;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
  });
}

// Live updates
let tick = 0;
function animate() {
  tick++;
  // Shift graph
  graphData.shift();
  graphData.push(2 + Math.sin(tick*0.15)*2 + Math.cos(tick*0.23+1)*1.2 + Math.random()*0.8);
  drawGraph();

  // Update speed
  const spd = (graphData[graphData.length-1]).toFixed(1);
  document.getElementById('liveSpeed').textContent = spd;
  document.getElementById('sbSpeed').textContent = spd + ' MB/s';

  // Update time
  const now = new Date();
  document.getElementById('sbTime').textContent = now.toTimeString().slice(0,8);

  // Cycle active download progress
  [0,1,2].forEach(i => {
    if(downloads[i].state==='dl') {
      downloads[i].pct = Math.min(100, downloads[i].pct + (Math.random()*0.4));
      if(downloads[i].pct >= 100) { downloads[i].state='ok'; downloads[i].speed='—'; downloads[i].eta='done'; }
    }
  });
  renderTable();
}

renderTable();
drawGraph();
setInterval(animate, 800);