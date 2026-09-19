'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '../..');
const CORE = path.join(ROOT, 'railway-djaeger-ai-core');
const FILES = {
  server: path.join(CORE, 'server.js'),
  selftest: path.join(CORE, 'selftest.js'),
  pkg: path.join(CORE, 'package.json'),
  docker: path.join(CORE, 'Dockerfile')
};

const LEGACY_VALIDATION = `function assertFiniteRange(name, value, min, max) {
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
`;

const NORMALIZED_VALIDATION = `function normalizeNumber(name, value, min, max, options = {}) {
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

  return out;
}

function sanitizeTelemetry(x) {
  x = normalizeTelemetry(x);
`;

const LEGACY_CATCH = `  } catch (err) {
    const code = Number(err && err.code) || 500;
    addTrace('SERVER_ERROR', { path: url.pathname, error: String(err && err.message || err).slice(0, 256) });
    return json(res, code, { ok: false, error: code === 500 ? 'internal_error' : String(err.message || 'bad_request') });
  }
`;

const DIAGNOSTIC_CATCH = `  } catch (err) {
    const code = Number(err && err.code) || 500;
    const error = String(err && err.message || err).slice(0, 256);
    addTrace('SERVER_ERROR', { path: url.pathname, error });
    if (url.pathname === '/v1/device/telemetry' && code >= 400 && code < 500) {
      console.warn(JSON.stringify({ event: 'DJAEGER_TELEMETRY_REJECT', code, error, at: nowIso() }));
    }
    return json(res, code, { ok: false, error: code === 500 ? 'internal_error' : error });
  }
`;

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function write(file, value) {
  fs.writeFileSync(file, value);
}

function existsAll() {
  return Object.entries(FILES).filter(([, p]) => !fs.existsSync(p)).map(([k]) => k);
}

function runTest() {
  const r = spawnSync('npm', ['test'], {
    cwd: CORE,
    encoding: 'utf8',
    timeout: 30000,
    env: { ...process.env, CI: '1' }
  });
  return {
    ok: r.status === 0,
    status: r.status,
    stdout: String(r.stdout || '').slice(-5000),
    stderr: String(r.stderr || '').slice(-5000)
  };
}

function diagnose() {
  const result = {
    version: 1,
    scope: 'DJAEGER_AI_ONLY',
    at: new Date().toISOString(),
    status: 'HEALTHY',
    patchable: [],
    blocked: [],
    checks: [],
    test: null
  };

  const missing = existsAll();
  if (missing.length) {
    result.blocked.push('missing_required_files:' + missing.join(','));
    result.status = 'UNPATCHABLE';
    return result;
  }

  const server = read(FILES.server);
  const docker = read(FILES.docker);
  let pkg;
  try {
    pkg = JSON.parse(read(FILES.pkg));
  } catch {
    result.blocked.push('invalid_package_json');
    result.status = 'UNPATCHABLE';
    return result;
  }

  const blocked = [
    ['hardware_authority_changed', !server.includes("const HARDWARE_AUTHORITY = 'NONE'")],
    ['work_scope_contamination', /hermes-work|railway-relay|HERMES-WORK-Relay/i.test(server)],
    ['direct_hardware_write_detected', /\/sys\/|setprop|su -c|magisk|cpu[0-9]+\/cpufreq/i.test(server)]
  ];
  for (const [name, bad] of blocked) {
    result.checks.push({ name, ok: !bad });
    if (bad) result.blocked.push(name);
  }

  const patchable = [
    ['package_test_gate_missing', !(pkg.scripts && typeof pkg.scripts.test === 'string' && pkg.scripts.test.includes('selftest.js'))],
    ['docker_selftest_copy_missing', !docker.includes('COPY selftest.js ./')],
    ['docker_test_gate_missing', !docker.includes('RUN npm test')],
    ['telemetry_numeric_string_compat_missing', !server.includes('function normalizeTelemetry(') && server.includes(LEGACY_VALIDATION)],
    ['telemetry_reject_diagnostic_missing', !server.includes('DJAEGER_TELEMETRY_REJECT') && server.includes(LEGACY_CATCH)]
  ];
  for (const [name, bad] of patchable) {
    result.checks.push({ name, ok: !bad });
    if (bad) result.patchable.push(name);
  }

  const mustExist = [
    ['ready_endpoint_present', server.includes("url.pathname === '/ready'")],
    ['selftest_endpoint_present', server.includes("url.pathname === '/selftest'")],
    ['remote_hardware_commands_disabled', server.includes('remote_hardware_commands: false')],
    ['selftest_file_present', fs.existsSync(FILES.selftest)]
  ];
  for (const [name, ok] of mustExist) {
    result.checks.push({ name, ok });
    if (!ok) result.blocked.push(name);
  }

  result.test = runTest();
  result.checks.push({ name: 'npm_test', ok: result.test.ok });

  if (result.blocked.length) result.status = 'UNPATCHABLE';
  else if (result.patchable.length) result.status = 'PATCHABLE';
  else if (!result.test.ok) {
    result.blocked.push('test_failed_without_safe_recipe');
    result.status = 'UNPATCHABLE';
  }

  return result;
}

