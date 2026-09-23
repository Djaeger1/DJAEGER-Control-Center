import { createClient } from '@supabase/supabase-js';
import fs from 'node:fs';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';

const BASE = process.env.MCP_SERVER_URL || 'https://mcp.desktopcommander.app';
const SESSION_PATH = process.env.DJAEGER_RDC_SESSION || '/data/adb/modules/djaeger_remote_boot/state/session.json';
const STATUS_PATH = process.env.DJAEGER_STATUS_PATH || '/data/adb/modules/djaeger_remote_boot/state/status.env';
const DEVICE_NAME = process.env.DJAEGER_DEVICE_NAME || 'DJAEGER-Android';
const VERSION = '1.0.0-djaeger-android';
const CLIENT_ID = 'mcp-device';
const HEARTBEAT_MS = 5 * 60 * 1000;
const HEALTH_MS = 15 * 1000;
const CHANNEL_GRACE_MS = 45 * 1000;

const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let shuttingDown = false;

function setStatus(state, detail='') {
  try {
    fs.mkdirSync(new URL('.', 'file://' + STATUS_PATH).pathname, { recursive: true, mode: 0o700 });
  } catch {}
  try {
    fs.writeFileSync(STATUS_PATH,
      'STATE=' + state + '\n' +
      'DETAIL=' + String(detail).replace(/[\r\n]/g, ' ') + '\n' +
      'UPDATED_AT=' + new Date().toISOString() + '\n',
      { mode: 0o600 });
  } catch {}
}

function resultText(text) {
  return { content: [{ type: 'text', text: String(text) }] };
}

function cleanText(s) {
  return String(s ?? '').replace(/\u0000/g, '');
}

function loadSaved() {
  try {
    const x = JSON.parse(fs.readFileSync(SESSION_PATH, 'utf8'));
    if (x?.deviceId && x?.session?.access_token && x?.session?.refresh_token) return x;
  } catch {}
  return null;
}

function saveSaved(saved) {
  const dir = SESSION_PATH.slice(0, SESSION_PATH.lastIndexOf('/'));
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(SESSION_PATH, JSON.stringify(saved, null, 2), { mode: 0o600 });
}

async function deviceAuthorize() {
  setStatus('PAIRING_START', 'requesting device authorization');
  const verifier = crypto.randomBytes(32).toString('base64url');
  const challenge = crypto.createHash('sha256').update(verifier).digest('base64url');

  const start = await fetch(BASE + '/device/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: CLIENT_ID,
      scope: 'mcp:tools',
      device_name: DEVICE_NAME,
      device_type: 'mcp',
      code_challenge: challenge,
      code_challenge_method: 'S256'
    })
  });
  if (!start.ok) throw new Error('device/start HTTP ' + start.status + ': ' + (await start.text()).slice(0, 300));
  const auth = await start.json();

  log('PAIRING_URL=' + auth.verification_uri_complete);
  setStatus('PAIRING_REQUIRED', auth.verification_uri_complete);
  const opened = spawnSync('am', ['start', '-a', 'android.intent.action.VIEW', '-d', auth.verification_uri_complete], { stdio: 'ignore' });
  log('PAIRING_BROWSER=' + (opened.status === 0 ? 'OPENED' : 'FAILED'));

  const interval = Math.max(2, auth.interval || 5) * 1000;
  const deadline = Date.now() + auth.expires_in * 1000;
  while (Date.now() < deadline && !shuttingDown) {
    await sleep(interval);
    let response;
    try {
      response = await fetch(BASE + '/device/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_code: auth.device_code,
          client_id: CLIENT_ID,
          code_verifier: verifier
        })
      });
    } catch {
      continue;
    }
    let data = {};
    try { data = await response.json(); } catch {}
    if (response.ok && data.access_token && data.device_id) {
      const saved = {
        deviceId: data.device_id,
        session: { access_token: data.access_token, refresh_token: data.refresh_token || null }
      };
      if (!saved.session.refresh_token) throw new Error('authorization returned no refresh token');
      saveSaved(saved);
      setStatus('AUTHENTICATED', 'pairing complete');
      return saved;
    }
    if (data.error === 'authorization_pending' || data.error === 'slow_down') continue;
    throw new Error(data.error_description || data.error || 'authorization failed');
  }
  throw new Error('authorization timeout');
}

