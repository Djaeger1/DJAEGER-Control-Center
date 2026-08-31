from pathlib import Path

p = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = p.read_text()

old_decl = '    private val pollRunnable = object : Runnable {'
new_decl = '    private val pollRunnable: Runnable = object : Runnable {'
if old_decl not in s: raise SystemExit('Build23: pollRunnable declaration not found')
s = s.replace(old_decl, new_decl, 1)
old_call = '''                    mainHandler.postDelayed(
                        pollRunnable,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )'''
new_call = '''                    mainHandler.postDelayed(
                        this,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )'''
if old_call not in s: raise SystemExit('Build23: self-reschedule call not found')
s = s.replace(old_call, new_call, 1)
if new_decl not in s or new_call not in s: raise SystemExit('Build23: compile-safe single-flight poll fix not applied')
p.write_text(s)
print('Build 23 compile-safe single-flight HUD poll fix applied')

for num, name in [(24, 'build24_realtime_telemetry_multiwindow_patch.py'), (25, 'build25_shell_literal_compile_fix.py')]:
    patch = Path('../../scripts') / name
    if not patch.is_file(): raise SystemExit(f'Build23: Build{num} patch missing')
    exec(compile(patch.read_text(), str(patch), 'exec'), {'__name__': '__main__'})

main = Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
ms = main.read_text()
legacy = '// CI_BASELINE_MARKER: v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC\n'
if legacy not in ms: ms += '\n' + legacy
main.write_text(ms)

for num, name in [
    (26, 'build26_miui_construction_rewrite.py'),
    (27, 'build27b_miui_visual_phase1_compat.py'),
    (28, 'build28_miui_panel_phase2.py'),
    (29, 'build29_miui_interaction_phase3.py'),
    (30, 'build30_miui_freeform_phase4.py'),
    (31, 'build31_game_session_scene_phase5.py'),
    (32, 'build32_load_bottleneck_phase6.py'),
    (33, 'build33_local_ai_policy_phase7.py'),
    (34, 'build34_policy_handshake_phase9.py'),
    (35, 'build35_verified_outcome_phase10.py'),
    (36, 'build36_stage12_maturity_fix.py'),
]:
    patch = Path('../../scripts') / name
    if not patch.is_file(): raise SystemExit(f'Build23: Build{num} patch missing')
    exec(compile(patch.read_text(), str(patch), 'exec'), {'__name__': '__main__'})
