# Next Control Center build target

Target version: v0.12.1-r11-r78-sync

Required before APK promotion:
- implement r78 coherent reader/model layer
- implement Strategy Composition and Strategy Result pipeline views
- implement Local AI/Gemini fallback distinction
- implement masked manual Key Vault UI against existing typed module interface
- preserve existing HUD/freeform/manual refresh/battery sync behavior
- static scan for forbidden direct hardware/network mutations
- stale/freshness fixture tests using R78_RUNTIME_SAMPLE
- build APK in CI
- inspect build result and artifact before device install

Do not label stable solely because compilation succeeds.
