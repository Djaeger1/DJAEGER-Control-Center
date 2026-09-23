#!/system/bin/sh
ROOT="$1"
MODDIR="$2"
BIN=$(dirname "$0")
[ -r "$BIN/singleton.sh" ] && { . "$BIN/singleton.sh"; djaeger_singleton_claim hermes_thought_worker; }
[ -r "$BIN/neuron_accounting.sh" ] && . "$BIN/neuron_accounting.sh"

SNAP="$ROOT/runtime/snapshot.env"
HSTATE="$ROOT/runtime/hermes_adapter.env"
HPLAN="$ROOT/policy/hermes_proposal.env"
LOCAL="$ROOT/policy/hermes_local_vote.env"
LEARN="$ROOT/history/learned_envelope.env"
SHADOW="$ROOT/runtime/shadow.env"
EXEC="$ROOT/runtime/execution.env"
NEURON="$ROOT/config/hermes_neuron_live.env"
OUT="$ROOT/runtime/hermes_thought.env"
KNOW="$ROOT/history/hermes_thought_knowledge.tsv"
GUARD="$ROOT/config/hermes_thought_teacher_guard.env"

kv(){ sed -n "s/^$1=//p" "$2" 2>/dev/null | head -n1; }
num(){ case "$1" in ''|*[!0-9.-]*) echo 0;; *) echo "$1";; esac; }
clean(){ printf '%s' "$1" | tr '\r\n\t|' '    ' | tr -cd 'A-Za-z0-9.,:;/%()_+=@ -' | cut -c1-700; }
json_escape(){ LC_ALL=C printf '%s' "$1" | tr -d '\000-\010\013-\037' | tr '\011' ' ' | sed 's/\\/\\\\/g;s/"/\\"/g' | awk 'BEGIN{ORS=""}{if(NR>1)printf "\\n";printf "%s",$0}'; }
config_value(){
  key="$1"
  for f in "$ROOT/config/hermes_cloud.env" "$ROOT/config/identity.env"; do
    [ -r "$f" ] || continue
    sed -n "s/^[[:space:]]*$key[[:space:]]*=[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]]\{4,\}\).*/\1/p" "$f" 2>/dev/null | head -n1
  done | head -n1
}
fp(){
  raw="$1|$2|$3|$4|$5"
  if command -v sha256sum >/dev/null 2>&1; then printf '%s' "$raw" | sha256sum | awk '{print $1}'
  else printf '%s' "$raw" | cksum | awk '{print $1}'; fi
}
local_text(){
  reason="$1"; skin=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  case "$reason" in
    local_frame_recovery_boost_not_supported_by_history)
      echo "Riwayat perangkat menunjukkan frame buruk tidak disebabkan clock yang terlalu rendah; pada pola buruk beban clock dan daya sudah setara atau lebih tinggi daripada pola mulus. Saya menahan boost dan memakai evidence berikutnya untuk mencari penyebab frame pacing tanpa menambah panas." ;;
    all_local_comfort_strategies_quarantined)
      echo "Strategi lokal yang relevan sudah ditolak oleh evidence atau shadow, jadi saya tidak mengulang kandidat yang sama hanya untuk terlihat aktif. Saya mempertahankan kondisi sekarang sampai ada evidence baru yang membuka strategi berbeda." ;;
    human_comfort_hard_thermal_guard_wait_native_cooling|local_synth_hard_thermal_guard|cloud_takeover_deferred_hard_thermal_guard)
      echo "Hard thermal gate sedang aktif, jadi transaksi hardware baru dihentikan dan kontrol thermal native diberi ruang bekerja. Setelah suhu kembali aman, saya menilai ulang frame lebih dulu sebelum mencoba perubahan." ;;
    local_memory_reuses_proven_strategy)
      echo "Saya mengenali pola yang pernah menghasilkan outcome aman dan memakai kembali pengetahuan itu daripada menebak strategi baru. Outcome berikutnya tetap dipakai untuk memperkuat atau membatalkan memory lama." ;;
    local_synth_LOCAL_FRAME_CRITICAL_RECOVERY|local_synth_LOCAL_FRAME_DEGRADED_RECOVERY)
      echo "Frame pacing memburuk dan saya membentuk kandidat dari envelope perangkat yang terukur, bukan preset. Kandidat hanya boleh lanjut bila causal guard, shadow, safety gate, dan readback mendukungnya." ;;
    local_synth_LOCAL_HUMAN_COMFORT_THERMAL_TRIM_GPU|local_synth_LOCAL_POWER_TRIM_GPU|local_synth_LOCAL_POWER_TRIM_BIG|local_synth_LOCAL_POWER_TRIM_LITTLE|local_synth_LOCAL_MATURE_MODEL_EFFICIENCY_PROBE)
      echo "Frame belum memberi alasan untuk mengejar performa lebih tinggi, jadi saya mencari pengurangan beban sekecil mungkin dari envelope yang sudah dipelajari. Penghematan hanya boleh dipertahankan jika frame tetap mulus." ;;
    cloud_requests_observe)
      echo "Sisi Cloud ONE HERMES menilai evidence belum cukup untuk membenarkan perubahan hardware. Saya menyerap keputusan itu sebagai pengetahuan dan melanjutkan observasi lokal tanpa memaksakan kandidat." ;;
    one_hermes_cloud_takeover_ready)
      echo "Pengetahuan lokal belum cukup untuk memilih strategi dengan aman, sehingga sisi Cloud ONE HERMES membantu merumuskan kandidat. Cloud hanya memberi reasoning; keputusan hardware tetap berada pada gate dan executor lokal." ;;
    gemini_offline_local_model_no_action_needed|local_synth_no_action_needed)
      if awk -v s="$skin" 'BEGIN{exit !(s>=42)}'; then
        echo "Model lokal belum menemukan perubahan yang terbukti lebih baik. Walau ada comfort pressure, saya tidak menukar kestabilan frame hanya demi suhu lebih rendah; saya menunggu evidence yang mendukung trim aman."
      else
        echo "Model lokal tidak menemukan keuntungan terukur dari perubahan hardware. Saya mempertahankan state sekarang dan menunggu perubahan evidence, bukan memaksa kandidat dari aturan tetap."
      fi ;;
    no_safe_takeover_strategy)
      echo "Tidak ada strategi takeover yang saat ini lolos evidence dan safety gate. Saya memilih tidak melakukan write baru; tidak menemukan kandidat aman adalah alasan untuk mengamati, bukan menebak." ;;
    neuron_guard_min_interval|restart_guard_no_cloud)
      echo "Cloud sengaja tidak dipanggil karena guard penggunaan neuron masih aktif. ONE HERMES Local tetap melanjutkan reasoning dari memory dan Device Truth, sehingga continuity tidak bergantung pada Cloud." ;;
    *)
      echo "ONE HERMES Local mempertahankan continuity dari Device Truth dan memory yang sudah dipelajari. Belum ada evidence baru yang cukup kuat untuk mengubah hardware, jadi saya menunggu perubahan pola yang benar-benar bermakna." ;;
  esac
}
teacher_needed(){
  # Known semantic classes are already understood by Local and must cost 0 neurons.
  # Cloud teaches only genuinely novel reason classes.
  case "$1" in
    local_frame_recovery_boost_not_supported_by_history|all_local_comfort_strategies_quarantined|human_comfort_hard_thermal_guard_wait_native_cooling|local_synth_hard_thermal_guard|cloud_takeover_deferred_hard_thermal_guard|local_memory_reuses_proven_strategy|local_synth_LOCAL_FRAME_CRITICAL_RECOVERY|local_synth_LOCAL_FRAME_DEGRADED_RECOVERY|local_synth_LOCAL_HUMAN_COMFORT_THERMAL_TRIM_GPU|local_synth_LOCAL_POWER_TRIM_GPU|local_synth_LOCAL_POWER_TRIM_BIG|local_synth_LOCAL_POWER_TRIM_LITTLE|local_synth_LOCAL_MATURE_MODEL_EFFICIENCY_PROBE|cloud_requests_observe|one_hermes_cloud_takeover_ready|gemini_offline_local_model_no_action_needed|local_synth_no_action_needed|no_safe_takeover_strategy|neuron_guard_min_interval|restart_guard_no_cloud|waiting_for_brain_state|non_game_workload|gemini_not_ready_not_failed|gemini_online_observe_or_rate_guard|cloud_health_reachable_auth_unverified|health_endpoint_auth_policy_*)
      return 1 ;;
    *) return 0 ;;
  esac
}
cloud_align(){
  d="$1"; draft="$2"; reason="$3"; now=$(date +%s)
  last=$(kv LAST_SUCCESS_AT "$GUARD"); case "$last" in ''|*[!0-9]*) last=0;; esac
  block=$(kv BLOCK_UNTIL "$GUARD"); case "$block" in ''|*[!0-9]*) block=0;; esac
  nu=$(kv UPDATED_AT "$NEURON"); case "$nu" in ''|*[!0-9]*) nu=0;; esac
  [ "$nu" -gt "$last" ] 2>/dev/null && last="$nu"
  [ "$now" -ge "$block" ] 2>/dev/null || return 1
  [ $((now-last)) -ge 900 ] 2>/dev/null || return 1
  token=$(config_value HERMES_ACCESS_KEY); [ -n "$token" ] || return 1
  endpoint=$(config_value HERMES_ENDPOINT); [ -n "$endpoint" ] || endpoint=$(config_value ENDPOINT); [ -n "$endpoint" ] || endpoint=https://hermes-cloud-djaeger.moclomper.workers.dev
  case "$endpoint" in */v1/chat|*/chat) url="$endpoint";; *) url="$(printf '%s' "$endpoint" | sed 's:/*$::')/v1/chat";; esac
  msg="You are the Cloud cognition of ONE HERMES teaching the Local cognition. Rewrite this Local reasoning into concise natural Indonesian focused on the new insight or decision, not a status template. Do not repeat Overview fields or raw telemetry unless essential. Never invent evidence. Maximum two short sentences. Return exactly THOUGHT=. Reason=$reason Draft=$draft"
  sys="You are ONE HERMES Cloud acting only as semantic teacher for ONE HERMES Local. The result becomes reusable local knowledge. No hardware authority."
  req="$ROOT/runtime/.thought_req.$$"; resp="$ROOT/runtime/.thought_resp.$$"; cfg="$ROOT/runtime/.thought_curl.$$"
  printf '{"mode":"FAST","task":"djaeger_thought_teacher","message":"%s","prompt":"%s","system":"%s","fallback":false,"max_tokens":180,"temperature":0.2}' "$(json_escape "$msg")" "$(json_escape "$msg")" "$(json_escape "$sys")" > "$req"
  printf 'header = "Authorization: Bearer %s"\n' "$token" > "$cfg"; chmod 600 "$req" "$cfg"; unset token
  http=$(curl --http1.1 --connect-timeout 4 -m 12 -sS -o "$resp" -w '%{http_code}' -K "$cfg" -H 'Content-Type: application/json' --data-binary "@$req" "$url" 2>/dev/null); rm -f "$cfg"
  if [ "$http" = 200 ] && [ -r "$resp" ]; then
    command -v neuron_record_success >/dev/null 2>&1 && neuron_record_success FAST "$req" "$resp"
    payload=$(tr '\n' ' ' < "$resp" | sed -n 's/.*"text"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed 's/\\n/ /g;s/\\r//g')
    if [ -z "$payload" ]; then
      payload=$(tr '\n' ' ' < "$resp" | sed -n 's/.*"content"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed 's/\\n/ /g;s/\\r//g')
    fi
    taught=$(printf '%s\n' "$payload" | sed 's/^.*THOUGHT=//')
    [ -n "$taught" ] || taught="$payload"
    taught=$(clean "$taught")
    if [ -n "$taught" ]; then
      { echo "LAST_SUCCESS_AT=$now"; echo "BLOCK_UNTIL=0"; echo "LAST_HTTP=200"; } > "$GUARD.tmp.$$"; chmod 600 "$GUARD.tmp.$$"; mv -f "$GUARD.tmp.$$" "$GUARD"
      rm -f "$req" "$resp"; printf '%s' "$taught"; return 0
    fi
  fi
  delay=300; case "$http" in 429) delay=1800;; 401|403) delay=21600;; esac
  old=$(kv LAST_SUCCESS_AT "$GUARD"); case "$old" in ''|*[!0-9]*) old=0;; esac
  { echo "LAST_SUCCESS_AT=$old"; echo "BLOCK_UNTIL=$((now+delay))"; echo "LAST_HTTP=$http"; } > "$GUARD.tmp.$$"; chmod 600 "$GUARD.tmp.$$"; mv -f "$GUARD.tmp.$$" "$GUARD"
  rm -f "$req" "$resp"; return 1
}

