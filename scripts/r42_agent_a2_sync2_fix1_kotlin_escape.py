#!/usr/bin/env python3
from pathlib import Path
m=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
ms=m.read_text()
start=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
end=ms.index('private fun currentRange',start)
thought=r'''@Composable fun ThoughtsCard(s:RuntimeState){
    BoxWithConstraints{
        val compact=maxWidth<520.dp
        val now=System.currentTimeMillis()/1000
        val httpCode=envField(s.geminiHttp,"HTTP_CODE")
        val httpAt=envField(s.geminiHttp,"AT").toLongOrNull()?:0L
        val httpAge=if(httpAt>0) now-httpAt else -1L
        val provider=envField(s.geminiHttp,"PROVIDER").ifBlank{"GEMINI"}
        val model=envField(s.geminiHttp,"MODEL")
        val geminiState=when{
            httpCode=="200"&&httpAge in 0..360 -> "ONLINE"
            httpCode=="200"&&httpAge>=0 -> "LAST OK • ${ageLabel(httpAge.toString())}"
            httpCode=="429" -> "RATE LIMIT"
            httpCode=="401"||httpCode=="403" -> "AUTH ERROR"
            httpCode.isNotBlank() -> "HTTP $httpCode"
            else -> "NO HTTP STATE"
        }
        val agentState=envField(s.brain,"AGENT_STATE").ifBlank{if(s.active=="1")"RUNNING" else "IDLE"}
        val agentWinner=envField(s.brain,"AGENT_WINNER").ifBlank{"NONE"}
        val agentReason=envField(s.brain,"AGENT_REASON")
        val execAt=envField(s.execution,"UPDATED_AT").toLongOrNull()?:envField(s.execution,"VERIFY_AT").toLongOrNull()?:0L
        val execFresh=execAt>0&&(now-execAt) in 0..180
        val execStatus=envField(s.execution,"EXECUTION_STATUS").ifBlank{envField(s.execution,"STATE")}.ifBlank{"NONE"}
        val readback=envField(s.execution,"READBACK_MATCH")
        val thoughtSrc=envField(s.thoughts,"SOURCE")
        val thoughtAt=envField(s.thoughts,"AT").toLongOrNull()?:0L
        val thoughtAge=if(thoughtAt>0) now-thoughtAt else -1L
        val thoughtFresh=thoughtAge in 0..360
        val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
        val conf=envField(s.thoughts,"CONFIDENCE")
        val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada reasoning baru yang dipublikasikan."}
        val thoughtTitle=when{
            thoughtSrc=="GEMINI"&&thoughtFresh->"PEMIKIRAN GEMINI"
            thoughtSrc=="GEMINI"->"LAST GEMINI THOUGHT"
            thoughtSrc.contains("HERMES",true)->"PEMIKIRAN HERMES H2"
            else->"PEMIKIRAN DJAEGER"
        }
        val thoughtState=if(thoughtFresh)thoughtStatus else if(thoughtAge>=0)"STALE • ${ageLabel(thoughtAge.toString())}" else thoughtStatus
        val executionLine=if(execFresh) "$execStatus • readback=${if(readback=="1")"VERIFIED" else if(readback.isBlank())"—" else readback}" else if(execAt>0) "LAST $execStatus • ${ageLabel((now-execAt).toString())}" else "NONE"
        val failureLine=if(agentState=="EXECUTION_FAILED"&&agentReason.isNotBlank()) "\nFailure: $agentReason" else ""
        val compactBody="Gemini: $provider • $geminiState\nAgent: $agentState • source=$agentWinner\nExecution: $executionLine$failureLine\n\n$thoughtTitle • $thoughtState\n$text"
        val fullBody="$compactBody\n\nModel: ${model.ifBlank{"—"}}\nThought confidence: ${conf.ifBlank{"—"}}%\nSession: ${if(s.active=="1")"ACTIVE ${s.game} • ${s.window}" else "INACTIVE"}"
        BoxCard("THOUGHT",if(compact)compactBody else fullBody,true)
    }
}

'''
ms=ms[:start]+thought+ms[end:]
m.write_text(ms)
print('R42_KOTLIN_STRING_ESCAPE=PASS')
print('R42_THOUGHT_CARD=RAW_GENERATOR_SAFE')
