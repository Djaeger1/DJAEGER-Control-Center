#!/system/bin/sh
# DJAEGER_ADAPTIVE_REMOTE_UPDATER_V1
# Software files only. No sysfs/proc-sys writes and no hardware commands.
ROOT="${1:-/data/adb/djaeger_observer}"
MOD="${2:-/data/adb/modules/djaeger_ai_observer}"
CFG="$ROOT/config/railway.env"
RUNTIME="$ROOT/runtime"
REC="$ROOT/recovery"
STATE="$RUNTIME/remote_update.env"
SEQFILE="$REC/remote_update_seq"
RELFILE="$REC/remote_update_release"
PIDFILE="$RUNTIME/remote_updater.pid"
DEFAULT_URL="https://djaeger-ai-core-production-736f.up.railway.app"

mkdir -p "$RUNTIME" "$REC" "$REC/remote-updates" 2>/dev/null || exit 2
chmod 700 "$RUNTIME" "$REC" "$REC/remote-updates" 2>/dev/null || true

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
qget(){
  [ -r "$1" ] || return 0
  awk -F= -v k="$2" '$1==k{v=substr($0,index($0,"=")+1);gsub(/^[[:space:]\047\042]+|[[:space:]\047\042]+$/,"",v);print v;exit}' "$1" 2>/dev/null
}
clean(){ printf '%s' "${1:-}" | tr '\r\n\t' '   ' | tr "'" ' ' | cut -c1-220; }
num(){ case "${1:-}" in ''|*[!0-9]*) echo 0;; *) echo "$1";; esac; }
vc(){ sed -n 's/^versionCode=//p' "$MOD/module.prop" 2>/dev/null | head -1; }
device_id(){
  _id="$(kv DEVICE_ID "$ROOT/config/identity.env")"
  [ -n "$_id" ] || _id="$(cat /data/adb/djaeger_ai/railway/device_id 2>/dev/null | head -1 | tr -d '\r\n')"
  [ -n "$_id" ] || _id="$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '\r\n')"
  printf '%s' "$_id"
}
publish(){
  _t="$STATE.tmp.$$"
  {
    echo "SCHEMA=DJAEGER_ADAPTIVE_REMOTE_UPDATE_V1"
    echo "STATE=$(clean "$1")"
    echo "SEQ=$(clean "${2:-$(cat "$SEQFILE" 2>/dev/null)}")"
    echo "RELEASE=$(clean "${3:-$(cat "$RELFILE" 2>/dev/null)}")"
    echo "DETAIL=$(clean "${4:-NA}")"
    echo "UPDATED_AT=$(date +%s)"
  } >"$_t" 2>/dev/null && { chmod 600 "$_t"; mv -f "$_t" "$STATE"; }
}
curlcfg(){
  _tok="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"
  [ -n "$_tok" ] || return 1
  _f="$RUNTIME/.curlcfg.$$"
  printf 'header = "Authorization: Bearer %s"\n' "$_tok" >"$_f" || return 1
  chmod 600 "$_f"
  printf '%s' "$_f"
}
fetch(){
  _url="$1"; _out="$2"; _cfg="$(curlcfg)" || return 1
  _code="$(curl -4 --http1.1 --connect-timeout 4 -m 10 -sS -o "$_out" -w '%{http_code}' -K "$_cfg" "$_url" 2>/dev/null)"; _rc=$?
  if [ "$_rc" -ne 0 ]; then
    _code="$(curl --http1.1 --connect-timeout 4 -m 10 -sS -o "$_out" -w '%{http_code}' -K "$_cfg" "$_url" 2>/dev/null)"; _rc=$?
  fi
  rm -f "$_cfg"
  [ "$_rc" -eq 0 ] && [ "$_code" = 200 ]
}
ack(){
  _seq="$1"; _rel="$2"; _st="$3"; _detail="$4"
  _url="$(kv DJAEGER_RAILWAY_URL "$CFG")"; [ -n "$_url" ] || _url="$DEFAULT_URL"
  _cfg="$(curlcfg)" || return 0
  _body="$RUNTIME/.ack.$$"
  printf '{"device_id":"%s","seq":%s,"release":"%s","state":"%s","detail":"%s","module_version_code":"%s"}'     "$(clean "$(device_id)")" "$(num "$_seq")" "$(clean "$_rel")" "$(clean "$_st")" "$(clean "$_detail")" "$(clean "$(vc)")" >"$_body"
  curl -4 --http1.1 --connect-timeout 4 -m 10 -sS -o /dev/null -K "$_cfg" -H 'Content-Type: application/json' --data-binary @"$_body" "${_url%/}/v1/device/update/ack" 2>/dev/null ||   curl --http1.1 --connect-timeout 4 -m 10 -sS -o /dev/null -K "$_cfg" -H 'Content-Type: application/json' --data-binary @"$_body" "${_url%/}/v1/device/update/ack" 2>/dev/null || true
  rm -f "$_cfg" "$_body"
}
allow_path(){
  _p="$1"
  case "$_p" in ''|/*|*'..'*|*'//'*) return 1;; esac
  case "$_p" in bin/*.sh|service.sh|module.prop) return 0;; *) return 1;; esac
}
restart_bridge(){
  for _d in /proc/[0-9]*; do
    [ -r "$_d/cmdline" ] || continue
    _p="${_d##*/}"
    _cmd="$(tr '\000' ' ' <"$_d/cmdline" 2>/dev/null)"
    case "$_cmd" in *"$MOD/bin/railway_bridge.sh"*) kill "$_p" 2>/dev/null || true;; esac
  done
  sleep 1
  nohup sh "$MOD/bin/railway_bridge.sh" "$ROOT" daemon >/dev/null 2>&1 </dev/null &
}
check_once(){
  [ -r "$CFG" ] || { publish BLOCKED 0 NONE CONFIG_MISSING; return 2; }
  _tok="$(kv DJAEGER_ACCESS_TOKEN "$CFG")"; [ -n "$_tok" ] || { publish BLOCKED 0 NONE TOKEN_MISSING; return 3; }
  _url="$(kv DJAEGER_RAILWAY_URL "$CFG")"; [ -n "$_url" ] || _url="$DEFAULT_URL"
  case "$_url" in https://*) :;; *) publish BLOCKED 0 NONE INVALID_URL; return 4;; esac
  _vc="$(vc)"; case "$_vc" in 202|203) :;; *) publish INCOMPATIBLE 0 NONE "VC_${_vc:-MISSING}"; return 5;; esac
  _did="$(device_id)"
  _mf="$RUNTIME/.manifest.$$"
  fetch "${_url%/}/v1/device/update/manifest.txt?vc=$_vc&device_id=$_did" "$_mf" || { rm -f "$_mf"; publish OFFLINE "$(cat "$SEQFILE" 2>/dev/null)" "$(cat "$RELFILE" 2>/dev/null)" MANIFEST_FETCH_FAILED; return 6; }
  _schema="$(qget "$_mf" SCHEMA)"; _seq="$(qget "$_mf" SEQ)"; _rel="$(qget "$_mf" RELEASE)"; _target="$(qget "$_mf" TARGET_VC)"; _count="$(qget "$_mf" FILE_COUNT)"
  [ "$_schema" = DJAEGER_ADAPTIVE_REPAIR_V1 ] || { rm -f "$_mf"; publish REJECTED 0 NONE BAD_SCHEMA; return 7; }
  case "$_seq" in ''|*[!0-9]*) rm -f "$_mf"; publish REJECTED 0 NONE BAD_SEQ; return 8;; esac
  printf ',%s,' "$_target" | grep -Fq ",$_vc," || { rm -f "$_mf"; publish INCOMPATIBLE "$_seq" "$_rel" "TARGET_$_target"; return 9; }
  _cur="$(cat "$SEQFILE" 2>/dev/null)"; case "$_cur" in ''|*[!0-9]*) _cur=0;; esac
  if [ "$_seq" -le "$_cur" ] 2>/dev/null; then rm -f "$_mf"; publish CURRENT "$_cur" "$(cat "$RELFILE" 2>/dev/null)" NO_UPDATE; return 0; fi

  _stage="$REC/remote-updates/stage.$_seq.$$"; _bak="$REC/remote-updates/backup.$_seq"; mkdir -p "$_stage" "$_bak" || { rm -f "$_mf"; publish ERROR "$_seq" "$_rel" STAGE_FAILED; return 10; }
  _list="$_stage/files.list"; : >"$_list"; _seen=0
  while IFS='|' read -r _tag _id _path _sha _mode; do
    [ "$_tag" = FILE ] || continue
    _seen=$((_seen+1)); allow_path "$_path" || { rm -rf "$_stage"; rm -f "$_mf"; publish REJECTED "$_seq" "$_rel" "PATH_DENIED_$_path"; return 11; }
    case "$_id" in ''|*[!A-Za-z0-9._-]*) rm -rf "$_stage"; rm -f "$_mf"; publish REJECTED "$_seq" "$_rel" BAD_FILE_ID; return 12;; esac
    _sf="$_stage/$_id"
    fetch "${_url%/}/v1/device/update/file/$_id" "$_sf" || { rm -rf "$_stage"; rm -f "$_mf"; publish OFFLINE "$_seq" "$_rel" "FILE_FETCH_FAILED_$_id"; return 13; }
    _got="$(sha256sum "$_sf" 2>/dev/null | awk '{print $1}')"; [ "$_got" = "$_sha" ] || { rm -rf "$_stage"; rm -f "$_mf"; publish REJECTED "$_seq" "$_rel" "HASH_MISMATCH_$_id"; return 14; }
    case "$_path" in *.sh|service.sh|bin/*) sh -n "$_sf" >/dev/null 2>&1 || { rm -rf "$_stage"; rm -f "$_mf"; publish REJECTED "$_seq" "$_rel" "SHELL_SYNTAX_$_path"; return 15; };; esac
    printf '%s|%s|%s|%s\n' "$_id" "$_path" "$_mode" "$_sf" >>"$_list"
  done <"$_mf"
  _expect="$(num "$_count")"; [ "$_seen" -eq "$_expect" ] || { rm -rf "$_stage"; rm -f "$_mf"; publish REJECTED "$_seq" "$_rel" COUNT_MISMATCH; return 16; }

  _bridge_changed=0
  while IFS='|' read -r _id _path _mode _src; do
    _dst="$MOD/$_path"; mkdir -p "$(dirname "$_dst")" "$_bak/$(dirname "$_path")"
    [ -e "$_dst" ] && cp -pf "$_dst" "$_bak/$_path" 2>/dev/null || true
    cp -f "$_src" "$_dst.new.$$" && chmod "${_mode:-755}" "$_dst.new.$$" && mv -f "$_dst.new.$$" "$_dst" || { rm -rf "$_stage"; rm -f "$_mf"; publish ERROR "$_seq" "$_rel" "APPLY_FAILED_$_path"; return 17; }
    [ "$_path" = bin/railway_bridge.sh ] && _bridge_changed=1
  done <"$_list"
  printf '%s\n' "$_seq" >"$SEQFILE"; printf '%s\n' "$_rel" >"$RELFILE"; chmod 600 "$SEQFILE" "$RELFILE"
  [ "$_bridge_changed" -eq 1 ] && restart_bridge
  ack "$_seq" "$_rel" APPLIED PASS
  publish APPLIED "$_seq" "$_rel" PASS
  rm -rf "$_stage"; rm -f "$_mf"
}
proc_is(){
  _pid="$1"; case "$_pid" in ''|*[!0-9]*) return 1;; esac
  kill -0 "$_pid" 2>/dev/null || return 1
  _cmd="$(tr '\000' ' ' <"/proc/$_pid/cmdline" 2>/dev/null)"
  case "$_cmd" in *"$MOD/bin/remote_updater.sh"*daemon*) return 0;; *) return 1;; esac
}
daemon(){
  _old="$(cat "$PIDFILE" 2>/dev/null)"; proc_is "$_old" && exit 0
  printf '%s\n' "$$" >"$PIDFILE"; chmod 600 "$PIDFILE"
  trap '_p="$(cat "$PIDFILE" 2>/dev/null)"; [ "$_p" = "$$" ] && rm -f "$PIDFILE"' EXIT INT TERM
  while :; do check_once >/dev/null 2>&1 || true; sleep 60; done
}
case "${3:-once}" in once|check) check_once;; daemon) daemon;; status) cat "$STATE" 2>/dev/null;; *) exit 2;; esac
