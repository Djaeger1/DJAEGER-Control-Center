from pathlib import Path

g=Path('app/build.gradle.kts');s=g.read_text().replace('versionCode = 18','versionCode = 19').replace('versionName = "0.8.1-rc-game-turbo-polished"','versionName = "0.8.2-rc-game-turbo-compile-fix"');g.write_text(s)

p=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt');s=p.read_text()
# Kotlin parser hardening: avoid return/string token ambiguity.
s=s.replace('val x=n(i)?:return"--";return String.format', 'val x=n(i) ?: return "--"; return String.format')
# Avoid shadowing the WindowManager.LayoutParams.x property with the overlay View variable.
s=s.replace('val x=v?:return;lp=WindowManager.LayoutParams(', 'val view=v?:return;lp=WindowManager.LayoutParams(')
s=s.replace(').apply{gravity=Gravity.TOP or Gravity.END;x=dp(8);y=dp(155)};drag(x);x.scaleX=scale;x.scaleY=scale;wm.addView(x,lp)}', ').apply{gravity=Gravity.TOP or Gravity.END;this.x=dp(8);this.y=dp(155)};drag(view);view.scaleX=scale;view.scaleY=scale;wm.addView(view,lp)}')
# Avoid shadowing root(command) with the expanded-panel root view.
s=s.replace('private fun expanded():View{val root=LinearLayout(this).apply{', 'private fun expanded():View{val box=LinearLayout(this).apply{')
s=s.replace('root.addView(head);val met=', 'box.addView(head);val met=')
s=s.replace('root.addView(met,LinearLayout.LayoutParams', 'box.addView(met,LinearLayout.LayoutParams')
s=s.replace('root.addView(TextView(this).apply{text="${data.game}  •  PLAYING"', 'box.addView(TextView(this).apply{text="${data.game}  •  PLAYING"')
s=s.replace('};root.addView(modes);root.addView(TextView(this).apply{text="↔  RESIZE MANUAL"', '};box.addView(modes);box.addView(TextView(this).apply{text="↔  RESIZE MANUAL"')
s=s.replace('v?.scaleY=scale}});return root}', 'v?.scaleY=scale}});return box}')
p.write_text(s)

m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt');s=m.read_text().replace('GAMING TURBO • v0.8.1 RC • GAME TURBO POLISHED • REALTIME 1s','GAMING TURBO • v0.8.2 RC • GAME TURBO • REALTIME 1s').replace('DJAEGER v0.8.1 RC','DJAEGER v0.8.2 RC');m.write_text(s)
