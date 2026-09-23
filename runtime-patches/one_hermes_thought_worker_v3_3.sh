#!/system/bin/sh
ROOT="$1"
MODDIR="$2"
BIN=$(dirname "$0")
[ -r "$BIN/singleton.sh" ] && { . "$BIN/singleton.sh"; djaeger_singleton_claim hermes_thought_worker; }
[ -r "$BIN/neuron_accounting.sh" ] && . "$BIN/neuron_accounting.sh"

SNAP="$ROOT/runtime/snapshot.env"
FRAME="$ROOT/runtime/frame.env"
PROGRESS="$ROOT/runtime/hermes_thought_progress.env"
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
WORKER_STATE="$ROOT/runtime/hermes_thought_worker_state.env"
ERRLOG="$ROOT/runtime/hermes_thought_worker.err"
WORKER_VERSION=ONE_HERMES_THOUGHT_V3_3
exec 2>>"$ERRLOG"

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
  raw="$1|$2|$3|$4|$5|${6:-BASE}"
  if command -v sha256sum >/dev/null 2>&1; then printf '%s' "$raw" | sha256sum | awk '{print $1}'
  else printf '%s' "$raw" | cksum | awk '{print $1}'; fi
}
# ONE_HERMES_LOCAL_PROGRESS_V1
frame_semantic_class(){
  _ffps=$(num "$(kv FPS_EST "$FRAME")"); [ "$_ffps" != 0 ] || _ffps=$(num "$(kv FPS_EST "$SNAP")")
  _fj=$(num "$(kv JANK_PCT "$FRAME")"); [ "$_fj" != 0 ] || _fj=$(num "$(kv JANK_PCT "$SNAP")")
  _fp95=$(num "$(kv P95_MS "$FRAME")"); [ "$_fp95" != 0 ] || _fp95=$(num "$(kv P95_MS "$SNAP")")
  _fe=$(kv FRAME_EVIDENCE "$FRAME")
  [ -n "$_fe" ] || _fe=$(kv FRAME_EVIDENCE "$SNAP")
  [ "$_fe" = VALID ] || { echo FRAME_UNKNOWN; return; }
  if awk -v f="$_ffps" -v j="$_fj" -v p="$_fp95" 'BEGIN{exit !(p>0&&p<=20&&f>=54&&j>=0&&j<=5)}'; then
    echo FRAME_SMOOTH
  elif awk -v f="$_ffps" -v j="$_fj" -v p="$_fp95" 'BEGIN{exit !((p>=25)||(f>0&&f<50)||(j>15))}'; then
    echo FRAME_BAD
  else
    echo FRAME_TRANSITION
  fi
}

thermal_margin(){
  _s=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  _b=$(num "$(kv BATTERY_TEMP_C "$SNAP")")
  _c=$(num "$(kv CPU_TEMP_C "$SNAP")")
  _g=$(num "$(kv GPU_TEMP_C "$SNAP")")
  awk -v s="$_s" -v b="$_b" -v c="$_c" -v g="$_g" 'BEGIN{
    m=-999
    if(s>0&&s-46>m)m=s-46
    if(b>0&&b-45>m)m=b-45
    if(c>0&&c-75>m)m=c-75
    if(g>0&&g-75>m)m=g-75
    if(m==-999)m=-99
    printf "%.1f",m
  }'
}

hard_thermal_now(){
  _s=$(num "$(kv SKIN_TEMP_C "$SNAP")")
  _b=$(num "$(kv BATTERY_TEMP_C "$SNAP")")
  _c=$(num "$(kv CPU_TEMP_C "$SNAP")")
  _g=$(num "$(kv GPU_TEMP_C "$SNAP")")
  awk -v s="$_s" -v b="$_b" -v c="$_c" -v g="$_g" 'BEGIN{exit !((s>0&&s>=46)||(b>0&&b>=45)||(c>0&&c>=75)||(g>0&&g>=75))}'
}

