'use strict';

const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 3000); // rollout marker: validated LIVEAUDIT gate repair
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
  out.predictive_policy_age_s = normalizeNumber('predictive_policy_age_s', x.predictive_policy_age_s, 0, 86400);
  out.root_policy_age_s = normalizeNumber('root_policy_age_s', x.root_policy_age_s, 0, 86400);
  out.audit_pass_count = normalizeNumber('audit_pass_count', x.audit_pass_count, 0, 10000);
  out.audit_warn_count = normalizeNumber('audit_warn_count', x.audit_warn_count, 0, 10000);
  out.audit_fail_count = normalizeNumber('audit_fail_count', x.audit_fail_count, 0, 10000);
  out.audit_at = normalizeNumber('audit_at', x.audit_at, 0, 4102444800);
  out.policy_until = normalizeNumber('policy_until', x.policy_until, 0, 4102444800);
  out.policy_remaining_s = normalizeNumber('policy_remaining_s', x.policy_remaining_s, -86400, 86400);

  return out;
}

function sanitizeTelemetry(x) {
  x = normalizeTelemetry(x);
  const allowed = [
    'schema','device_id','at','module_version','module_version_code',
    'workload_class','workload_context_age_s','game_session_active','workload_session_consistency','subject_package','profile','user_mode','window_mode',
    'skin_temp_c','battery_temp_c','cpu_temp_c','gpu_temp_c',
    'fps','jank_pct','p95_ms','p99_ms',
    'neurons_used','neurons_limit','neuron_tier','provider_quota_state','provider_quota_reason',
    'hermes_cloud_state','hermes_cloud_http','hermes_active_route','hermes_cloud_used','hermes_proposal_source','thought_source_current','thought_status_current','gemini_status','gemini_last_event_status','gemini_status_age_s','gemini_status_fresh','gemini_http_code','gemini_cooldown_until','gemini_cooldown_remaining_s','gemini_vault_count','gemini_ready_slots','gemini_cooling_slots','gemini_curl_rc','gemini_http_at','gemini_model','current_brain','brain_mode','final_source','cloud_in_control','cloud_plan_state','cloud_plan_reason','cloud_control_provider','cloud_plan_provider','policy_session_id','policy_game','policy_user_mode','policy_window_mode','policy_window_epoch','policy_until','policy_remaining_s','live_session_id','live_game','live_user_mode','live_window_mode','live_window_epoch','reasoning_status','reasoning_event_reason','reasoning_proposal_action','reasoning_proposal_profile','reasoning_confidence','predictive_policy_present','predictive_policy_age_s','root_policy_present','root_policy_age_s','audit_status','audit_pass_count','audit_warn_count','audit_fail_count','audit_at','audit_controller_live','audit_predictor_live','audit_supervisor_live','audit_workload_live','audit_app_control_live','audit_bridge_live','audit_updater_live','audit_knowledge_sync_live','audit_endpoint_https','audit_secret_permissions','audit_selftest_summary','audit_hash_controller','audit_hash_predictor','audit_hash_updater','audit_hash_bridge',
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
    workload_context_age_s: t.workload_context_age_s ?? null,
    game_session_active: t.game_session_active || null,
    workload_session_consistency: t.workload_session_consistency || null,
    subject_package: t.subject_package || null,
    window_mode: t.window_mode || null,
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
    hermes_active_route: t.hermes_active_route || null,
    hermes_cloud_used: t.hermes_cloud_used || null,
    hermes_proposal_source: t.hermes_proposal_source || null,
    thought_source_current: t.thought_source_current || null,
    thought_status_current: t.thought_status_current || null,
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
    current_brain: t.current_brain || null,
    brain_mode: t.brain_mode || null,
    final_source: t.final_source || null,
    cloud_in_control: t.cloud_in_control || null,
    cloud_plan_state: t.cloud_plan_state || null,
    cloud_plan_reason: t.cloud_plan_reason || null,
    cloud_control_provider: t.cloud_control_provider || null,
    cloud_plan_provider: t.cloud_plan_provider || null,
    policy_session_id: t.policy_session_id || null,
    policy_game: t.policy_game || null,
    policy_user_mode: t.policy_user_mode || null,
    policy_window_mode: t.policy_window_mode || null,
    policy_window_epoch: t.policy_window_epoch || null,
    policy_until: t.policy_until ?? null,
    policy_remaining_s: t.policy_remaining_s ?? null,
    live_session_id: t.live_session_id || null,
    live_game: t.live_game || null,
    live_user_mode: t.live_user_mode || null,
    live_window_mode: t.live_window_mode || null,
    live_window_epoch: t.live_window_epoch || null,
    reasoning_status: t.reasoning_status || null,
    reasoning_event_reason: t.reasoning_event_reason || null,
    reasoning_proposal_action: t.reasoning_proposal_action || null,
    reasoning_proposal_profile: t.reasoning_proposal_profile || null,
    reasoning_confidence: t.reasoning_confidence || null,
    predictive_policy_present: t.predictive_policy_present || null,
    predictive_policy_age_s: t.predictive_policy_age_s ?? null,
    root_policy_present: t.root_policy_present || null,
    root_policy_age_s: t.root_policy_age_s ?? null,
    audit_status: t.audit_status || null,
    audit_pass_count: t.audit_pass_count ?? null,
    audit_warn_count: t.audit_warn_count ?? null,
    audit_fail_count: t.audit_fail_count ?? null,
    audit_at: t.audit_at ?? null,
    audit_controller_live: t.audit_controller_live || null,
    audit_predictor_live: t.audit_predictor_live || null,
    audit_supervisor_live: t.audit_supervisor_live || null,
    audit_workload_live: t.audit_workload_live || null,
    audit_app_control_live: t.audit_app_control_live || null,
    audit_bridge_live: t.audit_bridge_live || null,
    audit_updater_live: t.audit_updater_live || null,
    audit_knowledge_sync_live: t.audit_knowledge_sync_live || null,
    audit_endpoint_https: t.audit_endpoint_https || null,
    audit_secret_permissions: t.audit_secret_permissions || null,
    audit_selftest_summary: t.audit_selftest_summary || null,
    audit_hash_controller: t.audit_hash_controller || null,
    audit_hash_predictor: t.audit_hash_predictor || null,
    audit_hash_updater: t.audit_hash_updater || null,
    audit_hash_bridge: t.audit_hash_bridge || null,
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
    t.workload_class === 'GAME' ||
    t.game_session_active === 'YES' ||
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
      // Recompute every payload hash from the exact bytes we are about to serve.
      // This prevents a stale manifest hash from pinning a previous repair payload.
      const rawManifest = fs.readFileSync(manifestPath, 'utf8');
      const manifest = rawManifest.split(/\\r?\\n/).map(line => {
        if (!line.startsWith('FILE|')) return line;
        const parts = line.split('|');
        if (parts.length !== 5 || !/^[A-Za-z0-9._-]+$/.test(parts[1])) return line;
        const payloadPath = path.join(UPDATE_ROOT, 'files', parts[1]);
        if (!payloadPath.startsWith(path.join(UPDATE_ROOT, 'files') + path.sep) || !fs.existsSync(payloadPath)) return line;
        parts[3] = crypto.createHash('sha256').update(fs.readFileSync(payloadPath)).digest('hex');
        return parts.join('|');
      }).join('\\n');
      const data = Buffer.from(manifest);
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
      console.log(JSON.stringify({ level: 'info', event: 'DJAEGER_UPDATE_ACK', ack, at: nowIso() }));
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
