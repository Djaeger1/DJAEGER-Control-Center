'use strict';
const http=require('http'),crypto=require('crypto');
const PORT=Number(process.env.PORT||8080);
const TOKEN=String(process.env.DJAEGER_ACCESS_TOKEN||'');
const MAX=Math.max(20,Math.min(1000,Number(process.env.MAX_TRACES||240)));
const samples=[]; const proposals=[]; let lastDevice=null;
let telemetryAccepted=0,lastDeviceReceivedMs=0;
const startedAtMs=Date.now();
const release='DJAEGER_AI_CORE_DIAG_V2';
function now(){return new Date().toISOString();}
function send(res,code,obj){const raw=Buffer.from(JSON.stringify(obj));res.writeHead(code,{'content-type':'application/json; charset=utf-8','content-length':raw.length,'cache-control':'no-store'});res.end(raw);}
function auth(req){if(TOKEN.length<16)return false;const h=String(req.headers.authorization||'');if(!h.startsWith('Bearer '))return false;const a=Buffer.from(h.slice(7)),b=Buffer.from(TOKEN);return a.length===b.length&&crypto.timingSafeEqual(a,b);}
function readJson(req){return new Promise((resolve,reject)=>{let n=0,cs=[];req.on('data',c=>{n+=c.length;if(n>131072){reject(Object.assign(new Error('too_large'),{code:413}));req.destroy();return;}cs.push(c);});req.on('end',()=>{try{resolve(JSON.parse(Buffer.concat(cs).toString('utf8')||'{}'));}catch{reject(Object.assign(new Error('bad_json'),{code:400}));}});req.on('error',reject);});}
function str(v,n=160){return v==null?null:String(v).slice(0,n);}
function num(v,min,max){if(v==null||v===''||String(v).toUpperCase()==='NA')return null;const x=Number(v);if(!Number.isFinite(x)||x<min||x>max)throw Object.assign(new Error('invalid_number'),{code:422});return x;}
function normalize(x){if(!x||typeof x!=='object'||Array.isArray(x))throw Object.assign(new Error('invalid_payload'),{code:400});return {schema:str(x.schema,64)||'DJAEGER_AI_TELEMETRY_V1',device_id:str(x.device_id,96),at:num(x.at,0,4102444800)||Math.floor(Date.now()/1000),package:str(x.package,160),cpu_little_khz:num(x.cpu_little_khz,0,5000000),cpu_big_khz:num(x.cpu_big_khz,0,5000000),gpu_hz:num(x.gpu_hz,0,3000000000),skin_temp_c:num(x.skin_temp_c,-30,150),battery_temp_c:num(x.battery_temp_c,-30,100),cpu_temp_c:num(x.cpu_temp_c,-30,150),gpu_temp_c:num(x.gpu_temp_c,-30,150),power_mw:num(x.power_mw,0,50000),fps:num(x.fps,0,1000),jank_pct:num(x.jank_pct,0,100),source:str(x.source,64)||'LOCAL_OBSERVER',server_received_at:now()};}
function push(a,v){a.unshift(v);if(a.length>MAX)a.length=MAX;}
const server=http.createServer(async(req,res)=>{try{const u=new URL(req.url,'http://localhost');
 if(req.method==='GET'&&u.pathname==='/health'){const age=lastDeviceReceivedMs?Math.max(0,Math.floor((Date.now()-lastDeviceReceivedMs)/1000)):null;return send(res,200,{ok:true,service:'DJAEGER_AI_CORE',release,hardware_authority:'NONE',foreign_runtime_dependencies:0,uptime_sec:Math.floor((Date.now()-startedAtMs)/1000),telemetry_seen:lastDeviceReceivedMs>0,telemetry_accepted:telemetryAccepted,last_telemetry_age_sec:age});}
 if(req.method==='GET'&&u.pathname==='/ready')return send(res,200,{ok:true,ready:true,release});
 if(!auth(req))return send(res,401,{ok:false,error:'unauthorized'});
 if(req.method==='POST'&&u.pathname==='/v1/device/telemetry'){const t=normalize(await readJson(req));lastDevice=t;lastDeviceReceivedMs=Date.now();telemetryAccepted++;push(samples,t);return send(res,200,{ok:true,accepted:true,hardware_action:false});}
 if(req.method==='POST'&&u.pathname==='/v1/agent/proposal'){const x=await readJson(req);const source=str(x.source,64);if(!['HERMES_LOCAL','HERMES_CLOUD','GEMINI','LOCAL_RULES'].includes(source))return send(res,422,{ok:false,error:'invalid_source'});const p={id:crypto.randomUUID(),at:now(),source,intent:str(x.intent,32),confidence:num(x.confidence,0,1),payload:x.payload&&typeof x.payload==='object'?x.payload:{},authority:'ADVISORY_ONLY'};push(proposals,p);return send(res,200,{ok:true,proposal:p,hardware_action:false});}
 if(req.method==='GET'&&u.pathname==='/v1/state')return send(res,200,{ok:true,release,last_device:lastDevice,sample_count:samples.length,last_proposal:proposals[0]||null,hardware_authority:'NONE'});
 if(req.method==='GET'&&u.pathname==='/v1/config')return send(res,200,{ok:true,release,cloud_hardware_authority:'NONE',device_executor_authority:'LOCAL_VALIDATED_ONLY',remote_hardware_commands:false,remote_software_updates:false});
 return send(res,404,{ok:false,error:'not_found'});
}catch(e){return send(res,e.code||500,{ok:false,error:String(e.message||e)});}});
if(require.main===module){
  server.listen(PORT,()=>console.log(JSON.stringify({event:'DJAEGER_AI_CLEAN_CORE_READY',port:PORT,release,at:now()})));
  setInterval(()=>{
    const age=lastDeviceReceivedMs?Math.max(0,Math.floor((Date.now()-lastDeviceReceivedMs)/1000)):null;
    console.log(JSON.stringify({event:'DJAEGER_AI_TELEMETRY_HEARTBEAT',release,telemetry_seen:lastDeviceReceivedMs>0,telemetry_accepted:telemetryAccepted,last_telemetry_age_sec:age,uptime_sec:Math.floor((Date.now()-startedAtMs)/1000),hardware_authority:'NONE',at:now()}));
  },60000).unref();
}
module.exports={server,normalize,release};
