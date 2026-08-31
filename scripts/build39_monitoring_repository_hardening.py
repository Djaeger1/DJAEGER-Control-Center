from pathlib import Path

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Monitoring Edition does not expose any control repository. Keep a tiny class
# for binary/source compatibility with historical files, with zero commands.
r = pkg / 'DjaegerRepository.kt'
r.write_text(r'''package com.djaeger.controlcenter

/** Monitoring Edition compatibility shell. Hardware/control APIs are removed. */
class DjaegerRepository
''')

# A legacy boot receiver may exist in the old source archive. Make it inert even
# though Build38 removes it from the manifest, preventing accidental service start
# if a stale manifest is ever merged.
b = pkg / 'BootReceiver.kt'
if b.exists():
    b.write_text(r'''package com.djaeger.controlcenter

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Monitoring Edition: intentionally inert. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) = Unit
}
''')

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