function applyPatch(result) {
  if (result.status !== 'PATCHABLE') {
    throw new Error('refusing_patch_for_status_' + result.status);
  }

  const changed = [];

  if (result.patchable.includes('package_test_gate_missing')) {
    const pkg = JSON.parse(read(FILES.pkg));
    pkg.scripts = pkg.scripts || {};
    pkg.scripts.test = 'node --check server.js && node selftest.js';
    write(FILES.pkg, JSON.stringify(pkg, null, 2) + '\n');
    changed.push('package.json:test_gate');
  }

  if (result.patchable.includes('docker_selftest_copy_missing') ||
      result.patchable.includes('docker_test_gate_missing')) {
    const canonical = [
      'FROM node:20-alpine',
      'WORKDIR /app',
      'COPY package.json ./',
      'COPY server.js ./',
      'COPY selftest.js ./',
      'ENV NODE_ENV=production',
      'RUN npm test',
      'EXPOSE 3000',
      'CMD ["node","server.js"]',
      ''
    ].join('\n');
    write(FILES.docker, canonical);
    changed.push('Dockerfile:test_gate');
  }

  let server = read(FILES.server);
  if (result.patchable.includes('telemetry_numeric_string_compat_missing')) {
    if (!server.includes(LEGACY_VALIDATION)) throw new Error('legacy_validation_signature_changed');
    server = server.replace(LEGACY_VALIDATION, NORMALIZED_VALIDATION);
    changed.push('server.js:numeric_string_compat');
  }

  if (result.patchable.includes('telemetry_reject_diagnostic_missing')) {
    if (!server.includes(LEGACY_CATCH)) throw new Error('legacy_catch_signature_changed');
    server = server.replace(LEGACY_CATCH, DIAGNOSTIC_CATCH);
    changed.push('server.js:telemetry_reject_diagnostic');
  }

  write(FILES.server, server);

  const after = diagnose();
  if (after.status !== 'HEALTHY') {
    throw new Error('post_patch_not_healthy:' + JSON.stringify({
      status: after.status,
      blocked: after.blocked,
      patchable: after.patchable,
      test: after.test && { ok: after.test.ok, status: after.test.status }
    }));
  }

  return { changed, after };
}

function argValue(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : null;
}

function saveResult(obj) {
  const out = argValue('--write-result');
  if (out) fs.writeFileSync(path.resolve(out), JSON.stringify(obj, null, 2) + '\n');
}

const mode = process.argv[2] || 'diagnose';

try {
  if (mode === 'diagnose') {
    const result = diagnose();
    saveResult(result);
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
    if (result.status === 'HEALTHY') process.exit(0);
    if (result.status === 'PATCHABLE') process.exit(10);
    process.exit(20);
  }

  if (mode === 'patch') {
    const before = diagnose();
    const patched = applyPatch(before);
    const output = { before, changed: patched.changed, after: patched.after };
    saveResult(output);
    process.stdout.write(JSON.stringify(output, null, 2) + '\n');
    process.exit(0);
  }

  throw new Error('unknown_mode:' + mode);
} catch (err) {
  const output = {
    version: 1,
    scope: 'DJAEGER_AI_ONLY',
    at: new Date().toISOString(),
    status: 'ERROR',
    error: String(err && err.stack || err).slice(0, 6000)
  };
  saveResult(output);
  process.stderr.write(JSON.stringify(output, null, 2) + '\n');
  process.exit(30);
}