local_progress_class(){
  _reason="$1"
  _frame_class="$2"
  _margin="$3"
  _now=$(date +%s)
  _prev_at=$(kv AT "$PROGRESS"); case "$_prev_at" in ''|*[!0-9]*) _prev_at=0;; esac
  _prev_reason=$(kv REASON "$PROGRESS")
  _prev_margin=$(kv THERMAL_MARGIN "$PROGRESS"); case "$_prev_margin" in ''|*[!0-9.-]*) _prev_margin="$_margin";; esac
  _age=$((_now-_prev_at)); [ "$_age" -ge 0 ] 2>/dev/null || _age=0

  _pc=STEADY
  case "$_reason" in
    human_comfort_hard_thermal_guard_wait_native_cooling|local_synth_hard_thermal_guard|cloud_takeover_deferred_hard_thermal_guard)
      if ! hard_thermal_now; then
        _pc=THERMAL_GATE_RELEASED
      elif [ "$_prev_reason" = "$_reason" ] && [ "$_age" -ge 45 ] 2>/dev/null; then
        if awk -v n="$_margin" -v p="$_prev_margin" 'BEGIN{exit !(n<=p-0.5)}'; then
          _pc=THERMAL_COOLING
        elif awk -v n="$_margin" -v p="$_prev_margin" 'BEGIN{exit !(n>=p+0.5)}'; then
          _pc=THERMAL_RISING
        else
          _pc=THERMAL_STEADY
        fi
      elif [ "$_prev_reason" = "$_reason" ]; then
        _prev_pc=$(kv PROGRESS_CLASS "$PROGRESS"); [ -n "$_prev_pc" ] || _prev_pc=THERMAL_HOLD_ENTERED
        _pc="$_prev_pc"
      else
        _pc=THERMAL_HOLD_ENTERED
      fi
      ;;
    local_frame_recovery_boost_not_supported_by_history|all_local_comfort_strategies_quarantined|gemini_offline_local_model_no_action_needed|local_synth_no_action_needed|no_safe_takeover_strategy)
      _pc="$_frame_class"
      ;;
    *)
      _pc=STEADY
      ;;
  esac

  if [ "$_prev_reason" != "$_reason" ] || [ "$_age" -ge 45 ] 2>/dev/null; then
    _pt="$PROGRESS.tmp.$$"
    {
      echo "AT=$_now"
      echo "REASON=$(clean "$_reason")"
      echo "THERMAL_MARGIN=$_margin"
      echo "FRAME_CLASS=$_frame_class"
      echo "PROGRESS_CLASS=$_pc"
    } > "$_pt"
    chmod 600 "$_pt"; mv -f "$_pt" "$PROGRESS"
  fi
  echo "$_pc"
}

