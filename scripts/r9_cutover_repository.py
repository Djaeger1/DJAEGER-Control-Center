#!/usr/bin/env python3
from pathlib import Path
import re

p = Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt')
s = p.read_text()

start_marker = '    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'
end_marker = '    suspend fun setUserMode(mode:String):Pair<Boolean,String> = withContext(Dispatchers.IO) {'
start = s.find(start_marker)
end = s.find(end_marker, start + 1)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('R9_CUTOVER_FAIL=snapshot-boundary-not-found')

legacy = s[start:end]
required_legacy = [
    '/sys/class/thermal/thermal_zone',
    'scaling_cur_freq',
    '/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq',
]
missing = [x for x in required_legacy if x not in legacy]
if missing:
    raise SystemExit('R9_CUTOVER_FAIL=unexpected-baseline:' + ','.join(missing))

replacement = r'''    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){
        val read = ConsolidatedSnapshotReader(persistent + "/cc_snapshot").read(4000)
        val mapped = ConsolidatedRuntimeMapper.map(read)
            ?: return@withContext RuntimeState(error=read.error.ifBlank { "SNAPSHOT_UNAVAILABLE" })

        val rt = mapped.runtime
        val tel = parseTelemetry(mapped.telemetryRaw)
        val now = System.currentTimeMillis()/1000
        val age = if(tel.epoch > 0) now - tel.epoch else Long.MAX_VALUE
        val fresh = tel.epoch > 0 && age in 0..5

        // Preserve r7 Network Intelligence while keeping r9's single atomic read.
        // NETWORK is already published by DJAEGER inside cc_snapshot; no network
        // commands, sysfs reads, or game traffic changes are performed here.
        val nkv = AtomicSnapshot.keyValues(mapped.network)
        val netAt = nkv["UPDATED_AT"]?.toLongOrNull() ?: 0L
        val netFresh = nkv["SESSION_ACTIVE"] == "1" && netAt > 0 && (now-netAt) in 0..30
        val network = if(netFresh) NetworkState(
            ping=nkv["PING_CURRENT_MS"] ?: "—",
            avg=nkv["PING_AVG_MS"] ?: "—",
            p95=nkv["PING_P95_MS"] ?: "—",
            jitter=nkv["JITTER_MS"] ?: "—",
            loss=nkv["PACKET_LOSS_PCT"] ?: "—",
            quality=nkv["QUALITY"] ?: "UNKNOWN",
            fresh=true
        ) else NetworkState()

        RuntimeState(
            root=true,
            sampleFresh=fresh,
            installed=mapped.installed,
            active=rt["ACTIVE"] ?: rt["active"] ?: "0",
            game=rt["GAME"] ?: rt["game"] ?: "NA",
            window=rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE",
            controllerPid=rt["CONTROLLER_PID"] ?: rt["controller_pid"] ?: "",
            predictorPid=rt["PREDICTOR_PID"] ?: rt["predictor_pid"] ?: "",
            updated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0,
            userMode=rt["USER_MODE"] ?: rt["user_mode"] ?: "AUTO",
            moduleVersion=mapped.moduleVersion,
            telemetry=tel,
            brain=mapped.brain,
            envelope=mapped.envelope,
            geminiHttp=mapped.geminiHttp,
            geminiServer=mapped.geminiServer,
            decisions=mapped.decisions,
            plans=mapped.plans,
            frameIntel=mapped.frameIntel,
            log=mapped.log,
            latestDecision=parseDecision(mapped.decisions),
            latestPlan=parsePlan(mapped.plans),
            network=network
        )
    }

'''

s2 = s[:start] + replacement + s[end:]

# Recurring repository snapshot must no longer contain direct hardware/network reads.
new_start = s2.find(start_marker)
new_end = s2.find(end_marker, new_start + 1)
new_snapshot = s2[new_start:new_end]
for forbidden in [
    '/sys/', 'thermal_zone', 'scaling_cur_freq', 'kgsl-3d0',
    'iptables', 'nft ', 'ip route', 'setprop net.',
]:
    if forbidden in new_snapshot:
        raise SystemExit('R9_CUTOVER_FAIL=forbidden-in-snapshot:' + forbidden)

for required in [
    'geminiKeyVaultStatus', 'addGeminiKeyToVault', 'selectGeminiKey',
    'removeGeminiKey', 'geminiChat', 'authoritySyncStatus',
    'kernelCapabilitySummary', 'maturityAudit', 'parseTelemetry',
    'parseDecision', 'parsePlan',
]:
    if required not in s2:
        raise SystemExit('R9_CUTOVER_FAIL=lost-required-symbol:' + required)

# Semantic regression guard: r7 NetworkState must be populated from the
# consolidated NETWORK section instead of silently falling back to defaults.
for required in ['AtomicSnapshot.keyValues(mapped.network)', 'network=network']:
    if required not in new_snapshot:
        raise SystemExit('R9_CUTOVER_FAIL=network-regression:' + required)

p.write_text(s2)
print('R9_CUTOVER=PASS')
print('R9_NETWORK_PRESERVATION=PASS')
print('RECURRING_ROOT_READ=cc_snapshot_only')
print('DIRECT_SYSFS_IN_SNAPSHOT=NO')
