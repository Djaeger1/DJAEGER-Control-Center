from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); rd=reader.read_text(); b=build.read_text()

def fun_block(src,name):
    key='@Composable fun '+name
    start=src.index(key); op=src.index('{',start)
    depth=0; i=op; in_str=False; esc=False
    while i<len(src):
        c=src[i]
        if in_str:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': in_str=False
        else:
            if c=='"': in_str=True
            elif c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0: return start,i+1,src[start:i+1]
        i+=1
    raise RuntimeError('unterminated '+name)

# Matched-pair identity: module 129653 + Control Center 12263.
b=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12263',b,count=1)
b=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r2-dualreg3-manualapp1-hcc1-feedback4-ui1-matched"',b,count=1)
m=m.replace('syncModule=="129652"','syncModule=="129653"')
m=m.replace('syncCc=="12262"','syncCc=="12263"')
m=m.replace('VC129652 / VC12262','VC129653 / VC12263')
rd=rd.replace("MODULE_VERSION_CODE='129652'","MODULE_VERSION_CODE='129653'")
rd=rd.replace("CONTROL_CENTER_VERSION_CODE='12262'","CONTROL_CENTER_VERSION_CODE='12263'")

# Accessible title colors requested by owner: GAME pink, APP light blue.
color_anchor='private val Bg=Color(0xFF090B10); private val Card=Color(0xFF121722); private val Green=Color(0xFF43E38A); private val Muted=Color(0xFF98A2B3); private val Amber=Color(0xFFFFC857); private val Red=Color(0xFFFF6B6B)'
assert color_anchor in m
m=m.replace(color_anchor,color_anchor+'; private val GameTitlePink=Color(0xFFFF8CC6); private val AppTitleLightBlue=Color(0xFF7DD3FC)',1)

gs,ge,gblock=fun_block(m,'GameRegistryCard')
old='Text(e.displayName,fontWeight=FontWeight.SemiBold)'
assert old in gblock
gblock=gblock.replace(old,'Text(e.displayName,color=GameTitlePink,fontWeight=FontWeight.SemiBold)',1)
m=m[:gs]+gblock+m[ge:]
as_,ae,ablock=fun_block(m,'AppRegistryListCard')
assert old in ablock
ablock=ablock.replace(old,'Text(e.displayName,color=AppTitleLightBlue,fontWeight=FontWeight.SemiBold)',1)
m=m[:as_]+ablock+m[ae:]

# Parse the HCC1 preset from the mapped cc_snapshot section. Backend truth is authoritative.
helper_anchor='private fun stat2(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f%s".format(values.average(),values.maxOrNull()?:0.0,unit)\n'
assert helper_anchor in m
helpers=r'''private fun hccPresetFromBlock(block:String):String{
    block.lineSequence().forEach{line->
        val x=line.trim()
        if(x.startsWith("COMFORT_PRESET=")||x.startsWith("HUMAN_COMFORT_PRESET=")){
            return x.substringAfter('=').trim().trim('\'', '"').uppercase()
        }
    }
    return ""
}
@Composable private fun HccPresetButton(label:String,selected:Boolean,enabled:Boolean,onClick:()->Unit,modifier:Modifier=Modifier){
    if(selected) Button(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
    else OutlinedButton(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
}
@Composable private fun HccFeedbackButton(label:String,flash:Boolean,enabled:Boolean,onClick:()->Unit,modifier:Modifier=Modifier){
    if(flash) Button(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
    else OutlinedButton(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
}
'''
m=m.replace(helper_anchor,helper_anchor+helpers,1)

# Local pending state prevents the old snapshot from visually undoing a just-confirmed preset.
status_anchor='    var comfortCommandStatus by remember{mutableStateOf("HCC1 controls ready. Current truth is read from cc_snapshot.")}\n'
assert status_anchor in m
m=m.replace(status_anchor,status_anchor+'    var requestedComfortPreset by remember{mutableStateOf<String?>(null)}\n    var feedbackFlash by remember{mutableStateOf<String?>(null)}\n',1)

logic_anchor='    val supported=s.moduleVersion.contains("12.9.50");'
assert logic_anchor in m
logic=r'''    val publishedComfortPreset=hccPresetFromBlock(s.hermesHumanComfort)
    val visibleComfortPreset=requestedComfortPreset ?: publishedComfortPreset.ifBlank{"COOL_STABLE"}
    LaunchedEffect(s.hermesHumanComfort,requestedComfortPreset){
        val req=requestedComfortPreset
        if(req!=null && publishedComfortPreset==req) requestedComfortPreset=null
    }
    LaunchedEffect(requestedComfortPreset){
        val req=requestedComfortPreset
        if(req!=null){delay(5000);if(requestedComfortPreset==req)requestedComfortPreset=null}
    }
    LaunchedEffect(feedbackFlash){
        val f=feedbackFlash
        if(f!=null){delay(900);if(feedbackFlash==f)feedbackFlash=null}
    }
'''
m=m.replace(logic_anchor,logic+logic_anchor,1)

