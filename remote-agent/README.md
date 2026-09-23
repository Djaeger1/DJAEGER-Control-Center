# DJAEGER Remote Boot Agent — isolated prototype

This branch is intentionally isolated from the production DJAEGER code. Nothing here changes the current module/APK until it is explicitly promoted.

## Goal

Run the official Remote Desktop Commander device agent automatically from a Magisk/KernelSU module so the terminal application does **not** need to stay open.

Flow:

```
Android boot
  -> Magisk/KernelSU service.sh
  -> djaeger-remote-launcher.sh
  -> Desktop Commander remote device agent
  -> hosted Remote MCP
  -> ChatGPT Remote Desktop Commander plugin
```

There is no extra Railway service and no Cloudflare tunnel. The user does not copy API keys, bearer tokens, or device IDs.

## Authentication behavior

The official Desktop Commander remote agent uses OAuth 2.0 device authorization. The first pairing still requires approving the browser page once. The prototype watches the agent output and opens that verification URL automatically.

After successful pairing, the official agent stores its session in:

```
$HOME/.desktop-commander-device/device.json
```

The prototype gives the agent a private module-owned HOME and locks that file to mode 0600. Current upstream source persists refreshed sessions, allowing later restarts to restore the session instead of requiring a new token to be copied by the user.

## Runtime strategy

Prototype v0.1 deliberately does **not** bundle a second Node.js runtime. It finds the existing `npx` runtime already installed on the Android device and starts it from the boot service. The terminal app itself does not have to be open.

This is a bridge prototype only. A later self-contained build can bundle a runtime after Android compatibility is proven.

## Safety

- Version pinned to Desktop Commander 0.2.51; no `@latest` drift at boot.
- State directory and OAuth session are root-only.
- Restart watchdog has a delay to avoid a crash loop.
- A `state/DISABLED` kill-switch stops remote access without uninstalling the module.
- `action.sh` toggles ENABLED/DISABLED on module managers that expose an Action button.
- No changes to DJAEGER production paths are made by this prototype.

## Important qualification

Remote Desktop Commander officially documents macOS, Windows and Linux. Android/Termux usage exists in upstream issue reports, but Android is not yet an officially listed target. Therefore this branch must remain a prototype until a real-device test proves:

1. remote config fetch succeeds,
2. first OAuth pairing succeeds,
3. ChatGPT `list_devices` sees the device,
4. remote ping succeeds,
5. reboot restores the persisted session without manual terminal startup,
6. 30-minute stability window passes,
7. no DJAEGER production files are touched.
