'use strict';
const http=require('http'),crypto=require('crypto'),fs=require('fs'),path=require('path');
const PORT=Number(process.env.PORT||8080);
const TOKEN=String(process.env.DJAEGER_ACCESS_TOKEN||'');
const MAX=Math.max(20,Math.min(1000,Number(process.env.MAX_TRACES||240)));
const samples=[]; const proposals=[]; let lastDevice=null;
let telemetryAccepted=0,lastDeviceReceivedMs=0;
let updatePolls=0,lastUpdatePollMs=0,updateAcks=0,authRejects=0,lastAuthRejectMs=0;
const startedAtMs=Date.now();
const release='DJAEGER_AI_CORE_ADAPTIVE_TRANSPORT_RECOVERY1';
const UPDATE_ROOT=path.join(__dirname,'updates','stable');
const ADAPTIVE_UPDATE_ROOT=path.join(__dirname,'updates','adaptive');
let lastUpdateAck=null;
function now(){return new Date().toISOString();}
function send(res,code,obj){const raw=Buffer.from(JSON.stringify(obj));res.writeHead(code,{'content-type':'application/json; charset=utf-8','content-length':raw.length,'cache-control':'no-store'});res.end(raw);}
function sendRaw(res,code,data,type='application/octet-stream'){const raw=Buffer.isBuffer(data)?data:Buffer.from(String(data));res.writeHead(code,{'content-type':type,'content-length':raw.length,'cache-control':'no-store'});res.end(raw);}
function deviceHash(v){return v?crypto.createHash('sha256').update(String(v)).digest('hex').slice(0,12):null;}
function auth(req){if(TOKEN.length<16)return false;const h=String(req.headers.authorization||'');if(!h.startsWith('Bearer '))return false;const a=Buffer.from(h.slice(7)),b=Buffer.from(TOKEN);return a.length===b.length&&crypto.timingSafeEqual(a,b);}
function readJson(req){return new Promise((resolve,reject)=>{let n=0,cs=[];req.on('data',c=>{n+=c.length;if(n>131072){reject(Object.assign(new Error('too_large'),{code:413}));req.destroy();return;}cs.push(c);});req.on('end',()=>{try{resolve(JSON.parse(Buffer.concat(cs).toString('utf8')||'{}'));}catch{reject(Object.assign(new Error('bad_json'),{code:400}));}});req.on('error',reject);});}
function str(v,n=160){return v==null?null:String(v).slice(0,n);}
function num(v,min,max){if(v==null||v===''||String(v).toUpperCase()==='NA')return null;const x=Number(v);if(!Number.isFinite(x)||x<min||x>max)throw Object.assign(new Error('invalid_number'),{code:422});return x;}
function normalize(x){if(!x||typeof x!=='object'||Array.isArray(x))throw Object.assign(new Error('invalid_payload'),{code:400});return {schema:str(x.schema,64)||'DJAEGER_AI_TELEMETRY_V1',device_id:str(x.device_id,96),at:num(x.at,0,4102444800)||Math.floor(Date.now()/1000),module_version:str(x.module_version,96),module_version_code:str(x.module_version_code,32),workload_class:str(x.workload_class,32),window_mode:str(x.window_mode,32),package:str(x.package??x.subject_package,160),cpu_little_khz:num(x.cpu_little_khz,0,5000000),cpu_big_khz:num(x.cpu_big_khz,0,5000000),gpu_hz:num(x.gpu_hz,0,3000000000),skin_temp_c:num(x.skin_temp_c,-30,150),battery_temp_c:num(x.battery_temp_c,-30,100),cpu_temp_c:num(x.cpu_temp_c,-30,150),gpu_temp_c:num(x.gpu_temp_c,-30,150),power_mw:num(x.power_mw,0,50000),fps:num(x.fps,0,1000),jank_pct:num(x.jank_pct,0,100),source:str(x.source,64)||'LOCAL_OBSERVER',server_received_at:now()};}
function push(a,v){a.unshift(v);if(a.length>MAX)a.length=MAX;}
function updateRootForVc(vc){return vc==='202'||vc==='203'?ADAPTIVE_UPDATE_ROOT:UPDATE_ROOT;}
function renderManifest(rootDir){
  const mf=path.join(rootDir,'manifest.txt'); if(!fs.existsSync(mf))return null;
  const filesRoot=path.join(rootDir,'files')+path.sep;
  return fs.readFileSync(mf,'utf8').split(/\r?\n/).map(line=>{
    if(!line.startsWith('FILE|'))return line;
    const p=line.split('|'); if(p.length!==5||!/^[A-Za-z0-9._-]+$/.test(p[1]))return line;
    const fp=path.join(rootDir,'files',p[1]); if(!fp.startsWith(filesRoot)||!fs.existsSync(fp))return line;
    p[3]=crypto.createHash('sha256').update(fs.readFileSync(fp)).digest('hex'); return p.join('|');
  }).join('\n');
}
const server=http.createServer(async(req,res)=>{try{const u=new URL(req.url,'http://localhost');
 if(req.method==='GET'&&u.pathname==='/health'){const age=lastDeviceReceivedMs?Math.max(0,Math.floor((Date.now()-lastDeviceReceivedMs)/1000)):null;const pollAge=lastUpdatePollMs?Math.max(0,Math.floor((Date.now()-lastUpdatePollMs)/1000)):null;const authAge=lastAuthRejectMs?Math.max(0,Math.floor((Date.now()-lastAuthRejectMs)/1000)):null;return send(res,200,{ok:true,service:'DJAEGER_AI_CORE',release,hardware_authority:'NONE',foreign_runtime_dependencies:0,uptime_sec:Math.floor((Date.now()-startedAtMs)/1000),telemetry_seen:lastDeviceReceivedMs>0,telemetry_accepted:telemetryAccepted,last_telemetry_age_sec:age,last_device_id_hash:lastDevice?deviceHash(lastDevice.device_id):null,last_source:lastDevice?.source||null,last_module_version_code:lastDevice?.module_version_code||null,update_poll_seen:lastUpdatePollMs>0,update_poll_count:updatePolls,last_update_poll_age_sec:pollAge,update_ack_count:updateAcks,auth_reject_count:authRejects,last_auth_reject_age_sec:authAge});}
 if(req.method==='GET'&&u.pathname==='/ready')return send(res,200,{ok:true,ready:true,release,adaptive_update_channel:true,adaptive_target_vc:['202','203']});
 if(!auth(req)){authRejects++;lastAuthRejectMs=Date.now();console.warn(JSON.stringify({event:'DJAEGER_AUTH_REJECT',method:req.method,path:u.pathname,auth_reject_count:authRejects,at:now()}));return send(res,401,{ok:false,error:'unauthorized'});}
 if(req.method==='GET'&&u.pathname==='/v1/device/update/manifest.txt'){
   updatePolls++;lastUpdatePollMs=Date.now();
   const vc=str(u.searchParams.get('vc'),32),rootDir=updateRootForVc(vc),channel=rootDir===ADAPTIVE_UPDATE_ROOT?'adaptive':'stable';
   console.log(JSON.stringify({event:'DJAEGER_UPDATE_POLL',vc,channel,device_id_hash:deviceHash(u.searchParams.get('device_id')),update_poll_count:updatePolls,at:now()}));
   const raw=renderManifest(rootDir); if(raw==null)return send(res,404,{ok:false,error:'update_manifest_missing',channel});
   return sendRaw(res,200,raw,'text/plain; charset=utf-8');
 }
 if(req.method==='GET'&&u.pathname.startsWith('/v1/device/update/file/')){
   const id=u.pathname.slice('/v1/device/update/file/'.length);
   if(!/^[A-Za-z0-9._-]+$/.test(id))return send(res,400,{ok:false,error:'invalid_update_file_id'});
   let fp=null,channel=null;
   for(const [name,rootDir] of [['adaptive',ADAPTIVE_UPDATE_ROOT],['stable',UPDATE_ROOT]]){
     const root=path.join(rootDir,'files')+path.sep,candidate=path.join(rootDir,'files',id);
     if(candidate.startsWith(root)&&fs.existsSync(candidate)){fp=candidate;channel=name;break;}
   }
   console.log(JSON.stringify({event:'DJAEGER_UPDATE_FILE_FETCH',id:str(id,96),channel,at:now()}));
   if(!fp)return send(res,404,{ok:false,error:'update_file_not_found'});
   return sendRaw(res,200,fs.readFileSync(fp));
 }
 if(req.method==='POST'&&u.pathname==='/v1/device/update/ack'){
   updateAcks++;
   const x=await readJson(req); lastUpdateAck={device_id_hash:deviceHash(x.device_id),seq:num(x.seq,0,1000000000),release:str(x.release,128),state:str(x.state,64),detail:str(x.detail,256),module_version_code:str(x.module_version_code,32),server_received_at:now()};
   console.log(JSON.stringify({event:'DJAEGER_UPDATE_ACK',ack:lastUpdateAck,at:now()})); return send(res,200,{ok:true,accepted:true});
 }
 if(req.method==='GET'&&u.pathname==='/v1/device/update/status')return send(res,200,{ok:true,channels:{stable:fs.existsSync(path.join(UPDATE_ROOT,'manifest.txt')),adaptive:fs.existsSync(path.join(ADAPTIVE_UPDATE_ROOT,'manifest.txt'))},last_ack:lastUpdateAck,at:now()});
 if(req.method==='POST'&&u.pathname==='/v1/device/telemetry'){const t=normalize(await readJson(req));lastDevice=t;lastDeviceReceivedMs=Date.now();telemetryAccepted++;push(samples,t);console.log(JSON.stringify({event:'DJAEGER_AI_TELEMETRY_ACCEPTED',accepted:telemetryAccepted,device_id_hash:deviceHash(t.device_id),source:t.source,module_version_code:t.module_version_code,package:t.package,at:now()}));return send(res,200,{ok:true,accepted:true,hardware_action:false});}
 if(req.method==='POST'&&u.pathname==='/v1/agent/proposal'){const x=await readJson(req);const source=str(x.source,64);if(!['HERMES_LOCAL','HERMES_CLOUD','GEMINI','LOCAL_RULES'].includes(source))return send(res,422,{ok:false,error:'invalid_source'});const p={id:crypto.randomUUID(),at:now(),source,intent:str(x.intent,32),confidence:num(x.confidence,0,1),payload:x.payload&&typeof x.payload==='object'?x.payload:{},authority:'ADVISORY_ONLY'};push(proposals,p);return send(res,200,{ok:true,proposal:p,hardware_action:false});}
 if(req.method==='GET'&&u.pathname==='/v1/state')return send(res,200,{ok:true,release,last_device:lastDevice,sample_count:samples.length,last_proposal:proposals[0]||null,hardware_authority:'NONE'});
 if(req.method==='GET'&&u.pathname==='/v1/config')return send(res,200,{ok:true,release,cloud_hardware_authority:'NONE',device_executor_authority:'LOCAL_VALIDATED_ONLY',remote_hardware_commands:false,remote_software_updates:true,update_channel:'stable+adaptive'});
 return send(res,404,{ok:false,error:'not_found'});
}catch(e){return send(res,e.code||500,{ok:false,error:String(e.message||e)});}});
if(require.main===module){
  server.listen(PORT,()=>console.log(JSON.stringify({event:'DJAEGER_AI_CLEAN_CORE_READY',port:PORT,release,at:now()})));
  setInterval(()=>{
    const age=lastDeviceReceivedMs?Math.max(0,Math.floor((Date.now()-lastDeviceReceivedMs)/1000)):null;
    console.log(JSON.stringify({event:'DJAEGER_AI_TELEMETRY_HEARTBEAT',release,telemetry_seen:lastDeviceReceivedMs>0,telemetry_accepted:telemetryAccepted,last_telemetry_age_sec:age,last_device_id_hash:lastDevice?deviceHash(lastDevice.device_id):null,last_source:lastDevice?.source||null,last_module_version_code:lastDevice?.module_version_code||null,uptime_sec:Math.floor((Date.now()-startedAtMs)/1000),hardware_authority:'NONE',at:now()}));
  },60000).unref();
}
module.exports={server,normalize,release};
