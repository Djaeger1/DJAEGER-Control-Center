from pathlib import Path

p = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = p.read_text()

# Shell variables embedded inside Kotlin strings must not be interpreted as
# Kotlin templates. Render a literal '$' through Kotlin's ${'$'} escape.
replacements = {
    '$z/type': "${'$'}z/type",
    '$z/temp': "${'$'}z/temp",
    '$n\\\"': "${'$'}n\\\"",
    '$t\\\"': "${'$'}t\\\"",
    '$L\\\"': "${'$'}L\\\"",
    '$?': "${'$'}?",
}
for old, new in replacements.items():
    s = s.replace(old, new)

# Explicit checks for the lines that previously failed Kotlin compilation.
if '$z/type' in s or '$z/temp' in s:
    raise SystemExit('Build25: unescaped thermal shell variable remains')
if 'dumpsys SurfaceFlinger --latency \\\"$L\\\"' in s:
    raise SystemExit('Build25: unescaped layer shell variable remains')

p.write_text(s)
print('Build 25 Kotlin shell-literal compile fix applied')
