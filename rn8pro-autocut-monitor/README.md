# DJAEGER AutoCut Monitor — Redmi Note 8 Pro

Aplikasi pendamping read-only untuk DJAEGER Charge Manager.

- Notification persistent di pull-down SystemUI.
- Charging: daya yang masuk ke baterai + suhu + SoC.
- Discharging: konsumsi daya baterai + suhu + SoC.
- Bypass: hanya tampil bila modul AutoCut mengirim mode cut yang valid, owner cocok, dan input_suspend=1.
- Tidak menulis sysfs dan tidak mengubah kebijakan cut/resume.

Broadcast contract:
- action: com.djaeger.autocut.STATUS
- package: com.djaeger.autocutmonitor
- string extras: mode, owner, input_suspend
