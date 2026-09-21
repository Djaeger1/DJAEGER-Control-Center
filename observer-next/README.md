# DJAEGER AI Adaptive

Clean device-first rebuild of DJAEGER AI.

## Core loop

OBSERVE → LEARN → PROPOSE → VALIDATE → SHADOW → LOCAL EXECUTE → READBACK → LEARN.

- CPU, GPU, thermal, battery/power, foreground workload and frame behavior are measured directly from the device.
- No static legacy performance preset is authoritative.
- Gemini proposes only frequencies that stay inside the measured device envelope.
- HERMES Local validates workload, exact kernel OPP membership, thermal headroom and frame maturity.
- ONE HERMES Cloud reviews the exact same candidate and has no direct hardware-write authority.
- A candidate proceeds only when Gemini, HERMES Local and HERMES Cloud agree on the same digest and confidence gates pass.
- Counterfactual shadow evidence must show frame behavior is not worse and power is not worse before execution approval exists.
- Only the local device executor may write CPU/GPU min/max bounds. It validates path, exact OPP, workload, package, freshness, thermal limits, approval expiry and digest binding before any write.
- The executor captures pre-apply CPU/GPU bounds and restores them on context change, approval expiry, thermal guard closure, write/readback failure or shutdown.
- The APK remains UI/telemetry only and never writes sysfs.
- Gemini keys, HERMES credentials/ID and the DJAEGER access token are migrated by explicit-key allowlist only. Raw legacy files, controllers and old profile maps are never imported.
- The Control Center Overview layout remains the familiar layout while the engine behind it is adaptive and device-learned.
- Manual GAME registry entries join the same measurement, reasoning, shadow and local execution pipeline. APP/SYSTEM/UNKNOWN workloads fail closed for hardware execution.

## Authority

Cloud reasoning is advisory. Hardware authority exists only on the local device, inside the gated executor. Native thermal protection remains independent and authoritative.

## Railway

The dedicated DJAEGER AI core receives bounded telemetry and advisory proposals only. It cannot issue remote hardware commands.
