'use strict';

const { spawn } = require('child_process');

const PORT = 39091;
const TOKEN = 'DJAEGER_TEST_TOKEN_123456789';
const base = 'http://127.0.0.1:' + PORT;
const child = spawn(process.execPath, ['server.js'], {
  cwd: __dirname,
  env: {
    ...process.env,
    PORT: String(PORT),
    DJAEGER_ACCESS_TOKEN: TOKEN,
    MAX_TRACES: '50',
    BODY_LIMIT_BYTES: '65536',
    DJAEGER_BUILD_ID: 'SELFTEST'
  },
  stdio: ['ignore', 'pipe', 'pipe']
});

let stderr = '';
child.stderr.on('data', d => { stderr += d.toString(); });

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function waitReady() {
  const deadline = Date.now() + 7000;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(base + '/ready');
      if (r.status === 200) return;
    } catch {}
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error('server_not_ready');
}

async function request(path, options = {}) {
  const r = await fetch(base + path, options);
  let body = null;
  try { body = await r.json(); } catch {}
  return { status: r.status, body };
}

(async () => {
  try {
    await waitReady();

    const health = await request('/health');
    assert(health.status === 200 && health.body && health.body.ok === true, 'health_failed');
    assert(health.body.hardware_authority === 'NONE', 'hardware_authority_regression');

    const self = await request('/selftest');
    assert(self.status === 200 && self.body && self.body.ok === true, 'selftest_failed');

    const headers = {
      'content-type': 'application/json',
      'authorization': 'Bearer ' + TOKEN
    };

    const good = await request('/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        schema: 'DJAEGER_TELEMETRY_V1',
        device_id: 'SELFTEST',
        profile: 'STABLE',
        neurons_used: '10000',
        neurons_limit: '10000',
        provider_quota_state: 'UNKNOWN',
        hermes_cloud_state: 'ONLINE',
        skin_temp_c: '39.5',
        fps: '60',
        jank_pct: '1.2'
      })
    });
    assert(good.status === 200 && good.body && good.body.ok === true, 'valid_telemetry_rejected');

    const state = await request('/v1/device/state', { headers });
    assert(state.status === 200, 'state_failed');
    assert(state.body.state.neurons_used === 10000 && state.body.state.neurons_limit === 10000, 'neuron_state_corrupt');
    assert(state.body.state.skin_temp_c === 39.5 && state.body.state.fps === 60, 'numeric_string_not_normalized');

    const obsGood = await request('/v1/device/observability', { headers });
    assert(obsGood.status === 200 && obsGood.body && obsGood.body.ok === true, 'observability_failed');
    assert(obsGood.body.telemetry_stats.accepted === 1, 'observability_accepted_count_wrong');
    assert(obsGood.body.last_known_good.neurons_used === 10000, 'known_good_baseline_missing');
    assert(Array.isArray(obsGood.body.last_anomalies) && obsGood.body.last_anomalies.length === 0, 'false_anomaly_on_good_sample');

    const unknownSentinel = await request('/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        neurons_used: '0',
        neurons_limit: '0',
        skin_temp_c: 'UNKNOWN',
        fps: ''
      })
    });
    assert(unknownSentinel.status === 200, 'unknown_sentinel_rejected');

    const unknownState = await request('/v1/device/state', { headers });
    assert(unknownState.body.state.neurons_used === 0, 'zero_neuron_used_changed');
    assert(unknownState.body.state.neurons_limit === null, 'zero_limit_not_normalized_to_unknown');
    assert(unknownState.body.state.skin_temp_c === null && unknownState.body.state.fps === null, 'sentinel_not_normalized');

    const obsUnknown = await request('/v1/device/observability', { headers });
    assert(obsUnknown.body.telemetry_stats.accepted === 2, 'observability_second_sample_missing');
    assert(obsUnknown.body.last_known_good.neurons_used === 0, 'info_anomaly_should_remain_known_good');
    assert(obsUnknown.body.last_anomalies.some(a => a.code === 'NEURON_LIMIT_UNKNOWN' && a.severity === 'INFO'), 'unknown_limit_info_missing');

    const zeroBlocked = await request('/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        neurons_used: '0',
        neurons_limit: '10000',
        provider_quota_state: 'EXHAUSTED',
        hermes_cloud_state: 'STANDBY',
        agent_execution_status: 'FAILED'
      })
    });
    assert(zeroBlocked.status === 200 && zeroBlocked.body.known_good === true, 'provider_blocked_zero_should_be_info');

    const obsBlocked = await request('/v1/device/observability', { headers });
    assert(obsBlocked.body.last_anomalies.some(a => a.code === 'NEURONS_ZERO_PROVIDER_BLOCKED' && a.severity === 'INFO'), 'provider_blocked_zero_info_missing');
    assert(obsBlocked.body.telemetry_stats.anomalous === 0, 'info_should_not_increment_anomalous');

    const zeroBug = await request('/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        neurons_used: '0',
        neurons_limit: '10000',
        provider_quota_state: 'AVAILABLE',
        hermes_cloud_state: 'READY'
      })
    });
    assert(zeroBug.status === 200 && zeroBug.body.known_good === false, 'ready_cloud_zero_warning_not_detected');

    const obsZero = await request('/v1/device/observability', { headers });
    assert(obsZero.body.last_anomalies.some(a => a.code === 'NEURONS_ZERO_WITH_READY_CLOUD' && a.severity === 'WARN'), 'ready_cloud_zero_anomaly_missing');
    assert(obsZero.body.telemetry_stats.anomalous === 1, 'anomalous_count_wrong');

    const badNeuron = await request('/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: JSON.stringify({ neurons_used: '10001', neurons_limit: '10000' })
    });
    assert(badNeuron.status === 422, 'invalid_neuron_state_not_rejected');

    const badJson = await fetch(base + '/v1/device/telemetry', {
      method: 'POST',
      headers,
      body: '{bad-json'
    });
    assert(badJson.status === 400, 'invalid_json_not_rejected');

    const unauth = await request('/v1/device/state');
    assert(unauth.status === 401, 'auth_regression');

    console.log('PASS|DJAEGER_AI_AUTOHEAL_SELFTEST');
    console.log('PASS|health');
    console.log('PASS|ready');
    console.log('PASS|hardware_authority_none');
    console.log('PASS|valid_neurons_10000_10000');
    console.log('PASS|numeric_string_compat');
    console.log('PASS|unknown_sentinel_compat');
    console.log('PASS|telemetry_observability');
    console.log('PASS|last_known_good_baseline');
    console.log('PASS|zero_neuron_accounting_context');
    console.log('PASS|provider_quota_decoupled_observability');
    console.log('PASS|reject_neurons_over_limit');
    console.log('PASS|reject_invalid_json');
    console.log('PASS|auth_guard');
  } catch (err) {
    console.error('FAIL|' + String(err && err.message || err));
    if (stderr) console.error(stderr.slice(0, 2000));
    process.exitCode = 1;
  } finally {
    child.kill('SIGTERM');
    setTimeout(() => child.kill('SIGKILL'), 1000).unref();
  }
})();
