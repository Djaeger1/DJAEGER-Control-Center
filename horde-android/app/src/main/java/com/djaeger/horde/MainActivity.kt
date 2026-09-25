package com.djaeger.horde

import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { HordeApp() }
    }
}

@Composable
fun HordeApp() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val prefs = remember { context.getSharedPreferences("horde", 0) }
    var key by remember { mutableStateOf(prefs.getString("key", "") ?: "") }
    var models by remember { mutableStateOf(listOf<String>()) }
    var model by remember { mutableStateOf("") }
    var prompt by remember { mutableStateOf("") }
    var output by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var tab by remember { mutableIntStateOf(0) }
    var image by remember { mutableStateOf<android.graphics.Bitmap?>(null) }
    val scope = rememberCoroutineScope()

    fun run(block: () -> String) {
        busy = true
        output = ""
        scope.launch(Dispatchers.IO) {
            runCatching { block() }
                .onSuccess { output = it }
                .onFailure { output = it.message ?: "Request failed" }
            busy = false
        }
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return@rememberLauncherForActivityResult
            image = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            run { HordeClient(key).interrogate(bytes) }
        }
    }

    MaterialTheme {
        Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())) {
            Text("Horde Universal AI", style = MaterialTheme.typography.headlineSmall)
            Text("Direct AI Horde • dynamic model selection", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = key,
                onValueChange = { key = it; prefs.edit().putString("key", it).apply() },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("AI Horde API key") },
                singleLine = true
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(enabled = !busy, onClick = {
                    busy = true
                    scope.launch(Dispatchers.IO) {
                        runCatching { HordeClient(key).models() }
                            .onSuccess { list ->
                                models = list
                                if (model !in list) model = list.firstOrNull().orEmpty()
                                output = "Loaded " + list.size + " active models."
                            }
                            .onFailure { e -> output = e.message ?: "Model load failed" }
                        busy = false
                    }
                }) { Text("Refresh models") }
                if (busy) CircularProgressIndicator(Modifier.size(22.dp))
            }
            Spacer(Modifier.height(8.dp))
            if (models.isNotEmpty()) {
                var expanded by remember { mutableStateOf(false) }
                Box {
                    OutlinedButton(onClick = { expanded = true }) {
                        Text(if (model.isBlank()) "Select model" else model)
                    }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        models.forEach { m ->
                            DropdownMenuItem(text = { Text(m) }, onClick = { model = m; expanded = false })
                        }
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            TabRow(selectedTabIndex = tab) {
                listOf("Text", "Image", "Interrogate").forEachIndexed { i, t ->
                    Tab(selected = tab == i, onClick = { tab = i }, text = { Text(t) })
                }
            }
            Spacer(Modifier.height(12.dp))
            if (tab < 2) {
                OutlinedTextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    modifier = Modifier.fillMaxWidth().height(140.dp),
                    label = { Text(if (tab == 0) "Prompt" else "Image prompt") }
                )
                Spacer(Modifier.height(8.dp))
                Button(
                    enabled = !busy && prompt.isNotBlank() && model.isNotBlank(),
                    onClick = {
                        if (tab == 0) {
                            run { HordeClient(key).text(prompt, model) }
                        } else {
                            busy = true
                            output = ""
                            scope.launch(Dispatchers.IO) {
                                runCatching { HordeClient(key).image(prompt, model) }
                                    .onSuccess { bytes ->
                                        image = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                                        output = "Image ready."
                                    }
                                    .onFailure { e -> output = e.message ?: "Image generation failed" }
                                busy = false
                            }
                        }
                    }
                ) { Text(if (tab == 0) "Generate text" else "Generate image") }
            } else {
                Button(enabled = !busy, onClick = { picker.launch("image/*") }) {
                    Text("Choose image and interrogate")
                }
            }
            Spacer(Modifier.height(12.dp))
            image?.let {
                Image(it.asImageBitmap(), "Horde result", Modifier.fillMaxWidth().heightIn(max = 360.dp))
            }
            if (output.isNotBlank()) {
                Text(output, Modifier.fillMaxWidth())
            }
        }
    }
}
