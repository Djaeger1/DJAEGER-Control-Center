from pathlib import Path

p=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s=p.read_text()
s=s.replace('v0.8.3', 'v0.9.0')
# Runtime parser compatibility: normalize shell-quoted values and accept the module's canonical active=1 signal.
s=s.replace('val value = line.substring(idx + 1).trim()', 'val value = line.substring(idx + 1).trim().trim(\'\\\"\', \'\\\'\')')
s=s.replace('return status.windowActive || status.sessionActive || status.gameActive', 'return status.activeFlag || status.windowActive || status.sessionActive || status.gameActive')
# Add activeFlag if the current state model exposes the parsed map/status object.
s=s.replace('val gameActive: Boolean,', 'val gameActive: Boolean,\n        val activeFlag: Boolean,')
s=s.replace('gameActive = boolValue(map["game_active"]),', 'gameActive = boolValue(map["game_active"]),\n            activeFlag = boolValue(map["active"]),')
p.write_text(s)

# MainActivity starts the monitor as soon as Control Center is opened and overlay permission exists.
m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=m.read_text().replace('v0.8.3 RC • GAME TURBO','v0.9.0 RC • MIUI GAME TURBO EXPERIENCE')
needle='super.onCreate(savedInstanceState)'
insert='''super.onCreate(savedInstanceState)\n        if (android.provider.Settings.canDrawOverlays(this)) {\n            val monitor = android.content.Intent(this, DjaegerHudService::class.java)\n            try {\n                if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(monitor) else startService(monitor)\n            } catch (_: Exception) {}\n        }'''
if needle in s:s=s.replace(needle,insert,1)
m.write_text(s)

# More authority for reliable lifecycle: package usage access is allowed as a fallback detector.
mf=Path('app/src/main/AndroidManifest.xml')
s=mf.read_text()
if 'android.permission.PACKAGE_USAGE_STATS' not in s:
    s=s.replace('<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />','<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />\n    <uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" tools:ignore="ProtectedPermissions" />')
mf.write_text(s)

# Version metadata.
g=Path('app/build.gradle.kts')
s=g.read_text().replace('versionCode = 20','versionCode = 21').replace('versionName = "0.8.3-rc-game-turbo"','versionName = "0.9.0-rc-miui-game-turbo"')
g.write_text(s)