progress_text(){
  _reason="$1"; _pc="$2"; _base="$3"
  case "$_reason:$_pc" in
    human_comfort_hard_thermal_guard_wait_native_cooling:THERMAL_HOLD_ENTERED|local_synth_hard_thermal_guard:THERMAL_HOLD_ENTERED|cloud_takeover_deferred_hard_thermal_guard:THERMAL_HOLD_ENTERED)
      echo "Hard thermal gate baru aktif, jadi saya menghentikan transaksi hardware baru dan menyerahkan pendinginan awal ke kontrol native. Saya akan menilai perubahan thermal dulu sebelum membuka evaluasi hardware lagi." ;;
    human_comfort_hard_thermal_guard_wait_native_cooling:THERMAL_COOLING|local_synth_hard_thermal_guard:THERMAL_COOLING|cloud_takeover_deferred_hard_thermal_guard:THERMAL_COOLING)
      echo "Pendinginan native mulai mengurangi tekanan thermal, tetapi hard gate masih aktif. Saya tetap menahan write baru; setelah gate benar-benar lepas, frame akan diperiksa lebih dulu sebelum perubahan apa pun." ;;
    human_comfort_hard_thermal_guard_wait_native_cooling:THERMAL_RISING|local_synth_hard_thermal_guard:THERMAL_RISING|cloud_takeover_deferred_hard_thermal_guard:THERMAL_RISING)
      echo "Tekanan thermal masih bergerak naik, jadi menambah intervensi hardware sekarang justru berisiko melawan mekanisme pendinginan native. Saya mempertahankan hold dan tidak membuka kandidat baru." ;;
    human_comfort_hard_thermal_guard_wait_native_cooling:THERMAL_STEADY|local_synth_hard_thermal_guard:THERMAL_STEADY|cloud_takeover_deferred_hard_thermal_guard:THERMAL_STEADY)
      echo "Hard thermal gate masih bertahan dan belum ada penurunan yang cukup bermakna untuk membuka transaksi baru. Saya mempertahankan hold sambil menunggu evidence thermal benar-benar berubah." ;;
    human_comfort_hard_thermal_guard_wait_native_cooling:THERMAL_GATE_RELEASED|local_synth_hard_thermal_guard:THERMAL_GATE_RELEASED|cloud_takeover_deferred_hard_thermal_guard:THERMAL_GATE_RELEASED)
      echo "Pembacaan terbaru sudah keluar dari hard thermal gate. Saya belum langsung mengubah hardware; siklus berikutnya harus mengecek kestabilan frame dan evidence lokal sebelum keputusan baru." ;;

    local_frame_recovery_boost_not_supported_by_history:FRAME_BAD)
      echo "Frame kembali masuk pola buruk, tetapi history yang sudah tervalidasi menunjukkan kondisi buruk bukan kekurangan clock. Saya tetap menahan boost dan memakai episode ini sebagai evidence tambahan untuk mencari penyebab frame pacing yang sebenarnya." ;;
    local_frame_recovery_boost_not_supported_by_history:FRAME_SMOOTH)
      echo "Frame kembali ke pola mulus tanpa perlu boost. Ini memperkuat evidence lokal bahwa menaikkan clock bukan resource yang hilang pada kasus sebelumnya, jadi strategi recovery tetap fokus pada penyebab selain frekuensi." ;;
    local_frame_recovery_boost_not_supported_by_history:FRAME_TRANSITION)
      echo "Frame sedang membaik atau berubah pola, tetapi belum cukup stabil untuk menyimpulkan recovery penuh. Karena boost sebelumnya tidak didukung history, saya tetap mengamati tanpa menaikkan clock." ;;

    all_local_comfort_strategies_quarantined:FRAME_BAD)
      echo "Frame sedang buruk sementara strategi lokal yang relevan masih dikarantina oleh evidence sebelumnya. Saya tidak membuka kembali kandidat yang sudah gagal dan tidak menggantinya dengan boost buta." ;;
    all_local_comfort_strategies_quarantined:FRAME_SMOOTH)
      echo "Frame sekarang berada di pola mulus meski strategi lokal sebelumnya masih dikarantina. Tidak ada alasan untuk memaksa perubahan baru; kondisi ini justru menjadi evidence bahwa menahan intervensi adalah pilihan yang benar saat ini." ;;
    all_local_comfort_strategies_quarantined:FRAME_TRANSITION)
      echo "Frame berada di kondisi transisi sementara strategi lokal lama tetap dikarantina. Saya menunggu pola menjadi jelas sebelum mempertimbangkan strategi baru, bukan mendaur ulang kandidat yang sudah ditolak." ;;

    gemini_offline_local_model_no_action_needed:FRAME_BAD|local_synth_no_action_needed:FRAME_BAD|no_safe_takeover_strategy:FRAME_BAD)
      echo "Frame memburuk, tetapi model lokal belum menemukan tindakan yang didukung evidence dan safety gate. Saya tidak mengubah hardware hanya karena frame turun; causal history tetap menjadi batas agar recovery tidak berubah menjadi boost buta." ;;
    gemini_offline_local_model_no_action_needed:FRAME_SMOOTH|local_synth_no_action_needed:FRAME_SMOOTH|no_safe_takeover_strategy:FRAME_SMOOTH)
      echo "Frame saat ini kembali mulus tanpa perubahan hardware baru. Saya mempertahankan state ini dan menjadikannya evidence tambahan sebelum mencoba efisiensi atau recovery lain." ;;
    *)
      echo "$_base" ;;
  esac
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

