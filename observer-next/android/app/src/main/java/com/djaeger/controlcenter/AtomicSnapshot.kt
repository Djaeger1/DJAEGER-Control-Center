package com.djaeger.controlcenter

/**
 * Parser for the single DJAEGER-owned atomic Control Center snapshot.
 * Unknown sections are tolerated and missing sections fail closed to empty data.
 */
object AtomicSnapshot {
    private val header = Regex("^__([A-Z0-9_]+)__$")
    private const val MAX_SNAPSHOT_CHARS = 256_000
    private const val MAX_SECTION_CHARS = 64_000

    fun sections(raw: String): Map<String, String> {
        if (raw.isBlank()) return emptyMap()
        val bounded = raw.take(MAX_SNAPSHOT_CHARS)
        val out = linkedMapOf<String, StringBuilder>()
        var current: String? = null
        for (line in bounded.lineSequence()) {
            val match = header.matchEntire(line.trim())
            if (match != null) {
                current = match.groupValues[1]
                out.putIfAbsent(current, StringBuilder())
                continue
            }
            val key = current ?: continue
            val target = out.getValue(key)
            if (target.length < MAX_SECTION_CHARS) {
                val room = MAX_SECTION_CHARS - target.length
                val add = if (line.length + 1 <= room) line + "\n" else line.take(room)
                target.append(add)
            }
        }
        return out.mapValues { it.value.toString().trimEnd() }
    }

    fun section(raw: String, name: String): String = sections(raw)[name.uppercase()].orEmpty()

    fun keyValues(section: String): Map<String, String> = section.lineSequence().mapNotNull { line ->
        val p = line.indexOf('=')
        if (p <= 0) null else line.substring(0, p).trim().uppercase() to clean(line.substring(p + 1))
    }.toMap()

    private fun clean(value: String): String {
        val x = value.trim()
        return if (x.length >= 2 && ((x.first() == '\'' && x.last() == '\'') || (x.first() == '"' && x.last() == '"'))) {
            x.substring(1, x.length - 1)
        } else x
    }
}
