import http from "node:http";
import https from "node:https";

const PORT = Number(process.env.PORT || 3000);
const TOPIC = process.env.NTFY_TOPIC || "";
const ACCESS_PATH = process.env.ACCESS_PATH || "";
const NTFY = process.env.NTFY_BASE || "https://ntfy.sh";
let directSnapshot = null;
let directReceivedAt = 0;

function send(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    "content-type":"application/json; charset=utf-8",
    "cache-control":"no-store"
  });
  res.end(body);
}

function safeSnapshot(x={}) {
  return {
    service:"HERMES_WORK",
    release:x.release ?? null,
    tether_state:x.tether_state ?? null,
    temperature_c:x.temperature_c ?? null,
    mem_available_mb:x.mem_available_mb ?? null,
    worker_state:x.worker_state ?? null,
    safe_mode:x.safe_mode ?? null,
    research_total:x.research_total ?? null,
    last_research:x.last_research ?? null,
    research_engine:x.research_engine ?? null,
    daily_brief_state:x.daily_brief_state ?? null,
    ideas_ready:x.ideas_ready ?? null,
    top_opportunity:x.top_opportunity ?? null,
    opportunity_engine:x.opportunity_engine ?? null,
    planner_state:x.planner_state ?? null,
    planner_queue:x.planner_queue ?? null,
    next_for_script:x.next_for_script ?? null,
    planner_engine:x.planner_engine ?? null,
    script_prep_state:x.script_prep_state ?? null,
    script_prep_ready:x.script_prep_ready ?? null,
    script_topic:x.script_topic ?? null,
    script_prep_engine:x.script_prep_engine ?? null,
    script_state:x.script_state ?? null,
    scripts_ready:x.scripts_ready ?? null,
    final_script_topic:x.final_script_topic ?? null,
    script_engine:x.script_engine ?? null,
    production_pack_state:x.production_pack_state ?? null,
    production_ready:x.production_ready ?? null,
    production_topic:x.production_topic ?? null,
    production_engine:x.production_engine ?? null,
    handoff_state:x.handoff_state ?? null,
    handoff_queue:x.handoff_queue ?? null,
    next_handoff_job:x.next_handoff_job ?? null,
    handoff_engine:x.handoff_engine ?? null,
    feedback_state:x.feedback_state ?? null,
    performance_records:x.performance_records ?? null,
    strong_signal:x.strong_signal ?? null,
    weak_signal:x.weak_signal ?? null,
    feedback_engine:x.feedback_engine ?? null,
    auto_update_state:x.auto_update_state ?? null,
    auto_update_last_check:x.auto_update_last_check ?? null,
    bridge_agent:x.bridge_agent ?? null,
    ai_used:x.ai_used ?? false,
    neurons_used:x.neurons_used ?? 0,
    sent_at:x.sent_at ?? null
  };
}

function ntfyViaHttps(url) {
  return new Promise((resolve,reject)=>{
    const req=https.get(url,{family:4,headers:{"user-agent":"HERMES-WORK-ChatGPT-Relay/1.1"}},res=>{
      let data="";res.setEncoding("utf8");
      res.on("data",chunk=>{if(data.length<2_000_000)data+=chunk});
      res.on("end",()=>res.statusCode>=200&&res.statusCode<300?resolve(data):reject(new Error("NTFY_HTTP_"+res.statusCode)));
    });
    req.setTimeout(15000,()=>req.destroy(new Error("NTFY_TIMEOUT")));
    req.on("error",reject);
  });
}
function parseNtfy(text) {
  const lines = text.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
  let latest = null;
  for (const line of lines) {
    try {
      const ev = JSON.parse(line);
      if (!ev || ev.event !== "message" || typeof ev.message !== "string") continue;
      const snap = JSON.parse(ev.message);
      if (snap && typeof snap === "object") latest = snap;
    } catch {}
  }
  return latest;
}
async function latestSnapshot() {
  if (directSnapshot && Date.now()-directReceivedAt < 20*60*1000) return directSnapshot;
  if (!TOPIC) throw new Error("NTFY_TOPIC_NOT_CONFIGURED");
  const url = `${NTFY}/${encodeURIComponent(TOPIC)}/json?poll=1&since=30m`;
  let firstErr = null;
  try {
    const r = await fetch(url, {headers:{"user-agent":"HERMES-WORK-ChatGPT-Relay/1.1"},signal:AbortSignal.timeout(15000)});
    if (!r.ok) throw new Error(`NTFY_HTTP_${r.status}`);
    const latest=parseNtfy(await r.text());
    if (latest) return latest;
    firstErr=new Error("NO_RECENT_SNAPSHOT");
  } catch(e) { firstErr=e; }
  try {
    const latest=parseNtfy(await ntfyViaHttps(url));
    if (latest) return latest;
    throw new Error("NO_RECENT_SNAPSHOT");
  } catch(e) {
    const a=String(firstErr?.cause?.code||firstErr?.code||firstErr?.message||firstErr||"unknown");
    const b=String(e?.cause?.code||e?.code||e?.message||e||"unknown");
    throw new Error("NTFY_UNAVAILABLE primary="+a+" fallback="+b);
  }
}

const server = http.createServer(async (req,res)=>{
  const u = new URL(req.url, "http://localhost");
  if (u.pathname === "/health") {
    return send(res,200,{ok:true,service:"HERMES_WORK_CHATGPT_RELAY",direct_fresh:!!(directSnapshot&&Date.now()-directReceivedAt<20*60*1000)});
  }
  if (u.pathname === "/ingest" && req.method === "POST") {
    if (!TOPIC || req.headers["x-hermes-topic"] !== TOPIC) return send(res,401,{ok:false,error:"unauthorized"});
    let body="";let tooLarge=false;
    req.setEncoding("utf8");
    req.on("data",chunk=>{body+=chunk;if(body.length>262144){tooLarge=true;req.destroy()}});
    req.on("end",()=>{
      if(tooLarge)return send(res,413,{ok:false,error:"payload_too_large"});
      try{
        const raw=JSON.parse(body);
        directSnapshot=safeSnapshot(raw);directReceivedAt=Date.now();
        return send(res,200,{ok:true,source:"direct-data-only",received_at:new Date(directReceivedAt).toISOString()});
      }catch(e){return send(res,400,{ok:false,error:"invalid_json"})}
    });
    return;
  }
  if (!ACCESS_PATH || u.pathname !== "/" + ACCESS_PATH) {
    return send(res,404,{error:"not_found"});
  }
  try {
    const snap = await latestSnapshot();
    return send(res,200,{ok:true,source:(directSnapshot&&Date.now()-directReceivedAt<20*60*1000)?"direct-data-only":"ntfy-data-only",snapshot:safeSnapshot(snap)});
  } catch (e) {
    return send(res,503,{ok:false,error:String(e?.message || e)});
  }
});

server.listen(PORT,"0.0.0.0",()=>console.log(`relay listening on ${PORT}`));


async function logLatestSnapshot() {
  try {
    const snap = safeSnapshot(await latestSnapshot());
    console.log("HERMES_SNAPSHOT " + JSON.stringify(snap));
  } catch (e) {
    console.log("HERMES_SNAPSHOT_ERROR " + String(e?.message || e));
  }
}

setTimeout(logLatestSnapshot, 3000);
setInterval(logLatestSnapshot, 60000);
