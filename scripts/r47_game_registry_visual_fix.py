from pathlib import Path

main = Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
m = main.read_text()

# The GAME REGISTRY surface uses a custom dark background, so do not inherit
# an ambiguous/default Material content color. Keep the established green
# section title and readable light entry names explicitly.
old_title = 'Text("GAME REGISTRY • MANUAL",fontWeight=FontWeight.Bold)'
new_title = 'Text("GAME REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)'
assert old_title in m, 'Game Registry title anchor not found'
m = m.replace(old_title, new_title, 1)

old_name = 'Text(e.displayName,fontWeight=FontWeight.SemiBold)'
new_name = 'Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)'
assert old_name in m, 'Game Registry entry-name anchor not found'
m = m.replace(old_name, new_name, 1)

main.write_text(m)

M = main.read_text()
assert 'Text("GAME REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)' in M
assert 'Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)' in M
assert 'Text("GAME REGISTRY • MANUAL",fontWeight=FontWeight.Bold)' not in M
assert 'Text(e.displayName,fontWeight=FontWeight.SemiBold)' not in M

print('GAME_REGISTRY_VISUAL_FIX=PASS')
print('TITLE_COLOR=GREEN_EXPLICIT')
print('ENTRY_NAME_COLOR=ON_SURFACE_EXPLICIT')
print('REGISTRY_LOGIC=UNCHANGED')
