from pathlib import Path

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Monitoring Edition does not expose any control repository. Keep a tiny class
# for source compatibility with historical files, with zero commands.
r = pkg / 'DjaegerRepository.kt'
r.write_text(r'''package com.djaeger.controlcenter

/** Monitoring Edition compatibility shell. Hardware/control APIs are removed. */
class DjaegerRepository
''')

# Legacy boot receivers from earlier Game Turbo stages are made inert even if
# their source remains in the archive. Build38 also removes receiver declarations
# from the manifest, so there is no boot-triggered behavior.
for b in pkg.glob('*BootReceiver.kt'):
    class_name = b.stem
    b.write_text(f'''package com.djaeger.controlcenter\n\nimport android.content.BroadcastReceiver\nimport android.content.Context\nimport android.content.Intent\n\n/** Monitoring Edition: intentionally inert. */\nclass {class_name} : BroadcastReceiver() {{\n    override fun onReceive(context: Context?, intent: Intent?) = Unit\n}}\n''')

# Static audit over final Kotlin sources: no resource/control mutation APIs.
for f in pkg.glob('*.kt'):
    s = f.read_text()
    for forbidden in [
        'djaeger-ai mode ', 'djaeger-ai policy-intent', 'native_write_plan',
        'settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft ',
        'TYPE_APPLICATION_OVERLAY', 'startForegroundService(', 'startService('
    ]:
        if forbidden in s:
            raise SystemExit(f'Build39 monitoring-only violation in {f.name}: {forbidden}')

print('Build 39 monitoring repository hardening applied')
