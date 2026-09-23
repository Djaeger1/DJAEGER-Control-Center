# DJAEGER Remote Boot Agent — isolated prototype

This branch is intentionally isolated from production DJAEGER code. Nothing here changes the current module/APK until it is explicitly promoted.

## Goal

Run the official Remote Desktop Commander device agent automatically from a Magisk/KernelSU module so the terminal application does not need to stay open.

```
Android boot
  -> Magisk/KernelSU service.sh
  -> djaeger-remote-launcher.sh
  -> Desktop Commander remote device agent
  -> hosted Remote MCP
  -> ChatGPT Remote Desktop Commander plugin
```

No extra relay service is added. The user does not copy API keys, bearer tokens, or device IDs.

## Authentication behavior

The official device agent uses OAuth 2.0 device authorization. First pairing still requires one browser approval. The prototype watches agent output and opens the verification URL automatically.

After successful pairing, the official agent stores its session in:

```
$HOME/.desktop-commander-device/device.json
```

The prototype gives the agent a private module-owned HOME and locks that session file to mode 0600. Current upstream source persists rotated refresh sessions so later restarts can restore them without asking the user to copy credentials.

## Runtime strategy

Prototype v0.1 deliberately does not bundle a second Android Node runtime. It reuses an existing Android Node/npx runtime from TermOnePlus or Termux, but the terminal application process itself does not need to remain open.

The launcher performs a public endpoint preflight before starting the agent. Network failures use bounded retry delays. HTTP 403 uses a 15-minute backoff to avoid a battery/network crash loop.

## Safety

- Desktop Commander package is pinned to 0.2.51; the boot service does not track a moving package version.
- State directory and OAuth session are root-only.
- Restart watchdog uses bounded delays.
- A state/DISABLED kill-switch stops remote access without uninstalling the module.
- action.sh toggles ENABLED/DISABLED on module managers that expose an Action button.
- uninstall.sh terminates launcher/agent processes.
- No DJAEGER production path is modified by this branch.

## Verified build state

GitHub Actions validates POSIX shell syntax, ShellCheck error-level findings, the isolation contract, ZIP layout, and produces a SHA-256 checksum.

Current CI state for commit f14e88b4b4205c105bd216226a2cf61ab5b37a1c: PASS.

## Upstream blockers / uncertainty

Remote Desktop Commander officially documents macOS, Windows and Linux, not Android.

Upstream issue #673 remains open. Android/Termux reproduced HTTP 403 on the public remote configuration endpoint through version 0.2.50, including both Wi-Fi and mobile data. The prototype therefore treats a 403 as a blocked state rather than repeatedly restarting.

There is also a newer upstream remote-readiness fix (#724) merged after the 0.2.51 release. Upstream telemetry cited in that fix includes affected 0.2.51 devices. Until a package containing that fix is released, a device may appear online yet still be unreachable.

Therefore BUILD_PASS is not DEVICE_PASS.

## Real-device qualification gate

Do not promote this prototype until a real Android device proves all of the following:

1. preflight returns HTTP 2xx,
2. first OAuth pairing succeeds,
3. ChatGPT list_devices sees the device,
4. remote ping succeeds,
5. one read-only command succeeds,
6. terminal app can be closed while the agent stays reachable,
7. reboot restores the persisted session without manual terminal startup,
8. 30-minute stability window passes,
9. uninstall/disable kills remote access,
10. no DJAEGER production files are touched.
