'use strict';
process.env.DJAEGER_ACCESS_TOKEN='cleanroom-selftest-token-123456789';
const core=require('./server'),server=core.server,TOKEN=process.env.DJAEGER_ACCESS_TOKEN;
function ok(v,m){if(!v)throw new Error(m);}
async function req(port,path,opt={}){const r=await fetch('http://127.0.0.1:'+port+path,opt);const ct=r.headers.get('content-type')||'';return {status:r.status,body:ct.includes('application/json')?await r.json():await r.text()};}
(async()=>{server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const port=server.address().port;try{
 let r=await req(port,'/health');ok(r.status===200&&r.body.hardware_authority==='NONE','health');
 r=await req(port,'/v1/state');ok(r.status===401,'auth');
 const h={'content-type':'application/json','authorization':'Bearer '+TOKEN};
 r=await req(port,'/v1/device/telemetry',{method:'POST',headers:h,body:JSON.stringify({device_id:'TEST',at:1,package:'sts.al',cpu_little_khz:1000000,cpu_big_khz:1800000,gpu_hz:600000000,skin_temp_c:39,battery_temp_c:37,cpu_temp_c:55,gpu_temp_c:52,power_mw:2200,fps:60,jank_pct:1.2})});ok(r.status===200&&r.body.hardware_action===false,'telemetry');
 r=await req(port,'/health');ok(r.body.telemetry_seen===true&&r.body.telemetry_accepted===1&&r.body.last_telemetry_age_sec!==null,'telemetry diagnostics');
 r=await req(port,'/v1/device/update/manifest.txt',{headers:h});ok(r.status===200&&typeof r.body==='string'&&r.body.includes("SEQ='64'"),'manifest');
 r=await req(port,'/v1/agent/proposal',{method:'POST',headers:h,body:JSON.stringify({source:'GEMINI',intent:'ADJUST',confidence:.9,payload:{gpu_max_hz:650000000}})});ok(r.status===200&&r.body.proposal.authority==='ADVISORY_ONLY','proposal');
 r=await req(port,'/v1/config',{headers:h});ok(r.body.remote_hardware_commands===false&&r.body.remote_software_updates===true&&r.body.device_executor_authority==='LOCAL_VALIDATED_ONLY','authority');
 console.log('PASS|DJAEGER_AI_CLEAN_CORE_SELFTEST');
}finally{server.close();}})().catch(e=>{console.error('FAIL|'+e.message);process.exit(1);});
