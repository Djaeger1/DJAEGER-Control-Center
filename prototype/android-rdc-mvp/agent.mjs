import { createClient } from '@supabase/supabase-js';
import fs from 'node:fs';
import { spawn } from 'node:child_process';

const BASE = process.env.MCP_SERVER_URL || 'https://mcp.desktopcommander.app';
const SESSION_PATH = process.env.DJAEGER_RDC_SESSION || '/data/local/tmp/djaeger-rdc-auth/session.json';
const DEVICE_NAME = 'DJAEGER-Android';
const VERSION = '0.2.51';

const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

function resultText(text) {
  return { content: [{ type: 'text', text: String(text) }] };
}
function cleanText(s) {
  return String(s ?? '').replace(/\u0000/g, '');
}

async function runCommand(args) {
  const command = String(args?.command ?? '');
  const timeout = Math.max(1000, Math.min(Number(args?.timeout_ms ?? 10000), 120000));
  if (!command) throw new Error('command is required');
  const shell = args?.shell || '/system/bin/sh';

  return await new Promise((resolve, reject) => {
    const child = spawn(shell, ['-c', command], {
      env: { ...process.env, PATH: '/data/adb/ksu/bin:/system/bin:/system/xbin:/vendor/bin:/product/bin' },
      stdio: ['ignore', 'pipe', 'pipe']
    });
    let out = '', err = '', timedOut = false;
    const cap = 1024 * 1024;
    child.stdout.on('data', d => { if (out.length < cap) out += d.toString(); });
    child.stderr.on('data', d => { if (err.length < cap) err += d.toString(); });
    const timer = setTimeout(() => {
      timedOut = true;
      try { child.kill('SIGKILL'); } catch {}
    }, timeout);
    child.on('error', reject);
    child.on('close', code => {
      clearTimeout(timer);
      const text = [
        out.trimEnd(),
        err ? 'STDERR:\n' + err.trimEnd() : '',
        timedOut ? '[DJAEGER] timed out' : '[DJAEGER] exit=' + code
      ].filter(Boolean).join('\n');
      resolve(resultText(cleanText(text)));
    });
  });
}

async function executeTool(name, args) {
  if (name === 'ping') return resultText('pong ' + new Date().toISOString());
  if (name === 'start_process') return await runCommand(args);
  if (name === 'shutdown') {
    setTimeout(() => process.exit(0), 500);
    return resultText('Shutdown initialized at ' + new Date().toISOString());
  }
  throw new Error('DJAEGER Android MVP does not support tool yet: ' + name);
}

