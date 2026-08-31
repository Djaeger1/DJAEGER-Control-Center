from pathlib import Path
p=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt')
s=p.read_text()
old='''        val power=if(current!=0L&&voltage>0L)kotlin.math.abs(current.toDouble()*voltage.toDouble())/1_000_000_000.0 else csv.powerMw
        val tel=csv.copy(
            cpuT=if(cpuLive>0)cpuLive else csv.cpuT,'''
new='''        val power=if(current!=0L&&voltage>0L)kotlin.math.abs(current.toDouble()*voltage.toDouble())/1_000_000_000.0 else csv.powerMw
        val now=System.currentTimeMillis()/1000
        val hasLive=cpuLive>0||gpuLive>0||skinLive>0||batLive>0||little>0||big>0||gpu>0
        val tel=csv.copy(
            epoch=if(csv.epoch>0)csv.epoch else if(hasLive)now else 0,
            cpuT=if(cpuLive>0)cpuLive else csv.cpuT,'''
if old not in s: raise SystemExit('Build47 telemetry timestamp anchor missing')
s=s.replace(old,new,1)
s=s.replace('''        val now=System.currentTimeMillis()/1000;val age=now-tel.epoch
''','''        val age=now-tel.epoch
''',1)
p.write_text(s)
if 'epoch=if(csv.epoch>0)csv.epoch else if(hasLive)now else 0' not in s: raise SystemExit('Build47 timestamp invariant failed')
print('Build47 applied: direct read-only telemetry receives a real sample timestamp')