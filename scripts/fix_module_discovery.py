#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("control-center-r2")
READER = ROOT / "app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt"
MAPPER = ROOT / "app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt"

rd = READER.read_text()
if "__MODULE_IDENTITY__" not in rd:
    marker = '            """.trimIndent()'
    pos = rd.find(marker, rd.find("__CONTROL_CENTER_SYNC__"))
    if pos < 0:
        raise SystemExit("MODULE_IDENTITY_READER_ANCHOR_NOT_FOUND")
    block = '''                printf '\\n__MODULE_IDENTITY__\\n'
                if [ -d /data/adb/modules/djaeger_game_stabilizer ]; then
                  echo 'INSTALLED=1'
                  sed -n 's/^versionCode=//p' /data/adb/modules/djaeger_game_stabilizer/module.prop 2>/dev/null | head -n 1 | sed 's/^/VERSION_CODE=/'
                  sed -n 's/^version=//p' /data/adb/modules/djaeger_game_stabilizer/module.prop 2>/dev/null | head -n 1 | sed 's/^/VERSION=/'
                else
                  echo 'INSTALLED=0'
                  echo 'VERSION_CODE=0'
                  echo 'VERSION=unknown'
                fi
'''
    rd = rd[:pos] + block + rd[pos:]
    READER.write_text(rd)

rm = MAPPER.read_text()
if "moduleIdentity = AtomicSnapshot.keyValues" not in rm:
    old = '''        val installedText = s["INSTALLED"].orEmpty().trim()
        val installed = installedText == "1" || installedText.equals("YES", true) || installedText.equals("TRUE", true)
        val runtime = AtomicSnapshot.keyValues(s["RUNTIME"].orEmpty())'''
    new = '''        val installedText = s["INSTALLED"].orEmpty().trim()
        val moduleIdentity = AtomicSnapshot.keyValues(s["MODULE_IDENTITY"].orEmpty())
        val fallbackInstalled = moduleIdentity["INSTALLED"]?.let { v ->
            v == "1" || v.equals("YES", true) || v.equals("TRUE", true)
        } ?: false
        val installed = installedText == "1" || installedText.equals("YES", true) || installedText.equals("TRUE", true) || fallbackInstalled
        val runtime = AtomicSnapshot.keyValues(s["RUNTIME"].orEmpty())'''
    if old not in rm:
        raise SystemExit("MODULE_IDENTITY_MAPPER_ANCHOR_NOT_FOUND")
    rm = rm.replace(old, new, 1)
    oldv = 'moduleVersion = s["VERSION"].orEmpty().trim().ifBlank { "unknown" },'
    newv = 'moduleVersion = s["VERSION"].orEmpty().trim().ifBlank { moduleIdentity["VERSION"].orEmpty().ifBlank { "unknown" } },'
    if oldv not in rm:
        raise SystemExit("MODULE_IDENTITY_VERSION_ANCHOR_NOT_FOUND")
    rm = rm.replace(oldv, newv, 1)
    MAPPER.write_text(rm)

rd = READER.read_text()
rm = MAPPER.read_text()
assert "__MODULE_IDENTITY__" in rd
assert "moduleIdentity = AtomicSnapshot.keyValues" in rm
assert "fallbackInstalled" in rm
print("MODULE_IDENTITY_FALLBACK=PASS")
print("SINGLE_ROOT_READER=PRESERVED")
