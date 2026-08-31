from pathlib import Path

p = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = p.read_text()

# Build 22 intentionally schedules the next poll only after the current root/UI
# cycle completes. Avoid referencing the property from its own initializer:
# inside the object-expression Runnable, lambda `this` is the Runnable instance.
old_decl = '    private val pollRunnable = object : Runnable {'
new_decl = '    private val pollRunnable: Runnable = object : Runnable {'
if old_decl not in s:
    raise SystemExit('Build23: pollRunnable declaration not found')
s = s.replace(old_decl, new_decl, 1)

old_call = '''                    mainHandler.postDelayed(
                        pollRunnable,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )'''
new_call = '''                    mainHandler.postDelayed(
                        this,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )'''
if old_call not in s:
    raise SystemExit('Build23: self-reschedule call not found')
s = s.replace(old_call, new_call, 1)

if new_decl not in s or new_call not in s:
    raise SystemExit('Build23: compile-safe single-flight poll fix not applied')

p.write_text(s)
print('Build 23 compile-safe single-flight HUD poll fix applied')

patch24 = Path('../../scripts/build24_realtime_telemetry_multiwindow_patch.py')
if not patch24.is_file():
    raise SystemExit('Build23: Build24 patch missing')
exec(compile(patch24.read_text(), str(patch24), 'exec'), {'__name__': '__main__'})

patch25 = Path('../../scripts/build25_shell_literal_compile_fix.py')
if not patch25.is_file():
    raise SystemExit('Build23: Build25 patch missing')
exec(compile(patch25.read_text(), str(patch25), 'exec'), {'__name__': '__main__'})

main = Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
ms = main.read_text()
legacy = '// CI_BASELINE_MARKER: v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC\n'
if legacy not in ms:
    ms += '\n' + legacy
main.write_text(ms)

for num, name in [
    (26, 'build26_miui_construction_rewrite.py'),
    (27, 'build27_miui_visual_phase1.py'),
    (28, 'build28_miui_panel_phase2.py'),
    (29, 'build29_miui_interaction_phase3.py'),
]:
    patch = Path('../../scripts') / name
    if not patch.is_file():
        raise SystemExit(f'Build23: Build{num} patch missing')
    exec(compile(patch.read_text(), str(patch), 'exec'), {'__name__': '__main__'})
