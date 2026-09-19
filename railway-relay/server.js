import http from "node:http";

const PORT = Number(process.env.PORT || 3000);
const TOPIC = process.env.NTFY_TOPIC || "";
const ACCESS_PATH = process.env.ACCESS_PATH || "";
const NTFY = process.env.NTFY_BASE || "https://ntfy.sh";

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
    bridge_agent:x.bridge_agent ?? null,
    ai_used:x.ai_used ?? false,
    neurons_used:x.neurons_used ?? 0,
    sent_at:x.sent_at ?? null
  };
}

async function latestSnapshot() {
  if (!TOPIC) throw new Error("NTFY_TOPIC_NOT_CONFIGURED");
  const url = `${NTFY}/${encodeURIComponent(TOPIC)}/json?poll=1&since=30m`;
  const r = await fetch(url, {headers:{"user-agent":"HERMES-WORK-ChatGPT-Relay/1.0"}});
  if (!r.ok) throw new Error(`NTFY_HTTP_${r.status}`);
  const t = await r.text();
  const lines = t.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
  let latest = null;
  for (const line of lines) {
    try {
      const ev = JSON.parse(line);
      if (!ev || ev.event !== "message" || typeof ev.message !== "string") continue;
      const snap = JSON.parse(ev.message);
      if (snap && typeof snap === "object") latest = snap;
    } catch {}
  }
  if (!latest) throw new Error("NO_RECENT_SNAPSHOT");
  return latest;
}

const server = http.createServer(async (req,res)=>{
  const u = new URL(req.url, "http://localhost");
  if (u.pathname === "/health") {
    return send(res,200,{ok:true,service:"HERMES_WORK_CHATGPT_RELAY"});
  }
  if (!ACCESS_PATH || u.pathname !== "/" + ACCESS_PATH) {
    return send(res,404,{error:"not_found"});
  }
  try {
    const snap = await latestSnapshot();
    return send(res,200,{ok:true,source:"ntfy-data-only",snapshot:safeSnapshot(snap)});
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
