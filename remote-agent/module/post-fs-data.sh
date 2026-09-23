#!/system/bin/sh
MODDIR=${0%/*}
STATE="$MODDIR/state"

mkdir -p "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"
chmod 700 "$STATE" "$STATE/home" "$STATE/tmp" "$STATE/npm-cache"

# Remote Desktop Commander persists OAuth session under HOME.
# Keep the credential store private to root.
if [ -f "$STATE/home/.desktop-commander-device/device.json" ]; then
  chmod 600 "$STATE/home/.desktop-commander-device/device.json"
fi
