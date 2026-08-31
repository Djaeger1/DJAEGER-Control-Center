# Exact artifact audit contract

The candidate is acceptable for one-device validation only when all of these
checks pass on the exact APK delivered to the user:

1. Gradle release compilation and JVM unit tests pass.
2. APK ZIP integrity passes.
3. APK Signature Schemes v2 and v3 verify with a non-debug certificate.
4. `apkanalyzer manifest debuggable` reports `false`.
5. The binary manifest contains only the launcher `MainActivity`; no service,
   receiver, provider, or forbidden permission remains.
6. DEX contains the `v0.12.1-r2` and `v12.9.50-r3` pairing markers.
7. DEX contains no retired HUD/overlay markers.
8. Source audit finds no sysfs mutation, network/game traffic mutation, generic
   settings/property mutation, or direct Gemini model override.
9. Every optional sysfs node read is newline-safe.
10. Missing values remain missing rather than becoming zero samples.
11. Power normalization passes standard-node priority, SM5602 fallback,
    vendor-mA conversion, plausibility, and discharge-only fixtures.

Passing this contract is a static/synthetic gate. It does not replace the
single hardware validation required by the project handoff.