worker_state(){
  _ws_stage="$1"; _ws_error="${2:-NONE}"
  _ws_tmp="$WORKER_STATE.tmp.$"
  _ws_active=$(kv HERMES_ACTIVE_SOURCE "$HSTATE"); [ -n "$_ws_active" ] || _ws_active=NONE
  {
    echo "WORKER_VERSION=$WORKER_VERSION"
    echo "PID=$"
    echo "HEARTBEAT_AT=$(date +%s)"
    echo "ACTIVE_SOURCE=$_ws_active"
    echo "LAST_STAGE=$_ws_stage"
    echo "LAST_ERROR=$_ws_error"
    echo "SOURCE_PATH=$0"
  } > "$_ws_tmp"
  chmod 600 "$_ws_tmp"; mv -f "$_ws_tmp" "$WORKER_STATE"
}

while true; do
  worker_state LOOP_START NONE
  active=$(kv HERMES_ACTIVE_SOURCE "$HSTATE")
  worker_state ACTIVE_READ NONE
  case "$active" in HERMES_LOCAL|HERMES_H2|HERMES_CLOUD) :;; *) worker_state WAITING_NON_HERMES NONE; sleep 15; continue;; esac
  pkg=$(kv ACTIVE_PACKAGE "$SNAP"); [ -n "$pkg" ] || pkg=UNKNOWN
  state=$(kv HERMES_LOCAL_STATE "$HSTATE"); [ -n "$state" ] || state=WAITING
  reason=$(kv HERMES_CLOUD_DETAIL "$HSTATE"); [ -n "$reason" ] || reason=no_review_yet
  shadow=$(kv SHADOW_STATE "$SHADOW"); [ -n "$shadow" ] || shadow=WAITING
  exec=$(kv EXECUTOR_STATE "$EXEC"); [ -n "$exec" ] || exec=IDLE
  intent=$(kv INTENT "$HPLAN"); [ -n "$intent" ] || intent=NONE
  worker_state CONTEXT_READY NONE
  frame_class=$(frame_semantic_class)
  thermal_m=$(thermal_margin)
  worker_state EVIDENCE_READY NONE
  progress=$(local_progress_class "$reason" "$frame_class" "$thermal_m")
  worker_state PROGRESS_READY NONE
  d=$(fp "$state" "$reason" "$shadow" "$exec" "$intent" "$progress")
  text=""; origin=LOCAL_REASONING
  [ -r "$KNOW" ] && text=$(awk -F'|' -v x="$d" '$1==x{v=$4}END{print v}' "$KNOW"); text=$(clean "$text")
  [ -n "$text" ] && origin=MEMORY_REUSE
  if [ -z "$text" ]; then
    base_draft=$(clean "$(local_text "$reason")")
    draft=$(clean "$(progress_text "$reason" "$progress" "$base_draft")")
    text="$draft"
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
  worker_state PUBLISHING NONE
  tmp="$OUT.tmp.$"
  { echo "AT=$(date +%s)"; echo "WORKER_VERSION=$WORKER_VERSION"; echo "WORKER_PID=$$"; echo "PACKAGE=$pkg"; echo "FINGERPRINT=$d"; echo "SOURCE=HERMES_H2"; echo "ORIGIN=$origin"; echo "STATUS=$state"; echo "CONFIDENCE=$conf"; echo "REASON=$(clean "$reason")"; echo "PROGRESS=$progress"; echo "FRAME_CLASS=$frame_class"; echo "EVIDENCE=shadow:$shadow,executor:$exec,intent:$intent,progress:$progress"; echo "TEXT=$text"; } > "$tmp"
  chmod 600 "$tmp"
  if mv -f "$tmp" "$OUT"; then worker_state PUBLISHED NONE; else worker_state PUBLISH_FAILED mv_out_failed; rm -f "$tmp"; sleep 15; continue; fi
  bytes=$(wc -c < "$KNOW" 2>/dev/null); case "$bytes" in ''|*[!0-9]*) bytes=0;; esac
  if [ "$bytes" -gt 8388608 ] 2>/dev/null; then tmp="$KNOW.compact.$$"; { echo 'fingerprint|at|reason|text'; tail -n 8000 "$KNOW" | grep -v '^fingerprint|'; } > "$tmp"; chmod 600 "$tmp"; mv -f "$tmp" "$KNOW"; fi
  sleep 15
done
