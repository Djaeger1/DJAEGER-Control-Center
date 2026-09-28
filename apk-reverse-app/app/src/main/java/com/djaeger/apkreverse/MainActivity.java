package com.djaeger.apkreverse;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int PICK_APK = 4101;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private Uri selectedUri;
    private String selectedName = "Belum dipilih";
    private Analyzer.Result lastResult;
    private String lastReport = "";
    private TextView selectedText;
    private TextView statusText;
    private TextView reportText;
    private ProgressBar progress;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(18), dp(16), dp(28));
        root.setBackgroundColor(0xFF0F1013);
        scroll.addView(root);

        TextView title = text("DJAEGER APK REVERSE", 27, Typeface.BOLD);
        title.setTextColor(0xFFFFFFFF);
        root.addView(title, lp());

        TextView subtitle = text("Model A • local workspace • Android standalone", 13, Typeface.NORMAL);
        subtitle.setTextColor(0xFFB8BBC4);
        root.addView(subtitle, gap());

        Button pick = button("📂  Pilih APK");
        pick.setOnClickListener(v -> pickApk());
        root.addView(pick, gap());

        selectedText = text("APK: " + selectedName, 14, Typeface.BOLD);
        selectedText.setTextColor(0xFFDDE0E8);
        root.addView(selectedText, gap());

        addSection(root, "🔎  ANALISIS", new String[] {
                "Manifest", "DEX", "Java / Kotlin", "Smali", "Native .so", "Proteksi"
        });

        Button analyze = button("ANALISIS SEKARANG");
        analyze.setOnClickListener(v -> analyzeSelected());
        root.addView(analyze, gap());

        progress = new ProgressBar(this);
        progress.setIndeterminate(true);
        progress.setVisibility(View.GONE);
        root.addView(progress, gap());

        addSection(root, "🤖  AI", new String[] {"Jelaskan hasil + sarankan langkah"});
        Button explain = button("JELASKAN HASIL");
        explain.setOnClickListener(v -> explainResult());
        root.addView(explain, gap());

        addSection(root, "🛠  OPERASI", new String[] {
                "Patch", "Rebuild", "Sign", "Export"
        });
        Button export = button("EXPORT WORKSPACE");
        export.setOnClickListener(v -> exportReport());
        root.addView(export, gap());
        Button ops = button("STATUS TOOLCHAIN");
        ops.setOnClickListener(v -> toast("Patch / Rebuild / Sign memerlukan toolchain eksternal; tidak saya palsukan sebagai berhasil."));
        root.addView(ops, gap());

        addSection(root, "📱  RUNTIME", new String[] {
                "Install", "Log", "Frida / root tools"
        });
        Button install = button("INSTALL APK TERPILIH");
        install.setOnClickListener(v -> installSelected());
        root.addView(install, gap());
        Button runtime = button("CEK ROOT + FRIDA");
        runtime.setOnClickListener(v -> checkRuntime());
        root.addView(runtime, gap());

        addSection(root, "📁  WORKSPACE", new String[] {
                "Hasil analisis", "Report AI", "Metadata", "Hash"
        });
        reportText = text("Workspace kosong. Pilih APK lalu jalankan ANALISIS.", 12, Typeface.NORMAL);
        reportText.setTypeface(Typeface.MONOSPACE);
        reportText.setTextColor(0xFFE7E8ED);
        reportText.setPadding(dp(12), dp(12), dp(12), dp(12));
        reportText.setBackgroundColor(0xFF191B20);
        root.addView(reportText, gap());

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button copy = button("Copy");
        copy.setOnClickListener(v -> copyReport());
        actions.addView(copy, new LinearLayout.LayoutParams(0, -2, 1));
        Button share = button("Share");
        share.setOnClickListener(v -> shareReport());
        LinearLayout.LayoutParams shareLp = new LinearLayout.LayoutParams(0, -2, 1);
        shareLp.leftMargin = dp(8);
        actions.addView(share, shareLp);
        root.addView(actions, gap());

        statusText = text("Status: siap", 13, Typeface.BOLD);
        statusText.setTextColor(0xFFB8BBC4);
        root.addView(statusText, gap());

        setContentView(scroll);
    }

    private void addSection(LinearLayout root, String heading, String[] rows) {
        TextView h = text(heading, 17, Typeface.BOLD);
        h.setTextColor(0xFFFFFFFF);
        root.addView(h, gap());
        for (String row : rows) {
            TextView item = text("   ├─ " + row, 14, Typeface.NORMAL);
            item.setTextColor(0xFFD0D3DB);
            root.addView(item, lp());
        }
    }

    private void pickApk() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("application/vnd.android.package-archive");
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(i, PICK_APK);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 4102 && resultCode == RESULT_OK && data != null && data.getData() != null) {
            try (java.io.OutputStream out = getContentResolver().openOutputStream(data.getData())) {
                if (out == null) throw new IllegalStateException("File tujuan tidak dapat dibuka");
                out.write(lastReport.getBytes("UTF-8"));
                statusText.setText("Status: workspace report diekspor");
                toast("Report diekspor.");
            } catch (Exception e) {
                toast("Export gagal: " + e.getMessage());
            }
            return;
        }
        if (requestCode != PICK_APK || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        selectedUri = data.getData();
        selectedName = resolveName(selectedUri);
        try { getContentResolver().takePersistableUriPermission(selectedUri, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException ignored) {}
        selectedText.setText("APK: " + selectedName);
        statusText.setText("Status: APK dipilih");
        reportText.setText("Siap dianalisis: " + selectedName);
    }

    private void analyzeSelected() {
        if (selectedUri == null) { toast("Pilih APK terlebih dahulu."); return; }
        progress.setVisibility(View.VISIBLE);
        statusText.setText("Status: ANALISIS berjalan…");
        worker.execute(() -> {
            try (InputStream in = getContentResolver().openInputStream(selectedUri)) {
                if (in == null) throw new IllegalStateException("URI tidak dapat dibuka");
                lastResult = Analyzer.analyze(in);
                lastReport = lastResult.toReport(selectedName);
                main.post(() -> {
                    reportText.setText(lastReport);
                    statusText.setText(String.format(Locale.US, "Status: SELESAI • %.2f MB • SHA-256 %s…",
                            lastResult.bytesRead / 1048576.0, lastResult.sha256.substring(0, 12)));
                    progress.setVisibility(View.GONE);
                });
            } catch (Exception e) {
                main.post(() -> {
                    statusText.setText("Status: GAGAL");
                    reportText.setText("Analisis gagal: " + e);
                    progress.setVisibility(View.GONE);
                });
            }
        });
    }

    private void explainResult() {
        if (lastResult == null) { toast("Jalankan analisis dulu."); return; }
        lastReport = lastResult.toAiExplanation(selectedName);
        reportText.setText(lastReport);
        statusText.setText("Status: AI lokal menjelaskan hasil analisis");
    }

    private void exportReport() {
        if (lastReport.isEmpty()) { toast("Belum ada hasil."); return; }
        Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        i.setType("text/plain");
        i.putExtra(Intent.EXTRA_TITLE, selectedName + ".djaeger.txt");
        startActivityForResult(i, 4102);
    }

    private void installSelected() {
        if (selectedUri == null) { toast("Pilih APK terlebih dahulu."); return; }
        try {
            Intent i = new Intent(Intent.ACTION_VIEW);
            i.setDataAndType(selectedUri, "application/vnd.android.package-archive");
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(i);
            statusText.setText("Status: membuka installer Android");
        } catch (Exception e) {
            toast("Installer Android tidak dapat dibuka: " + e.getMessage());
        }
    }

    private void checkRuntime() {
        worker.execute(() -> {
            String root = shell("su -c id");
            String frida = shell("su -c 'pidof frida-server'");
            String log = shell("su -c 'logcat -d -t 60 -s AndroidRuntime *:S'");
            main.post(() -> {
                reportText.setText(
                        "RUNTIME CHECK\n================\n" +
                        "Root:\n" + root.trim() + "\n\n" +
                        "Frida-server PID:\n" + (frida.trim().isEmpty() ? "tidak terdeteksi" : frida.trim()) +
                        "\n\nAndroidRuntime log snapshot:\n" + (log.trim().isEmpty() ? "tidak ada output / akses log ditolak" : log.trim()));
                statusText.setText("Status: runtime check selesai");
            });
        });
    }

    private String shell(String cmd) {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"sh", "-c", cmd});
            java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
            java.io.InputStream in = p.getInputStream();
            byte[] b = new byte[4096];
            int n;
            while ((n = in.read(b)) != -1) out.write(b, 0, n);
            p.waitFor();
            return out.toString("UTF-8");
        } catch (Exception e) {
            return "gagal: " + e;
        }
    }

    private void copyReport() {
        if (lastReport.isEmpty()) { toast("Belum ada hasil."); return; }
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("DJAEGER APK Reverse", lastReport));
        toast("Report disalin.");
    }

    private void shareReport() {
        if (lastReport.isEmpty()) { toast("Belum ada hasil."); return; }
        Intent i = new Intent(Intent.ACTION_SEND);
        i.setType("text/plain");
        i.putExtra(Intent.EXTRA_SUBJECT, "DJAEGER APK Reverse - " + selectedName);
        i.putExtra(Intent.EXTRA_TEXT, lastReport);
        startActivity(Intent.createChooser(i, "Bagikan report"));
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
    }

    @Override protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }

    private String resolveName(Uri uri) {
        try (android.database.Cursor c = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                String n = c.getString(0);
                if (n != null && !n.isEmpty()) return n;
            }
        } catch (Exception ignored) {}
        String p = uri.getLastPathSegment();
        return p == null ? "selected.apk" : p;
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        return b;
    }

    private TextView text(String value, int size, int style) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTypeface(Typeface.DEFAULT, style);
        return t;
    }

    private LinearLayout.LayoutParams lp() { return new LinearLayout.LayoutParams(-1, -2); }

    private LinearLayout.LayoutParams gap() {
        LinearLayout.LayoutParams p = lp();
        p.topMargin = dp(9);
        return p;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }
}
