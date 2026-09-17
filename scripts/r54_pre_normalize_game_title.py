from pathlib import Path
p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()
old='Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)'
new='Text(e.displayName,fontWeight=FontWeight.SemiBold)'
assert old in s, 'GAME title color anchor not found'
s=s.replace(old,new,1)
p.write_text(s)
print('R54_PRE_GAME_TITLE_NORMALIZED=PASS')