while true; do
  active=$(kv HERMES_ACTIVE_SOURCE "$HSTATE")
  case "$active" in HERMES_LOCAL|HERMES_H2|HERMES_CLOUD) :;; *) sleep 15; continue;; esac
  pkg=$(kv ACTIVE_PACKAGE "$SNAP"); [ -n "$pkg" ] || pkg=UNKNOWN
  state=$(kv HERMES_LOCAL_STATE "$HSTATE"); [ -n "$state" ] || state=WAITING
  reason=$(kv HERMES_CLOUD_DETAIL "$HSTATE"); [ -n "$reason" ] || reason=no_review_yet
  shadow=$(kv SHADOW_STATE "$SHADOW"); [ -n "$shadow" ] || shadow=WAITING
  exec=$(kv EXECUTOR_STATE "$EXEC"); [ -n "$exec" ] || exec=IDLE
  intent=$(kv INTENT "$HPLAN"); [ -n "$intent" ] || intent=NONE
  d=$(fp "$state" "$reason" "$shadow" "$exec" "$intent")
  text=""; origin=LOCAL_REASONING
  [ -r "$KNOW" ] && text=$(awk -F'|' -v x="$d" '$1==x{v=$4}END{print v}' "$KNOW"); text=$(clean "$text")
  [ -n "$text" ] && origin=MEMORY_REUSE
  if [ -z "$text" ]; then
    draft=$(clean "$(local_text "$reason")"); text="$draft"
    if teacher_needed "$reason"; then
      taught=$(cloud_align "$d" "$draft" "$reason" 2>/dev/null); taught=$(clean "$taught")
      if [ -n "$taught" ]; then
        text="$taught"; origin=CLOUD_TAUGHT
        [ -r "$KNOW" ] || printf 'fingerprint|at|reason|text\n' > "$KNOW"
        printf '%s|%s|%s|%s\n' "$d" "$(date +%s)" "$(clean "$reason")" "$text" >> "$KNOW"; chmod 600 "$KNOW"
      fi
    fi
  fi
  conf=$(kv CONFIDENCE "$LOCAL"); case "$conf" in ''|*[!0-9]*) conf=$(kv CONFIDENCE "$LEARN");; esac; case "$conf" in ''|*[!0-9]*) conf=0;; esac
  tmp="$OUT.tmp.$$"
  { echo "AT=$(date +%s)"; echo "PACKAGE=$pkg"; echo "FINGERPRINT=$d"; echo "SOURCE=HERMES_H2"; echo "ORIGIN=$origin"; echo "STATUS=$state"; echo "CONFIDENCE=$conf"; echo "REASON=$(clean "$reason")"; echo "EVIDENCE=shadow:$shadow,executor:$exec,intent:$intent"; echo "TEXT=$text"; } > "$tmp"
  chmod 600 "$tmp"; mv -f "$tmp" "$OUT"
  bytes=$(wc -c < "$KNOW" 2>/dev/null); case "$bytes" in ''|*[!0-9]*) bytes=0;; esac
  if [ "$bytes" -gt 8388608 ] 2>/dev/null; then tmp="$KNOW.compact.$$"; { echo 'fingerprint|at|reason|text'; tail -n 8000 "$KNOW" | grep -v '^fingerprint|'; } > "$tmp"; chmod 600 "$tmp"; mv -f "$tmp" "$KNOW"; fi
  sleep 15
done
