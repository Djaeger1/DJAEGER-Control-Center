# DJAEGER APK Reverse v0.2.0

Model A Control Center layout: Analysis, AI explanation, Operations status, Runtime checks and Workspace export.

Standalone Android APK for local, read-only reconnaissance of APK packages.

Current scope:
- Android document picker for APK selection.
- Stream-read analysis without first copying the whole APK.
- SHA-256 calculation.
- ZIP entry inventory.
- DEX and native library/ABI inventory.
- Conventional META-INF signature entry detection.
- Bounded printable-string extraction from DEX.
- Copy/share of a human-readable report.

This v0.1 intentionally does not patch or repackage APKs, bypass security controls, inject Frida hooks, intercept network traffic, or modify the selected application.

The app is designed to be standalone: no Termux dependency and no host command is required for the analysis workflow.
