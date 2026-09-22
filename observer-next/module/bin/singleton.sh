#!/system/bin/sh
# Shared DJAEGER AI single-instance guard.
# Source this file, then call: djaeger_singleton_claim <worker-name>
djaeger_singleton_claim(){
  _dj_name="$1"
  [ -n "$_dj_name" ] || return 1
  _dj_dir="$ROOT/runtime/locks"
  _dj_lock="$_dj_dir/${_dj_name}.lock"
  mkdir -p "$_dj_dir" || exit 0
  chmod 700 "$_dj_dir" 2>/dev/null

  if mkdir "$_dj_lock" 2>/dev/null; then
    printf '%s\n' "$$" > "$_dj_lock/pid"
  else
    _dj_old="$(cat "$_dj_lock/pid" 2>/dev/null)"
    case "$_dj_old" in ''|*[!0-9]*) _dj_old=0;; esac
    if [ "$_dj_old" -gt 1 ] 2>/dev/null && kill -0 "$_dj_old" 2>/dev/null; then
      exit 0
    fi
    rm -rf "$_dj_lock" 2>/dev/null
    mkdir "$_dj_lock" 2>/dev/null || exit 0
    printf '%s\n' "$$" > "$_dj_lock/pid"
  fi
  chmod 700 "$_dj_lock" 2>/dev/null
  _dj_self="$(cat "$_dj_lock/pid" 2>/dev/null)"

  # Only the process that still owns the PID file may remove the lock.
  # Without this ownership check, an old worker exiting late can delete a
  # newly-started worker's lock directory after a hot restart.
  djaeger_singleton_cleanup(){
    _dj_owner="$(cat "$_dj_lock/pid" 2>/dev/null)"
    [ -n "$_dj_self" ] && [ "$_dj_owner" = "$_dj_self" ] && rm -rf "$_dj_lock" 2>/dev/null
  }

  # EXIT only cleans the lock. Signal traps must also terminate the worker.
  # TERM/HUP used to remove the lock unconditionally, which could race with
  # replacement workers and make a healthy process appear dead.
  trap 'djaeger_singleton_cleanup' EXIT
  trap 'djaeger_singleton_cleanup; trap - EXIT INT TERM HUP; exit 0' INT TERM HUP
}
