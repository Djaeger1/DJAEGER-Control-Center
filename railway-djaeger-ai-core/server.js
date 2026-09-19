'use strict';

const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 3000);
const TOKEN = String(process.env.DJAEGER_ACCESS_TOKEN || '');
const MAX_TRACES = Math.max(20, Math.min(1000, Number(process.env.MAX_TRACES || 200)));
const BODY_LIMIT = Math.max(4096, Math.min(262144, Number(process.env.BODY_LIMIT_BYTES || 65536)));
const RELEASE = 'DJAEGER_AUTOHEAL_V1';
const HARDWARE_AUTHORITY = 'NONE';
const BUILD_ID = String(process.env.RAILWAY_GIT_COMMIT_SHA || process.env.DJAEGER_BUILD_ID || 'unknown').slice(0, 64);
const UPDATE_ROOT = path.join(__dirname, 'updates', 'stable');

let lastTelemetry = null;
let lastKnownGood = null;
let lastAnomalies = [];
let lastUpdateAck = null;
const telemetryStats = {
  accepted: 0,
  anomalous: 0,
  first_received_at: null,
  last_received_at: null,
  baseline_updates: 0
};
const traces = [];

function nowIso() { return new Date().toISOString(); }
function traceId() { return 'DJG-' + Date.now().toString(36).toUpperCase() + '-' + crypto.randomBytes(3).toString('hex').toUpperCase(); }

function addTrace(type, data) {
  const item = { trace_id: traceId(), at: nowIso(), type, data };
  traces.unshift(item);
  if (traces.length > MAX_TRACES) traces.length = MAX_TRACES;
  return item;
}

function json(res, code, body) {
  const data = Buffer.from(JSON.stringify(body));
  res.writeHead(code, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': data.length,
    'cache-control': 'no-store'
  });
  res.end(data);
}

