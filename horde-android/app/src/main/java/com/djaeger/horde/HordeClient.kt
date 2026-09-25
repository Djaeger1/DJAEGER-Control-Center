package com.djaeger.horde

import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class HordeClient(private val apiKey: String) {
    private val base = "https://aihorde.net/api/v2"

    private fun request(method: String, path: String, body: String? = null): String {
        val c = (URL(base + path).openConnection() as HttpURLConnection)
        c.requestMethod = method
        c.connectTimeout = 20000
        c.readTimeout = 30000
        c.setRequestProperty("apikey", apiKey.ifBlank { "0000000000" })
        c.setRequestProperty("Client-Agent", "HordeUniversalAI:1.0.0")
        c.setRequestProperty("Accept", "application/json")
        if (body != null) {
            c.doOutput = true
            c.setRequestProperty("Content-Type", "application/json")
            c.outputStream.use { it.write(body.toByteArray()) }
        }
        val code = c.responseCode
        val stream = if (code in 200..299) c.inputStream else c.errorStream
        val text = BufferedReader(InputStreamReader(stream)).use { it.readText() }
        if (code !in 200..299) error("HTTP " + code + ": " + text)
        return text
    }

    fun models(): List<String> {
        val arr = JSONArray(request("GET", "/status/models"))
        return (0 until arr.length()).mapNotNull { i ->
            arr.optJSONObject(i)?.optString("name")?.takeIf { it.isNotBlank() }
        }.sorted()
    }

    fun text(prompt: String, model: String): String {
        val body = JSONObject().apply {
            put("prompt", prompt)
            put("models", JSONArray().put(model))
            put("params", JSONObject().apply {
                put("max_length", 512)
                put("max_context_length", 4096)
                put("temperature", 0.7)
            })
        }
        val id = JSONObject(request("POST", "/generate/text/async", body.toString())).getString("id")
        repeat(90) {
            Thread.sleep(2000)
            val s = JSONObject(request("GET", "/generate/text/status/" + id))
            val gens = s.optJSONArray("generations")
            if (s.optBoolean("done") && gens != null && gens.length() > 0) {
                return gens.getJSONObject(0).optString("text")
            }
        }
        error("Text generation timed out")
    }

    fun image(prompt: String, model: String): ByteArray {
        val body = JSONObject().apply {
            put("prompt", prompt)
            put("models", JSONArray().put(model))
            put("params", JSONObject().apply {
                put("width", 512); put("height", 512); put("steps", 20)
            })
        }
        val id = JSONObject(request("POST", "/generate/async", body.toString())).getString("id")
        repeat(120) {
            Thread.sleep(2000)
            val s = JSONObject(request("GET", "/generate/status/" + id))
            val gens = s.optJSONArray("generations")
            if (s.optBoolean("done") && gens != null && gens.length() > 0) {
                return Base64.decode(gens.getJSONObject(0).optString("img"), Base64.DEFAULT)
            }
        }
        error("Image generation timed out")
    }

    fun interrogate(imageBytes: ByteArray): String {
        val body = JSONObject().apply {
            put("source_image", Base64.encodeToString(imageBytes, Base64.NO_WRAP))
            put("forms", JSONArray().put(JSONObject().apply { put("name", "caption") }))
        }
        val id = JSONObject(request("POST", "/interrogate/async", body.toString())).getString("id")
        repeat(90) {
            Thread.sleep(2000)
            val s = JSONObject(request("GET", "/interrogate/status/" + id))
            if (s.optBoolean("done")) return s.toString()
        }
        error("Interrogation timed out")
    }
}
