#!/usr/bin/env python3
from pathlib import Path
m=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=m.read_text()
old='val badge=when(src){"GEMINI"->"✦ GEMINI • $status";"GROQ"->"◇ GROQ • $status";"LOCAL_AI"->"◆ LOCAL AI • $status";else->"-"}'
new='''val badge=when(src){\n        "GEMINI"->"✦ GEMINI • $status"\n        "GROQ"->"◇ GROQ • $status"\n        "LOCAL_AI"->"◆ LOCAL AI • $status"\n        else->"-"\n    }'''
assert old in s, 'R28 prepatch badge source anchor missing'
s=s.replace(old,new,1)
m.write_text(s)
print('R28_BADGE_PREPATCH=PASS')