function authOk(req) {
  if (!TOKEN) return false;
  const h = String(req.headers.authorization || '');
  if (!h.startsWith('Bearer ')) return false;
  const got = Buffer.from(h.slice(7));
  const exp = Buffer.from(TOKEN);
  return got.length === exp.length && crypto.timingSafeEqual(got, exp);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    let rejected = false;

    req.on('data', c => {
      if (rejected) return;
      size += c.length;
      if (size > BODY_LIMIT) {
        rejected = true;
        reject(Object.assign(new Error('body_too_large'), { code: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });

    req.on('end', () => {
      if (rejected) return;
      try {
        const raw = Buffer.concat(chunks).toString('utf8');
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        reject(Object.assign(new Error('invalid_json'), { code: 400 }));
      }
    });

    req.on('error', reject);
  });
}

function normalizeNumber(name, value, min, max, options = {}) {
  if (value === undefined) return undefined;
  if (value === null) return null;

  if (typeof value === 'string') {
    const raw = value.trim();
    const sentinel = raw.toUpperCase();
    if (!raw || ['UNKNOWN','UNAVAILABLE','N/A','NA','NULL','NONE'].includes(sentinel)) return null;
    value = Number(raw);
  }

  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw Object.assign(new Error('invalid_' + name), { code: 422 });
  }

  if (options.zeroAsUnknown && value === 0) return null;
  return value;
}

function normalizeTelemetry(x) {
  if (!x || typeof x !== 'object' || Array.isArray(x)) {
    throw Object.assign(new Error('invalid_payload'), { code: 400 });
  }

  const out = { ...x };
  out.neurons_used = normalizeNumber('neurons_used', x.neurons_used, 0, 1000000000);
  out.neurons_limit = normalizeNumber('neurons_limit', x.neurons_limit, 0, 1000000000, { zeroAsUnknown: true });

  if (out.neurons_used !== undefined && out.neurons_limit !== undefined &&
      out.neurons_used !== null && out.neurons_limit !== null &&
      out.neurons_used > out.neurons_limit) {
    throw Object.assign(new Error('neurons_used_exceeds_limit'), { code: 422 });
  }

  for (const k of ['skin_temp_c','battery_temp_c','cpu_temp_c','gpu_temp_c']) {
    out[k] = normalizeNumber(k, x[k], -30, 150);
  }
  out.fps = normalizeNumber('fps', x.fps, 0, 1000);
  out.jank_pct = normalizeNumber('jank_pct', x.jank_pct, 0, 100);
  out.p95_ms = normalizeNumber('p95_ms', x.p95_ms, 0, 60000);
  out.p99_ms = normalizeNumber('p99_ms', x.p99_ms, 0, 60000);
  out.control_loop_age_s = normalizeNumber('control_loop_age_s', x.control_loop_age_s, 0, 86400);
  out.agent_execution_age_s = normalizeNumber('agent_execution_age_s', x.agent_execution_age_s, 0, 86400);
  out.gemini_status_age_s = normalizeNumber('gemini_status_age_s', x.gemini_status_age_s, 0, 604800);
  out.gemini_cooldown_until = normalizeNumber('gemini_cooldown_until', x.gemini_cooldown_until, 0, 4102444800);
  out.gemini_cooldown_remaining_s = normalizeNumber('gemini_cooldown_remaining_s', x.gemini_cooldown_remaining_s, 0, 86400);
  out.gemini_vault_count = normalizeNumber('gemini_vault_count', x.gemini_vault_count, 0, 32);
  out.gemini_ready_slots = normalizeNumber('gemini_ready_slots', x.gemini_ready_slots, 0, 32);
  out.gemini_cooling_slots = normalizeNumber('gemini_cooling_slots', x.gemini_cooling_slots, 0, 32);
  out.gemini_curl_rc = normalizeNumber('gemini_curl_rc', x.gemini_curl_rc, 0, 255);
  out.gemini_http_at = normalizeNumber('gemini_http_at', x.gemini_http_at, 0, 4102444800);

  return out;
}

function sanitizeTelemetry(x) {
  x = normalizeTelemetry(x);
  const allowed = [
    'schema','device_id','at','module_version','module_version_code',
    'workload_class','subject_package','profile','user_mode','window_mode',
    'skin_temp_c','battery_temp_c','cpu_temp_c','gpu_temp_c',
    'fps','jank_pct','p95_ms','p99_ms',
    'neurons_used','neurons_limit','neuron_tier','provider_quota_state','provider_quota_reason',
    'hermes_cloud_state','hermes_cloud_http','gemini_status','gemini_last_event_status','gemini_status_age_s','gemini_status_fresh','gemini_http_code','gemini_cooldown_until','gemini_cooldown_remaining_s','gemini_vault_count','gemini_ready_slots','gemini_cooling_slots','gemini_curl_rc','gemini_http_at','gemini_model',
    'control_loop_age_s','agent_execution_status','agent_execution_source','agent_execution_age_s',
    'remote_repair_state','remote_repair_seq','remote_repair_release','remote_repair_detail','source'
  ];
  const out = {};
  for (const k of allowed) {
    if (Object.prototype.hasOwnProperty.call(x, k)) {
      const v = x[k];
      if (['string','number','boolean'].includes(typeof v) || v === null) out[k] = v;
    }
  }
  out.server_received_at = nowIso();
  return out;
}

function safeTelemetrySummary(t) {
  if (!t) return null;
  return {
    schema: t.schema || null,
    module_version: t.module_version || null,
    workload_class: t.workload_class || null,
    profile: t.profile || null,
    skin_temp_c: t.skin_temp_c ?? null,
    battery_temp_c: t.battery_temp_c ?? null,
    cpu_temp_c: t.cpu_temp_c ?? null,
    gpu_temp_c: t.gpu_temp_c ?? null,
    fps: t.fps ?? null,
    jank_pct: t.jank_pct ?? null,
    p95_ms: t.p95_ms ?? null,
    p99_ms: t.p99_ms ?? null,
    neurons_used: t.neurons_used ?? null,
    neurons_limit: t.neurons_limit ?? null,
    neuron_tier: t.neuron_tier || null,
    provider_quota_state: t.provider_quota_state || null,
    provider_quota_reason: t.provider_quota_reason || null,
    hermes_cloud_state: t.hermes_cloud_state || null,
    hermes_cloud_http: t.hermes_cloud_http ?? null,
    gemini_status: t.gemini_status || null,
    gemini_last_event_status: t.gemini_last_event_status || null,
    gemini_status_age_s: t.gemini_status_age_s ?? null,
    gemini_status_fresh: t.gemini_status_fresh || null,
    gemini_http_code: t.gemini_http_code || null,
    gemini_cooldown_until: t.gemini_cooldown_until ?? null,
    gemini_cooldown_remaining_s: t.gemini_cooldown_remaining_s ?? null,
    gemini_vault_count: t.gemini_vault_count ?? null,
    gemini_ready_slots: t.gemini_ready_slots ?? null,
    gemini_cooling_slots: t.gemini_cooling_slots ?? null,
    gemini_curl_rc: t.gemini_curl_rc ?? null,
    gemini_http_at: t.gemini_http_at ?? null,
    gemini_model: t.gemini_model || null,
    control_loop_age_s: t.control_loop_age_s ?? null,
    agent_execution_status: t.agent_execution_status || null,
    agent_execution_source: t.agent_execution_source || null,
    agent_execution_age_s: t.agent_execution_age_s ?? null,
    remote_repair_state: t.remote_repair_state || null,
    remote_repair_seq: t.remote_repair_seq ?? null,
    remote_repair_release: t.remote_repair_release || null,
    remote_repair_detail: t.remote_repair_detail || null,
    agent_execution_status_trust: t.agent_execution_source ? 'SCOPED' : 'LEGACY_UNSCOPED',
    source: t.source || null,
    server_received_at: t.server_received_at
  };
}

function detectTelemetryAnomalies(t) {
  const anomalies = [];

  if (t.neurons_limit !== undefined && t.neurons_limit !== null &&
      t.neurons_used !== undefined && t.neurons_used !== null &&
      t.neurons_limit > 0 && t.neurons_used === 0) {
    const providerBlocked = String(t.provider_quota_state || '').toUpperCase() === 'EXHAUSTED';
    const cloudReady = ['READY','ONLINE'].includes(String(t.hermes_cloud_state || '').toUpperCase());
    if (providerBlocked) {
      anomalies.push({
        code: 'NEURONS_ZERO_PROVIDER_BLOCKED',
        severity: 'INFO',
        detail: 'no successful remote Cloud usage recorded while provider quota is exhausted'
      });
    } else if (cloudReady) {
      anomalies.push({
        code: 'NEURONS_ZERO_WITH_READY_CLOUD',
        severity: 'WARN',
        detail: 'Cloud is ready but device-side remote usage estimate remains zero'
      });
    } else {
      anomalies.push({
        code: 'NEURONS_ZERO_NO_REMOTE_SUCCESS',
        severity: 'INFO',
        detail: 'no successful remote Cloud usage has been recorded for the current accounting day'
      });
    }
  }

  if (t.control_loop_age_s !== undefined && t.control_loop_age_s !== null &&
      t.control_loop_age_s > 900) {
    anomalies.push({
      code: 'CONTROL_LOOP_STALE',
      severity: 'WARN',
      detail: 'control_loop_age_s exceeds 900 seconds'
    });
  }

  if (t.neurons_limit === null && t.neurons_used !== undefined) {
    anomalies.push({
      code: 'NEURON_LIMIT_UNKNOWN',
      severity: 'INFO',
      detail: 'neurons_limit is unavailable or sentinel'
    });
  }

  return anomalies;
}

function isKnownGoodTelemetry(t, anomalies) {
  if (!t || !t.server_received_at) return false;
  return !anomalies.some(a => a.severity === 'WARN' || a.severity === 'CRITICAL');
}

function observeTelemetry(t) {
  telemetryStats.accepted += 1;
  telemetryStats.first_received_at ||= t.server_received_at;
  telemetryStats.last_received_at = t.server_received_at;

  const anomalies = detectTelemetryAnomalies(t);
  lastAnomalies = anomalies;
  if (anomalies.some(a => a.severity === 'WARN' || a.severity === 'CRITICAL')) {
    telemetryStats.anomalous += 1;
  }

  const summary = safeTelemetrySummary(t);
  const knownGood = isKnownGoodTelemetry(t, anomalies);
  if (knownGood) {
    lastKnownGood = summary;
    telemetryStats.baseline_updates += 1;
  }

  const shouldLog = telemetryStats.accepted <= 5 ||
    telemetryStats.accepted % 10 === 0 ||
    anomalies.length > 0;

  if (shouldLog) {
    console.log(JSON.stringify({
      event: 'DJAEGER_TELEMETRY_SUMMARY',
      sample: telemetryStats.accepted,
      known_good: knownGood,
      anomalies,
      telemetry: summary,
      at: nowIso()
    }));
  }

  const actionableAnomalies = anomalies.filter(a => a.severity === 'WARN' || a.severity === 'CRITICAL');
  if (actionableAnomalies.length > 0) {
    console.warn(JSON.stringify({
      event: 'DJAEGER_TELEMETRY_ANOMALY',
      sample: telemetryStats.accepted,
      anomalies: actionableAnomalies,
      at: nowIso()
    }));
  }

  return { summary, anomalies, knownGood };
}

function serviceSelftest() {
  const checks = [
    { name: 'token_configured', ok: TOKEN.length >= 16 },
    { name: 'hardware_authority_none', ok: HARDWARE_AUTHORITY === 'NONE' },
    { name: 'trace_bounds', ok: MAX_TRACES >= 20 && MAX_TRACES <= 1000 },
    { name: 'body_limit_bounds', ok: BODY_LIMIT >= 4096 && BODY_LIMIT <= 262144 },
    { name: 'release_defined', ok: RELEASE === 'DJAEGER_AUTOHEAL_V1' },
    { name: 'update_manifest_present', ok: fs.existsSync(path.join(UPDATE_ROOT, 'manifest.txt')) }
  ];

  const failed = checks.filter(c => !c.ok).map(c => c.name);
  return {
    ok: failed.length === 0,
    release: RELEASE,
    build_id: BUILD_ID,
    checks,
    failed,
    telemetry_present: Boolean(lastTelemetry),
    at: nowIso()
  };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');

  if (req.method === 'GET' && url.pathname === '/health') {
    return json(res, 200, {
      ok: true,
      service: 'DJAEGER-AI-Core',
      schema: 'DJAEGER_RAILWAY_CORE_V1',
      release: RELEASE,
      build_id: BUILD_ID,
      mode: 'OBSERVE_DEBUG_ONLY',
      hardware_authority: HARDWARE_AUTHORITY,
      at: nowIso()
    });
  }

  if (req.method === 'GET' && (url.pathname === '/ready' || url.pathname === '/selftest')) {
    const result = serviceSelftest();
    return json(res, result.ok ? 200 : 503, result);
  }

  if (!authOk(req)) {
    addTrace('AUTH_REJECT', { method: req.method, path: url.pathname });
    return json(res, 401, { ok: false, error: 'unauthorized' });
  }

  try {
    if (req.method === 'GET' && url.pathname === '/v1/device/update/manifest.txt') {
      const manifestPath = path.join(UPDATE_ROOT, 'manifest.txt');
      if (!fs.existsSync(manifestPath)) return json(res, 404, { ok: false, error: 'update_manifest_missing' });
      const data = fs.readFileSync(manifestPath);
      res.writeHead(200, {
        'content-type': 'text/plain; charset=utf-8',
        'content-length': data.length,
        'cache-control': 'no-store'
      });
      return res.end(data);
    }

    if (req.method === 'GET' && url.pathname.startsWith('/v1/device/update/file/')) {
      const id = url.pathname.slice('/v1/device/update/file/'.length);
      if (!/^[A-Za-z0-9._-]+$/.test(id)) return json(res, 400, { ok: false, error: 'invalid_update_file_id' });
      const filePath = path.join(UPDATE_ROOT, 'files', id);
      if (!filePath.startsWith(path.join(UPDATE_ROOT, 'files') + path.sep) || !fs.existsSync(filePath)) {
        return json(res, 404, { ok: false, error: 'update_file_not_found' });
      }
      const data = fs.readFileSync(filePath);
      res.writeHead(200, {
        'content-type': 'application/octet-stream',
        'content-length': data.length,
        'cache-control': 'no-store'
      });
      return res.end(data);
    }

    if (req.method === 'POST' && url.pathname === '/v1/device/update/ack') {
      const body = await readBody(req);
      const ack = {
        device_id: String(body.device_id || 'UNKNOWN').slice(0, 96),
        seq: normalizeNumber('update_seq', body.seq ?? 0, 0, 1000000000),
        release: String(body.release || 'UNKNOWN').slice(0, 128),
        state: String(body.state || 'UNKNOWN').slice(0, 64),
        detail: String(body.detail || '').slice(0, 256),
        module_version_code: String(body.module_version_code || 'UNKNOWN').slice(0, 32),
        server_received_at: nowIso()
      };
      lastUpdateAck = ack;
      const tr = addTrace('UPDATE_ACK', ack);
      return json(res, 200, { ok: true, trace_id: tr.trace_id, ack });
    }

    if (req.method === 'GET' && url.pathname === '/v1/device/update/status') {
      return json(res, 200, {
        ok: true,
        channel: 'stable',
        manifest_present: fs.existsSync(path.join(UPDATE_ROOT, 'manifest.txt')),
        last_ack: lastUpdateAck,
        at: nowIso()
      });
    }

    if (req.method === 'POST' && url.pathname === '/v1/device/telemetry') {
      const body = await readBody(req);
      const t = sanitizeTelemetry(body);
      lastTelemetry = t;
      const observation = observeTelemetry(t);
      const tr = addTrace('TELEMETRY', {
        device_id: t.device_id || 'UNKNOWN',
        workload_class: t.workload_class || 'UNKNOWN',
        profile: t.profile || 'UNKNOWN',
        neurons_used: t.neurons_used ?? null,
        neurons_limit: t.neurons_limit ?? null,
        provider_quota_state: t.provider_quota_state || 'UNKNOWN',
        provider_quota_reason: t.provider_quota_reason || 'NONE',
        hermes_cloud_state: t.hermes_cloud_state || 'UNKNOWN'
      });
      return json(res, 200, {
        ok: true,
        trace_id: tr.trace_id,
        received_at: t.server_received_at,
        known_good: observation.knownGood,
        anomaly_count: observation.anomalies.length
      });
    }

    if (req.method === 'POST' && url.pathname === '/v1/device/event') {
      const body = await readBody(req);
      const safe = {
        device_id: String(body.device_id || 'UNKNOWN').slice(0, 96),
        event: String(body.event || 'UNKNOWN').slice(0, 96),
        component: String(body.component || 'UNKNOWN').slice(0, 96),
        status: String(body.status || 'UNKNOWN').slice(0, 96),
        detail: String(body.detail || '').slice(0, 512)
      };
      const tr = addTrace('DEVICE_EVENT', safe);
      return json(res, 200, { ok: true, trace_id: tr.trace_id });
    }

    if (req.method === 'GET' && url.pathname === '/v1/device/state') {
      return json(res, 200, {
        ok: true,
        service: 'DJAEGER-AI-Core',
        release: RELEASE,
        build_id: BUILD_ID,
        mode: 'OBSERVE_DEBUG_ONLY',
        hardware_authority: HARDWARE_AUTHORITY,
        state: lastTelemetry,
        trace_count: traces.length,
        at: nowIso()
      });
    }

    if (req.method === 'GET' && url.pathname === '/v1/device/observability') {
      const ageMs = lastTelemetry && lastTelemetry.server_received_at
        ? Math.max(0, Date.now() - Date.parse(lastTelemetry.server_received_at))
        : null;
      return json(res, 200, {
        ok: true,
        service: 'DJAEGER-AI-Core',
        release: RELEASE,
        build_id: BUILD_ID,
        telemetry_age_ms: ageMs,
        telemetry_stats: telemetryStats,
        current: safeTelemetrySummary(lastTelemetry),
        last_known_good: lastKnownGood,
        last_anomalies: lastAnomalies,
        at: nowIso()
      });
    }

    if (req.method === 'GET' && url.pathname === '/v1/debug/traces') {
      const limit = Math.max(1, Math.min(MAX_TRACES, Number(url.searchParams.get('limit') || 50)));
      return json(res, 200, { ok: true, traces: traces.slice(0, limit), at: nowIso() });
    }

    if (req.method === 'GET' && url.pathname === '/v1/config') {
      return json(res, 200, {
        ok: true,
        schema: 'DJAEGER_RAILWAY_CONFIG_V1',
        release: RELEASE,
        build_id: BUILD_ID,
        mode: 'OBSERVE_DEBUG_ONLY',
        telemetry_interval_game_sec: 15,
        telemetry_interval_app_sec: 30,
        telemetry_interval_idle_sec: 120,
        telemetry_interval_screen_off_sec: 300,
        remote_hardware_commands: false,
        remote_software_repairs: true,
        update_channel: 'stable',
        hardware_authority: HARDWARE_AUTHORITY
      });
    }

    return json(res, 404, { ok: false, error: 'not_found' });
  } catch (err) {
    const code = Number(err && err.code) || 500;
    const error = String(err && err.message || err).slice(0, 256);
    addTrace('SERVER_ERROR', { path: url.pathname, error });
    if (url.pathname === '/v1/device/telemetry' && code >= 400 && code < 500) {
      console.warn(JSON.stringify({ event: 'DJAEGER_TELEMETRY_REJECT', code, error, at: nowIso() }));
    }
    return json(res, code, { ok: false, error: code === 500 ? 'internal_error' : error });
  }
});

function fatal(kind, err) {
  console.error(JSON.stringify({
    event: kind,
    error: String(err && err.stack || err).slice(0, 2000),
    at: nowIso()
  }));
  process.exit(1);
}

process.on('uncaughtException', err => fatal('UNCAUGHT_EXCEPTION', err));
process.on('unhandledRejection', err => fatal('UNHANDLED_REJECTION', err));

server.listen(PORT, '0.0.0.0', () => {
  addTrace('BOOT', { port: PORT, schema: 'DJAEGER_RAILWAY_CORE_V1', release: RELEASE, build_id: BUILD_ID });
  console.log(JSON.stringify({ event: 'DJAEGER_AI_CORE_READY', release: RELEASE, build_id: BUILD_ID, port: PORT, at: nowIso() }));
});

process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
});
