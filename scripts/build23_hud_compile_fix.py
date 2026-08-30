from pathlib import Path

p = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = p.read_text()
old = '    private val pollRunnable = object : Runnable {'
new = '    private val pollRunnable: Runnable = object : Runnable {'
if old not in s:
    raise SystemExit('Build23: pollRunnable declaration not found')
s = s.replace(old, new, 1)
if new not in s:
    raise SystemExit('Build23: explicit Runnable type not applied')
p.write_text(s)
print('Build 23 HUD compile fix applied')