async function main() {
  log('DJAEGER_RDC_AGENT=START');
  if (!fs.existsSync(SESSION_PATH)) throw new Error('session not found: ' + SESSION_PATH);
  const saved = JSON.parse(fs.readFileSync(SESSION_PATH, 'utf8'));
  const deviceId = saved.deviceId;
  const savedSession = saved.session;
  if (!deviceId || !savedSession?.access_token || !savedSession?.refresh_token) {
    throw new Error('session.json incomplete');
  }

  const infoRes = await fetch(BASE + '/api/mcp-info');
  if (!infoRes.ok) throw new Error('mcp-info HTTP ' + infoRes.status);
  const info = await infoRes.json();

  let client;
  client = createClient(info.supabaseUrl, info.supabasePublishableKey, {
    auth: { autoRefreshToken: true, persistSession: false, detectSessionInUrl: false },
    realtime: {
      accessToken: async () => {
        try {
          const { data } = await client.auth.getSession();
          return data.session?.access_token || savedSession.access_token;
        } catch {
          return savedSession.access_token;
        }
      }
    }
  });

  const { data: authData, error: authError } = await client.auth.setSession({
    access_token: savedSession.access_token,
    refresh_token: savedSession.refresh_token
  });
  if (authError) throw authError;
  const user = authData.user;
  if (!user) throw new Error('authenticated user missing');

  const currentSession = authData.session;
  if (currentSession?.access_token) {
    client.realtime.setAuth(currentSession.access_token);
    saved.session = {
      access_token: currentSession.access_token,
      refresh_token: currentSession.refresh_token || savedSession.refresh_token
    };
    fs.writeFileSync(SESSION_PATH, JSON.stringify(saved, null, 2), { mode: 0o600 });
  }

  client.auth.onAuthStateChange((event, session) => {
    if (event === 'TOKEN_REFRESHED' && session?.access_token) {
      saved.session = {
        access_token: session.access_token,
        refresh_token: session.refresh_token || saved.session.refresh_token
      };
      try { fs.writeFileSync(SESSION_PATH, JSON.stringify(saved, null, 2), { mode: 0o600 }); } catch {}
      try { client.realtime.setAuth(session.access_token); } catch {}
      log('SESSION=REFRESHED');
    }
  });

  const { data: device, error: devErr } = await client
    .from('mcp_devices')
    .select('id,user_id')
    .eq('id', deviceId)
    .eq('user_id', user.id)
    .maybeSingle();
  if (devErr) throw devErr;
  if (!device) throw new Error('paired device row not found');

  await client.from('mcp_devices').update({
    status: 'offline',
    last_seen: new Date().toISOString(),
    device_name: DEVICE_NAME,
    capabilities: { app_version: VERSION }
  }).eq('id', deviceId);

  const seen = new Set();
  const channel = client.channel('user:' + user.id, {
    config: { private: true, presence: { key: deviceId, enabled: true } }
  });

  async function finish(id, status, result=null, errorMessage=null) {
    const update = { status, completed_at: new Date().toISOString() };
    if (result !== null) update.result = result;
    if (errorMessage !== null) update.error_message = cleanText(errorMessage);
    const { error } = await client.from('mcp_remote_calls').update(update).eq('id', id);
    if (error) log('RESULT_WRITE_ERROR', id, error.message);
  }

  async function handleDoorbell(payload) {
    const callId = payload?.call_id;
    if (!callId || payload?.device_id !== deviceId || seen.has(callId)) return;
    seen.add(callId);
    if (seen.size > 100) seen.delete(seen.values().next().value);

    const { data, error } = await client
      .from('mcp_remote_calls')
      .update({ status: 'executing' })
      .eq('id', callId)
      .eq('device_id', deviceId)
      .eq('status', 'pending')
      .select('*');
    if (error) {
      log('CLAIM_ERROR', callId, error.message);
      seen.delete(callId);
      return;
    }
    const row = data?.[0];
    if (!row) return;

    log('CALL', row.tool_name);
    try {
      let args = row.tool_args ?? {};
      if (typeof args === 'string') {
        try { args = JSON.parse(args); } catch {}
      }
      const result = await executeTool(row.tool_name, args);
      await finish(callId, 'completed', result, null);
      log('CALL_DONE', row.tool_name);
    } catch (e) {
      await finish(callId, 'failed', null, e?.message || String(e));
      log('CALL_FAIL', row.tool_name, e?.message || String(e));
    }
  }

  channel.on('broadcast', { event: 'new_call' }, ({ payload }) => {
    handleDoorbell(payload).catch(e => log('DOORBELL_ERROR', e?.message || String(e)));
  });

  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('channel subscribe timeout')), 30000);
    channel.subscribe(async (status, err) => {
      log('CHANNEL=' + status, err?.message || '');
      if (status === 'SUBSCRIBED') {
        clearTimeout(timer);
        try {
          const tracked = await channel.track({
            device_id: deviceId,
            device_name: DEVICE_NAME,
            app_version: VERSION,
            platform: 'android'
          });
          if (tracked !== 'ok') throw new Error('presence track=' + tracked);
          const { error: capErr } = await client.from('mcp_devices').update({
            capabilities: { app_version: VERSION, transport_broadcast_v1: true },
            status: 'online',
            last_seen: new Date().toISOString(),
            device_name: DEVICE_NAME
          }).eq('id', deviceId);
          if (capErr) throw capErr;
          log('DJAEGER_RDC_AGENT=READY');
          resolve();
        } catch (e) { reject(e); }
      } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
        clearTimeout(timer);
        reject(new Error('channel ' + status + ': ' + (err?.message || '')));
      }
    });
  });

  setInterval(async () => {
    try {
      await client.from('mcp_devices').update({
        status: 'online',
        last_seen: new Date().toISOString(),
        capabilities: { app_version: VERSION, transport_broadcast_v1: true }
      }).eq('id', deviceId);
    } catch {}
  }, 5 * 60 * 1000);

  process.on('SIGTERM', async () => {
    try { await client.from('mcp_devices').update({ status: 'offline' }).eq('id', deviceId); } catch {}
    process.exit(0);
  });

  await new Promise(() => {});
}

main().catch(async e => {
  console.error('DJAEGER_RDC_AGENT=FATAL');
  console.error(e?.stack || e);
  process.exit(1);
});
