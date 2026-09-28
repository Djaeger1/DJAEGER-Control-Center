package com.djaeger.apkreverse;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int PICK_APK = 4101;
    private TextView selectedText;
    private TextView statusText;
    private TextView resultText;
    private ProgressBar progress;
    private Uri selectedUri;
    private String selectedName = "none";
    private String lastReport = "";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(22), dp(18), dp(28));
        root.setBackgroundColor(0xFF101114);
        scroll.addView(root);

        TextView title = text("DJAEGER APK Reverse", 28, Typeface.BOLD);
        title.setTextColor(0xFFFFFFFF);
        root.addView(title, lp());

        TextView subtitle = text("Standalone local APK reconnaissance • v0.1.0", 14, Typeface.NORMAL);
        subtitle.setTextColor(0xFFB8BBC4);
        root.addView(subtitle, lp());

        Button pick = button("Pilih APK");
        pick.setOnClickListener(v -> pickApk());
        root.addView(pick, topLp());

        selectedText = text("APK: belum dipilih", 15, Typeface.BOLD);
        selectedText.setTextColor(0xFFD9DBE3);
        root.addView(selectedText, lp());

        Button analyze = button("ANALISIS SEKARANG");
        analyze.setOnClickListener(v -> analyzeSelected());
        root.addView(analyze, topLp());

        progress = new ProgressBar(this);
        progress.setIndeterminate(true);
        progress.setVisibility(View.GONE);
        root.addView(progress, centeredLp());

        statusText = text("Status: siap", 14, Typeface.NORMAL);
        statusText.setTextColor(0xFFB8BBC4);
        root.addView(statusText, topLp());

        TextView mode = text("Mode v0.1: read-only. Tidak mengubah APK yang dipilih.", 13, Typeface.BOLD);
        mode.setTextColor(0xFFB8BBC4);
        root.addView(mode, topLp());

        resultText = text("Hasil analisis akan muncul di sini.", 13, Typeface.NORMAL);
        resultText.setTextIsSelectable(true);
        resultText.setTypeface(Typeface.MONOSPACE);
        resultText.setTextColor(0xFFE7E8ED);
        resultText.setPadding(dp(12), dp(12), dp(12), dp(12));
        resultText.setBackgroundColor(0xFF191B20);
        root.addView(resultText, topLp());

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
        root.addView(actions, topLp());

        setContentView(scroll);
    }

    private void pickApk() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                "application/vnd.android.package-archive", "application/zip", "application/octet-stream"
        });
        startActivityForResult(i, PICK_APK);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_APK || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        selectedUri = data.getData();
        selectedName = resolveName(selectedUri);
        selectedText.setText("APK: " + selectedName);
        statusText.setText("Status: file dipilih • tekan ANALISIS SEKARANG");
        resultText.setText("Menunggu analisis…");
        lastReport = "";
        try {
            getContentResolver().takePersistableUriPermission(
                    selectedUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException ignored) {}
    }

    private void analyzeSelected() {
        if (selectedUri == null) {
            toast("Pilih APK terlebih dahulu.");
            return;
        }
        progress.setVisibility(View.VISIBLE);
        statusText.setText("Status: membaca APK secara lokal…");
        resultText.setText("");

        worker.execute(() -> {
            try (InputStream in = getContentResolver().openInputStream(selectedUri)) {
                if (in == null) throw new IOException("Tidak dapat membuka URI APK.");
                Analyzer.Result result = Analyzer.analyze(in);
                String report = result.toReport(selectedName);
                runOnUiThread(() -> {
                    lastReport = report;
                    resultText.setText(report);
                    statusText.setText(String.format(Locale.US,
                            "Status: SELESAI • %.2f MB dibaca • SHA-256 siap",
                            result.bytesRead / 1048576.0));
                    progress.setVisibility(View.GONE);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    statusText.setText("Status: GAGAL • " + e.getMessage());
                    resultText.setText("Analisis gagal.\n\n" + e);
                    progress.setVisibility(View.GONE);
                });
            }
        });
    }

    private void copyReport() {
        if (lastReport.isEmpty()) {
            toast("Belum ada hasil untuk disalin.");
            return;
        }
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("DJAEGER APK Reverse", lastReport));
        toast("Report disalin.");
    }

    private void shareReport() {
        if (lastReport.isEmpty()) {
            toast("Belum ada hasil untuk dibagikan.");
            return;
        }
        Intent i = new Intent(Intent.ACTION_SEND);
        i.setType("text/plain");
        i.putExtra(Intent.EXTRA_SUBJECT, "DJAEGER APK Reverse report - " + selectedName);
        i.putExtra(Intent.EXTRA_TEXT, lastReport);
        startActivity(Intent.createChooser(i, "Bagikan report"));
    }

    private String resolveName(Uri uri) {
        try (android.database.Cursor c = getContentResolver().query(
                uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                String name = c.getString(0);
                if (name != null && !name.isEmpty()) return name;
            }
        } catch (Exception ignored) {}
        String path = uri.getLastPathSegment();
        return path == null ? "selected.apk" : path;
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

    private LinearLayout.LayoutParams lp() {
        return new LinearLayout.LayoutParams(-1, -2);
    }

    private LinearLayout.LayoutParams topLp() {
        LinearLayout.LayoutParams p = lp();
        p.topMargin = dp(10);
        return p;
    }

    private LinearLayout.LayoutParams centeredLp() {
        LinearLayout.LayoutParams p = lp();
        p.gravity = Gravity.CENTER_HORIZONTAL;
        p.topMargin = dp(8);
        return p;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }
}
