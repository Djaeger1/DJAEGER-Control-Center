from pathlib import Path

p = Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s = p.read_text()

old = '''            for z in /sys/class/thermal/thermal_zone*; do
              [ -r "$z/type" ] || continue; [ -r "$z/temp" ] || continue
              n=$(cat "$z/type" 2>/dev/null); t=$(cat "$z/temp" 2>/dev/null)
              case "$n" in cpu-*-usr|cpuss-*-usr|gpuss-*-usr|skin*|quiet-therm-usr) printf '%s=%s\\n' "$n" "$t";; esac
            done'''

new = '''            for z in /sys/class/thermal/thermal_zone*; do
              [ -r "${'$'}z/type" ] || continue; [ -r "${'$'}z/temp" ] || continue
              n=$(cat "${'$'}z/type" 2>/dev/null); t=$(cat "${'$'}z/temp" 2>/dev/null)
              case "${'$'}n" in cpu-*-usr|cpuss-*-usr|gpuss-*-usr|skin*|quiet-therm-usr) printf '%s=%s\\n' "${'$'}n" "${'$'}t";; esac
            done'''

if old not in s:
    raise SystemExit('Build40: thermal shell snippet anchor missing')
s = s.replace(old, new, 1)

# No unescaped shell identifier interpolation is allowed inside MainActivity.
for token in ('$z', '$n', '$t'):
    if token in s:
        raise SystemExit(f'Build40: unescaped shell token remains: {token}')

p.write_text(s)
print('Build 40 Kotlin shell literal fix applied')
