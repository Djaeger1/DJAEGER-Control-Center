'use strict';

const http = require('http');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 3000);
const TOKEN = String(process.env.DJAEGER_ACCESS_TOKEN || '');
const MAX_TRACES = Math.max(20, Math.min(1000, Number(process.env.MAX_TRACES || 200)));
const BODY_LIMIT = Math.max(4096, Math.min(262144, Number(process.env.BODY_LIMIT_BYTES || 65536)));
const RELEASE = 'DJAEGER_AUTOHEAL_V1';
const HARDWARE_AUTHORITY = 'NONE';
const BUILD_ID = String(process.env.RAILWAY_GIT_COMMIT_SHA || process.env.DJAEGER_BUILD_ID || 'unknown').slice(0, 64);

let lastTelemetry = null;
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

function assertFiniteRange(name, value, min, max) {
  if (value === undefined || value === null) return;
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw Object.assign(new Error('invalid_' + name), { code: 422 });
  }
}

function validateTelemetry(x) {
  if (!x || typeof x !== 'object' || Array.isArray(x)) {
    throw Object.assign(new Error('invalid_payload'), { code: 400 });
  }

  assertFiniteRange('neurons_used', x.neurons_used, 0, 1000000000);
  assertFiniteRange('neurons_limit', x.neurons_limit, 1, 1000000000);
  if (x.neurons_used !== undefined && x.neurons_limit !== undefined &&
      x.neurons_used !== null && x.neurons_limit !== null &&
      x.neurons_used > x.neurons_limit) {
    throw Object.assign(new Error('neurons_used_exceeds_limit'), { code: 422 });
  }

  for (const k of ['skin_temp_c','battery_temp_c','cpu_temp_c','gpu_temp_c']) {
    assertFiniteRange(k, x[k], -30, 150);
  }
  assertFiniteRange('fps', x.fps, 0, 1000);
  assertFiniteRange('jank_pct', x.jank_pct, 0, 100);
  assertFiniteRange('p95_ms', x.p95_ms, 0, 60000);
  assertFiniteRange('p99_ms', x.p99_ms, 0, 60000);
  assertFiniteRange('control_loop_age_s', x.control_loop_age_s, 0, 86400);
}

function sanitizeTelemetry(x) {
  validateTelemetry(x);
  const allowed = [
    'schema','device_id','at','module_version','module_version_code',
    'workload_class','subject_package','profile','user_mode','window_mode',
    'skin_temp_c','battery_temp_c','cpu_temp_c','gpu_temp_c',
    'fps','jank_pct','p95_ms','p99_ms',
    'neurons_used','neurons_limit','neuron_tier','provider_quota_state','provider_quota_reason',
    'hermes_cloud_state','hermes_cloud_http','gemini_status',
    'control_loop_age_s','agent_execution_status','source'
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

function serviceSelftest() {
  const checks = [
    { name: 'token_configured', ok: TOKEN.length >= 16 },
    { name: 'hardware_authority_none', ok: HARDWARE_AUTHORITY === 'NONE' },
    { name: 'trace_bounds', ok: MAX_TRACES >= 20 && MAX_TRACES <= 1000 },
    { name: 'body_limit_bounds', ok: BODY_LIMIT >= 4096 && BODY_LIMIT <= 262144 },
    { name: 'release_defined', ok: RELEASE === 'DJAEGER_AUTOHEAL_V1' }
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
    if (req.method === 'POST' && url.pathname === '/v1/device/telemetry') {
      const body = await readBody(req);
      const t = sanitizeTelemetry(body);
      lastTelemetry = t;
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
      return json(res, 200, { ok: true, trace_id: tr.trace_id, received_at: t.server_received_at });
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
        hardware_authority: HARDWARE_AUTHORITY
      });
    }

    return json(res, 404, { ok: false, error: 'not_found' });
  } catch (err) {
    const code = Number(err && err.code) || 500;
    addTrace('SERVER_ERROR', { path: url.pathname, error: String(err && err.message || err).slice(0, 256) });
    return json(res, code, { ok: false, error: code === 500 ? 'internal_error' : String(err.message || 'bad_request') });
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