async function runCommand(args) {
  const command = String(args?.command ?? '');
  const timeout = Math.max(1000, Math.min(Number(args?.timeout_ms ?? 10000), 300000));
  if (!command) throw new Error('command is required');
  const shell = args?.shell || '/system/bin/sh';

  return await new Promise((resolve, reject) => {
    const child = spawn(shell, ['-c', command], {
      cwd: process.env.HOME || '/',
      env: {
        ...process.env,
        PATH: '/data/adb/ksu/bin:/data/adb/magisk:/system/bin:/system/xbin:/vendor/bin:/product/bin'
      },
      stdio: ['ignore', 'pipe', 'pipe']
    });
    let out = '', err = '', timedOut = false;
    const cap = 2 * 1024 * 1024;
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
  if (name === 'get_config') {
    return resultText(JSON.stringify({
      version: VERSION,
      defaultShell: '/system/bin/sh',
      allowedDirectories: [],
      systemInfo: { platform: process.platform, arch: process.arch, release: os.release(), hostname: os.hostname(), uid: process.getuid?.() }
    }, null, 2));
  }
  if (name === 'shutdown') {
    setTimeout(() => gracefulExit(0, 'remote shutdown'), 300);
    return resultText('Shutdown initialized at ' + new Date().toISOString());
  }
  throw new Error('DJAEGER Android bridge does not support tool yet: ' + name);
}

let client = null;
let channel = null;
let deviceId = null;
let lastJoinedAt = 0;

async function markOffline() {
  if (!client || !deviceId) return;
  try {
    await client.from('mcp_devices').update({
      status: 'offline',
      last_seen: new Date().toISOString(),
      capabilities: { app_version: VERSION }
    }).eq('id', deviceId);
  } catch {}
}

async function gracefulExit(code, why) {
  if (shuttingDown) return;
  shuttingDown = true;
  setStatus('OFFLINE', why);
  log('EXIT', why);
  await markOffline();
  try { if (channel && client) await client.removeChannel(channel); } catch {}
  setTimeout(() => process.exit(code), 100);
}

async function main() {
  setStatus('STARTING', 'initializing Android root bridge');
  log('DJAEGER_RDC_AGENT=START version=' + VERSION);

  const infoRes = await fetch(BASE + '/api/mcp-info');
  if (!infoRes.ok) throw new Error('mcp-info HTTP ' + infoRes.status);
  const info = await infoRes.json();

  let saved = loadSaved();
  if (!saved) saved = await deviceAuthorize();
  deviceId = saved.deviceId;

  client = createClient(info.supabaseUrl, info.supabasePublishableKey, {
    auth: { autoRefreshToken: true, persistSession: false, detectSessionInUrl: false },
    realtime: {
      accessToken: async () => {
        try {
          const { data } = await client.auth.getSession();
          return data.session?.access_token || saved.session.access_token;
        } catch {
          return saved.session.access_token;
        }
      }
    }
  });

  let authData, authError;
  ({ data: authData, error: authError } = await client.auth.setSession({
    access_token: saved.session.access_token,
    refresh_token: saved.session.refresh_token
  }));

  if (authError || !authData?.user) {
    log('SESSION_RESTORE=FAILED', authError?.message || 'no user');
    try { fs.rmSync(SESSION_PATH, { force: true }); } catch {}
    saved = await deviceAuthorize();
    deviceId = saved.deviceId;
    ({ data: authData, error: authError } = await client.auth.setSession({
      access_token: saved.session.access_token,
      refresh_token: saved.session.refresh_token
    }));
    if (authError || !authData?.user) throw authError || new Error('authenticated user missing');
  }

  const user = authData.user;
  const currentSession = authData.session;
  if (currentSession?.access_token) {
    saved.session = {
      access_token: currentSession.access_token,
      refresh_token: currentSession.refresh_token || saved.session.refresh_token
    };
    saveSaved(saved);
    client.realtime.setAuth(currentSession.access_token);
  }

  client.auth.onAuthStateChange((event, session) => {
    if (event === 'TOKEN_REFRESHED' && session?.access_token) {
      saved.session = {
        access_token: session.access_token,
        refresh_token: session.refresh_token || saved.session.refresh_token
      };
      try { saveSaved(saved); } catch {}
      try { client.realtime.setAuth(session.access_token); } catch {}
      log('SESSION=REFRESHED');
    } else if (event === 'SIGNED_OUT' && !shuttingDown) {
      gracefulExit(71, 'remote session signed out');
    }
  });

  const { data: device, error: devErr } = await client
    .from('mcp_devices')
    .select('id,user_id')
    .eq('id', deviceId)
    .eq('user_id', user.id)
    .maybeSingle();
  if (devErr) throw devErr;
  if (!device) {
    try { fs.rmSync(SESSION_PATH, { force: true }); } catch {}
    throw new Error('paired device row missing; restart will request fresh pairing');
  }

  await markOffline();

  const seen = new Set();
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

    const { data, error } = await client.from('mcp_remote_calls')
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
      if (typeof args === 'string') { try { args = JSON.parse(args); } catch {} }
      const result = await executeTool(row.tool_name, args);
      await finish(callId, 'completed', result, null);
      log('CALL_DONE', row.tool_name);
    } catch (e) {
      await finish(callId, 'failed', null, e?.message || String(e));
      log('CALL_FAIL', row.tool_name, e?.message || String(e));
    }
  }

  channel = client.channel('user:' + user.id, {
    config: { private: true, presence: { key: deviceId, enabled: true } }
  });

  channel.on('broadcast', { event: 'new_call' }, ({ payload }) => {
    handleDoorbell(payload).catch(e => log('DOORBELL_ERROR', e?.message || String(e)));
  });

  let firstReadyResolve, firstReadyReject;
  const firstReady = new Promise((resolve, reject) => {
    firstReadyResolve = resolve;
    firstReadyReject = reject;
  });
  let firstSettled = false;

  channel.subscribe(async (status, err) => {
    log('CHANNEL=' + status, err?.message || '');
    if (status === 'SUBSCRIBED') {
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
        lastJoinedAt = Date.now();
        setStatus('ONLINE', 'Remote Desktop Commander root bridge ready');
        log('DJAEGER_RDC_AGENT=READY');
        if (!firstSettled) {
          firstSettled = true;
          firstReadyResolve();
        }
      } catch (e) {
        if (!firstSettled) {
          firstSettled = true;
          firstReadyReject(e);
        } else {
          gracefulExit(72, 'presence/register failure: ' + (e?.message || String(e)));
        }
      }
    } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
      setStatus('CHANNEL_' + status, err?.message || status);
      if (!firstSettled) {
        firstSettled = true;
        firstReadyReject(new Error('channel ' + status + ': ' + (err?.message || '')));
      } else if (!shuttingDown) {
        setTimeout(() => gracefulExit(73, 'channel ' + status), 1500);
      }
    }
  });

  const readyTimeout = setTimeout(() => {
    if (!firstSettled) {
      firstSettled = true;
      firstReadyReject(new Error('first channel ready timeout'));
    }
  }, 45000);
  await firstReady;
  clearTimeout(readyTimeout);

  setInterval(async () => {
    if (shuttingDown) return;
    if (channel?.state !== 'joined') return;
    try {
      const { error } = await client.from('mcp_devices').update({
        status: 'online',
        last_seen: new Date().toISOString(),
        capabilities: { app_version: VERSION, transport_broadcast_v1: true }
      }).eq('id', deviceId);
      if (error) log('HEARTBEAT_ERROR', error.message);
    } catch (e) {
      log('HEARTBEAT_THROW', e?.message || String(e));
    }
  }, HEARTBEAT_MS);

  let unhealthySince = 0;
  setInterval(() => {
    if (shuttingDown) return;
    const joined = channel?.state === 'joined';
    if (joined) {
      unhealthySince = 0;
      lastJoinedAt = Date.now();
      return;
    }
    if (!unhealthySince) unhealthySince = Date.now();
    if (Date.now() - unhealthySince > CHANNEL_GRACE_MS) {
      gracefulExit(74, 'channel health watchdog restart');
    }
  }, HEALTH_MS);

  process.on('SIGTERM', () => gracefulExit(0, 'SIGTERM'));
  process.on('SIGINT', () => gracefulExit(0, 'SIGINT'));
  process.on('SIGHUP', () => gracefulExit(0, 'SIGHUP'));

  await new Promise(() => {});
}

main().catch(async e => {
  setStatus('FATAL', e?.message || String(e));
  console.error('DJAEGER_RDC_AGENT=FATAL');
  console.error(e?.stack || e);
  try { await markOffline(); } catch {}
  process.exit(1);
});
