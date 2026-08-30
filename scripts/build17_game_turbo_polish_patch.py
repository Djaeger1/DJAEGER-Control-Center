from pathlib import Path

# Build 17: behavior polish for the Game Turbo-style HUD without changing control authority.
g=Path('app/build.gradle.kts');s=g.read_text().replace('versionCode = 17','versionCode = 18').replace('versionName = "0.8.0-rc-game-turbo-experience"','versionName = "0.8.1-rc-game-turbo-polished"');g.write_text(s)

p=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt');s=p.read_text()
s=s.replace('private var state=0;private var game=false;private var data=Data();private var scale=1f','private var state=0;private var game=false;private var suppressed=false;private var data=Data();private var scale=1f')
s=s.replace('if(active&&Settings.canDrawOverlays(this@DjaegerHudService)){if(!game){game=true;state=0;show()}else refresh()}else if(game){game=false;hide()}','if(active&&Settings.canDrawOverlays(this@DjaegerHudService)){if(!suppressed){if(!game){game=true;state=0;show()}else refresh()}}else{suppressed=false;if(game){game=false;hide()}}')
s=s.replace('drag(x);wm.addView(x,lp)}','drag(x);x.scaleX=scale;x.scaleY=scale;wm.addView(x,lp)}')
s=s.replace('head.addView(action("×"){game=false;hide()})','head.addView(action("×"){suppressed=true;game=false;hide()})')
p.write_text(s)

m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt');s=m.read_text().replace('GAMING TURBO • v0.8.0 RC • GAME TURBO EXPERIENCE • REALTIME 1s','GAMING TURBO • v0.8.1 RC • GAME TURBO POLISHED • REALTIME 1s').replace('DJAEGER v0.8.0 RC','DJAEGER v0.8.1 RC');m.write_text(s)