repls={
'Button(onClick={bridgeOp="COMFORT_COOL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("COOL STABLE",style=MaterialTheme.typography.labelSmall)}':'HccPresetButton("COOL STABLE",visibleComfortPreset=="COOL_STABLE",bridgeOp==null,{requestedComfortPreset="COOL_STABLE";bridgeOp="COMFORT_COOL"},Modifier.weight(1f))',
'OutlinedButton(onClick={bridgeOp="COMFORT_BASELINE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("BASELINE",style=MaterialTheme.typography.labelSmall)}':'HccPresetButton("BASELINE",visibleComfortPreset=="BASELINE",bridgeOp==null,{requestedComfortPreset="BASELINE";bridgeOp="COMFORT_BASELINE"},Modifier.weight(1f))',
'OutlinedButton(onClick={bridgeOp="COMFORT_RESET"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RESET",style=MaterialTheme.typography.labelSmall)}':'OutlinedButton(onClick={requestedComfortPreset="COOL_STABLE";bridgeOp="COMFORT_RESET"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RESET",style=MaterialTheme.typography.labelSmall)}',
'OutlinedButton(onClick={bridgeOp="FEEDBACK_VERY_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SANGAT NYAMAN",style=MaterialTheme.typography.labelSmall)}':'HccFeedbackButton("SANGAT NYAMAN",feedbackFlash=="VERY_COMFORTABLE",bridgeOp==null,{feedbackFlash="VERY_COMFORTABLE";bridgeOp="FEEDBACK_VERY_COMFORTABLE"},Modifier.weight(1f))',
'OutlinedButton(onClick={bridgeOp="FEEDBACK_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NYAMAN",style=MaterialTheme.typography.labelSmall)}':'HccFeedbackButton("NYAMAN",feedbackFlash=="COMFORTABLE",bridgeOp==null,{feedbackFlash="COMFORTABLE";bridgeOp="FEEDBACK_COMFORTABLE"},Modifier.weight(1f))',
'OutlinedButton(onClick={bridgeOp="FEEDBACK_LESS_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KURANG NYAMAN",style=MaterialTheme.typography.labelSmall)}':'HccFeedbackButton("KURANG NYAMAN",feedbackFlash=="LESS_COMFORTABLE",bridgeOp==null,{feedbackFlash="LESS_COMFORTABLE";bridgeOp="FEEDBACK_LESS_COMFORTABLE"},Modifier.weight(1f))',
'OutlinedButton(onClick={bridgeOp="FEEDBACK_UNCOMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("TIDAK NYAMAN",style=MaterialTheme.typography.labelSmall)}':'HccFeedbackButton("TIDAK NYAMAN",feedbackFlash=="UNCOMFORTABLE",bridgeOp==null,{feedbackFlash="UNCOMFORTABLE";bridgeOp="FEEDBACK_UNCOMFORTABLE"},Modifier.weight(1f))',
}
for oldv,newv in repls.items():
    assert oldv in m, 'missing HCC control anchor: '+oldv[:50]
    m=m.replace(oldv,newv,1)

main.write_text(m); reader.write_text(rd); build.write_text(b)

# Final gates: exact requested UI and matched-pair contract.
M=main.read_text(); RD=reader.read_text(); B=build.read_text()
assert 'versionCode = 12263' in B and 'hcc1-feedback4-ui1-matched' in B
assert 'syncModule=="129653"' in M and 'syncCc=="12263"' in M
assert "MODULE_VERSION_CODE='129653'" in RD and "CONTROL_CENTER_VERSION_CODE='12263'" in RD
assert 'color=GameTitlePink' in M and 'GameTitlePink=Color(0xFFFF8CC6)' in M
assert 'color=AppTitleLightBlue' in M and 'AppTitleLightBlue=Color(0xFF7DD3FC)' in M
assert 'visibleComfortPreset=="BASELINE"' in M and 'visibleComfortPreset=="COOL_STABLE"' in M
assert 'requestedComfortPreset="COOL_STABLE";bridgeOp="COMFORT_RESET"' in M
assert M.count('HccFeedbackButton(')>=5
assert 'delay(900)' in M
assert 'GAME REGISTRY • MANUAL' in M and 'APP REGISTRY • MANUAL' in M
print('HCC1_FEEDBACK4_UI1=PASS')
print('PAIR=VC129653+VC12263')
print('PRESET_SELECTED_STATE=BACKEND_CC_SNAPSHOT_WITH_PENDING_ACK')
print('RESET_DEFAULT=COOL_STABLE')
print('FEEDBACK_UI=TRANSIENT_900MS')
print('GAME_TITLE=PINK_FF8CC6')
print('APP_TITLE=LIGHT_BLUE_7DD3FC')
print('AUTHORITY_CHANGE=NONE')
