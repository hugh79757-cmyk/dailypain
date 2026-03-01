export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"GET,POST,OPTIONS","Access-Control-Allow-Headers":"Content-Type"};
    if (request.method === "OPTIONS") return new Response(null, {headers:cors});
    if (url.pathname === "/auth/callback") return new Response("OK", {headers:{"Content-Type":"text/plain"}});
    if (url.pathname === "/deauth") return new Response(JSON.stringify({success:true}), {headers:{"Content-Type":"application/json",...cors}});
    if (url.pathname === "/data-deletion") return new Response(JSON.stringify({url:url.href,confirmation_code:"dp_"+Date.now()}), {headers:{"Content-Type":"application/json",...cors}});
    if (url.pathname === "/api/pain" && request.method === "POST") {
      try {
        const b = await request.json();
        await env.DB.prepare("INSERT INTO pain_points (date,keyword,category,title,description,pain_summary,pain_score,solution_hint,source_url,source) VALUES (?,?,?,?,?,?,?,?,?,?)").bind(b.date,b.keyword,b.category,b.title,b.description,b.pain_summary,b.pain_score||0,b.solution_hint,b.source_url,b.source||"naver_kin").run();
        return new Response(JSON.stringify({ok:true}), {headers:{"Content-Type":"application/json",...cors}});
      } catch(e) { return new Response(JSON.stringify({error:e.message}), {status:500,headers:{"Content-Type":"application/json",...cors}}); }
    }
    if (url.pathname === "/api/pains") {
      const date = url.searchParams.get("date") || new Date().toISOString().split("T")[0];
      const cat = url.searchParams.get("category") || "";
      let q = "SELECT * FROM pain_points WHERE date = ?"; const p = [date];
      if (cat) { q += " AND category = ?"; p.push(cat); }
      q += " ORDER BY pain_score DESC LIMIT 50";
      const {results} = await env.DB.prepare(q).bind(...p).all();
      return new Response(JSON.stringify(results), {headers:{"Content-Type":"application/json",...cors}});
    }
    if (url.pathname === "/api/dates") {
      const {results} = await env.DB.prepare("SELECT DISTINCT date FROM pain_points ORDER BY date DESC LIMIT 30").all();
      return new Response(JSON.stringify(results.map(r=>r.date)), {headers:{"Content-Type":"application/json",...cors}});
    }
    if (url.pathname === "/api/star" && request.method === "POST") {
      const {id} = await request.json();
      await env.DB.prepare("UPDATE pain_points SET starred = CASE WHEN starred=1 THEN 0 ELSE 1 END WHERE id=?").bind(id).run();
      return new Response(JSON.stringify({ok:true}), {headers:{"Content-Type":"application/json",...cors}});
    }
    if (url.pathname === "/api/starred") {
      const {results} = await env.DB.prepare("SELECT * FROM pain_points WHERE starred=1 ORDER BY pain_score DESC").all();
      return new Response(JSON.stringify(results), {headers:{"Content-Type":"application/json",...cors}});
    }
    return new Response(getHTML(), {headers:{"Content-Type":"text/html; charset=utf-8"}});
  }
};
function getHTML() {
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>DailyPain</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}.header{background:#1e293b;padding:20px;text-align:center;border-bottom:1px solid #334155}.header h1{font-size:24px;color:#f97316}.header p{color:#94a3b8;font-size:14px;margin-top:4px}.controls{display:flex;gap:10px;padding:16px;flex-wrap:wrap;justify-content:center;background:#1e293b}.controls select,.controls button{padding:8px 16px;border-radius:8px;border:1px solid #475569;background:#334155;color:#e2e8f0;font-size:14px;cursor:pointer}.controls button.active{background:#f97316;color:#fff;border-color:#f97316}.container{max-width:800px;margin:0 auto;padding:16px}.card{background:#1e293b;border-radius:12px;padding:16px;margin-bottom:12px;border:1px solid #334155;transition:border-color .2s}.card:hover{border-color:#f97316}.card-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.badge{background:#f97316;color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600}.score{color:#fbbf24;font-weight:700;font-size:18px}.card h3{font-size:16px;color:#f1f5f9;margin-bottom:6px}.pain{color:#fb923c;font-size:14px;margin-bottom:4px}.hint{color:#67e8f9;font-size:13px;margin-bottom:8px}.card-bottom{display:flex;justify-content:space-between;align-items:center}.link{color:#818cf8;text-decoration:none;font-size:12px}.star-btn{background:none;border:none;font-size:20px;cursor:pointer}.stats{text-align:center;padding:8px;color:#64748b;font-size:13px}.empty{text-align:center;padding:60px 20px;color:#64748b}</style></head><body><div class="header"><h1>DailyPain</h1><p>한국 사업자의 매일 페인포인트</p></div><div class="controls"><select id="dateSelect"></select><select id="catSelect"><option value="">전체 카테고리</option></select><button id="starredBtn" onclick="loadStarred()">⭐ 저장됨</button></div><div id="stats" class="stats"></div><div id="container" class="container"></div><script>const BASE='';let currentMode='daily';async function loadDates(){const res=await fetch(BASE+'/api/dates');const dates=await res.json();const sel=document.getElementById('dateSelect');sel.innerHTML='';if(!dates.length){sel.innerHTML='<option>데이터 없음</option>';return}dates.forEach(d=>{const o=document.createElement('option');o.value=d;o.textContent=d;sel.appendChild(o)});sel.onchange=()=>loadPains();loadPains()}async function loadPains(){currentMode='daily';document.getElementById('starredBtn').classList.remove('active');const date=document.getElementById('dateSelect').value;const cat=document.getElementById('catSelect').value;let u=BASE+'/api/pains?date='+date;if(cat)u+='&category='+cat;const res=await fetch(u);const data=await res.json();renderCards(data);updateCats(data);document.getElementById('stats').textContent=date+' — '+data.length+'개 페인포인트'}async function loadStarred(){currentMode='starred';document.getElementById('starredBtn').classList.add('active');const res=await fetch(BASE+'/api/starred');const data=await res.json();renderCards(data);document.getElementById('stats').textContent='저장된 페인포인트 '+data.length+'개'}function updateCats(data){const cats=[...new Set(data.map(d=>d.category).filter(Boolean))];const sel=document.getElementById('catSelect');const cur=sel.value;sel.innerHTML='<option value="">전체 카테고리</option>';cats.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;sel.appendChild(o)});sel.value=cur;sel.onchange=()=>loadPains()}function renderCards(data){const c=document.getElementById('container');if(!data.length){c.innerHTML='<div class="empty">데이터가 없습니다</div>';return}c.innerHTML=data.map(d=>'<div class="card"><div class="card-top"><span class="badge">'+(d.category||'')+'</span><span class="score">'+(d.pain_score||0)+'점</span></div><h3>'+(d.title||'').substring(0,60)+'</h3><div class="pain">🔥 '+(d.pain_summary||'')+'</div><div class="hint">💡 '+(d.solution_hint||'')+'</div><div class="card-bottom"><a class="link" href="'+(d.source_url||'')+'" target="_blank">원문 보기 →</a><button class="star-btn" onclick="toggleStar('+d.id+',this)">'+(d.starred?'⭐':'☆')+'</button></div></div>').join('')}async function toggleStar(id,btn){await fetch(BASE+'/api/star',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});btn.textContent=btn.textContent==='☆'?'⭐':'☆'}loadDates()</script></body></html>`;
}
