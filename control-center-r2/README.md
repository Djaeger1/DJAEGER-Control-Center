# DJAEGER Control Center v0.12.1-r2

Status: **candidate source**, paired only with
`DJAEGER v12.9.50-r3 Transactional Restore Integrity`.

This project continues the existing v0.12.1 Control Center line. It is a
minimal maturity revision of r1, not a redesign.

## Preserved contract

- Compact v0.12.1 Compose UI and Overview / Session / Charts / AI / History /
  Safety / Logs tabs.
- One-second read-only telemetry.
- COPY actions, Gemini chat, Gemini key management, typed user modes, and
  module audit/status commands.
- Gemini remains advisory. Hardware authority stays in the DJAEGER module.
- No direct sysfs writes, network/game traffic manipulation, HUD, overlay,
  launcher, boot receiver, usage access, or foreground service.

## r2 remediation

- Restores a complete Gradle project that can be rebuilt.
- Forces a newline after every optional live sysfs read.
- Uses `-1`/gaps for missing sensors across cards, statistics, and charts.
- Prefers the standard battery current node and uses SM5602 only as fallback.
- Mirrors the module's uA/mA, voltage, power, and discharge-only validity
  gates.
- Removes the final `Settings.canDrawOverlays` reference.
- Removes AndroidX Startup/ProfileInstaller runtime components.
- Builds a non-debuggable release variant and audits the exact signed APK.

## Release gate

Do not label this pair stable until the single mature device validation from
`README_WORK_HANDOFF.md` passes. The generated signing identity must be retained
for every future Control Center update.
