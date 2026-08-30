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

# Chain the next maturity patch from the repository scripts directory. Keeping
# this here makes the existing workflow execute Build24 without weakening any
# of the already-proven Build22/23 assertions or requiring device-side testing.
patch24 = Path('../../scripts/build24_realtime_telemetry_multiwindow_patch.py')
if not patch24.is_file():
    raise SystemExit('Build23: Build24 patch missing')
exec(compile(patch24.read_text(), str(patch24), 'exec'), {'__name__': '__main__'})
