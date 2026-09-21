package com.djaeger.recovery;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.*;
import java.util.concurrent.TimeUnit;

public final class MainActivity extends Activity {
    private TextView status;
    private Button recover;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(32, 32, 32, 32);
        body.setBackgroundColor(Color.rgb(9, 11, 16));

        TextView title = new TextView(this);
        title.setText("DJAEGER AI • TRANSPORT RECOVERY");
        title.setTextColor(Color.rgb(67, 227, 138));
        title.setTextSize(20);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        body.addView(title);

        TextView info = new TextView(this);
        info.setText("\nTarget: Adaptive VC202/203\nNo flash • no reboot • no CPU/GPU write\nRepairs Railway credentials, bridge and remote updater only.\n");
        info.setTextColor(Color.LTGRAY);
        info.setTextSize(15);
        body.addView(info);

        recover = new Button(this);
        recover.setText("RECOVER TRANSPORT");
        recover.setOnClickListener(v -> startRecovery());
        body.addView(recover);

        status = new TextView(this);
        status.setText("\nREADY\nTap RECOVER TRANSPORT once.");
        status.setTextColor(Color.WHITE);
        status.setTextSize(13);
        status.setTypeface(Typeface.MONOSPACE);
        status.setTextIsSelectable(true);
        body.addView(status);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(body);
        setContentView(scroll);
    }

    private File copyAsset(String name) throws IOException {
        File out = new File(getFilesDir(), name);
        try (InputStream in = getAssets().open(name); OutputStream os = new FileOutputStream(out, false)) {
            byte[] buf = new byte[8192];
            for (int n; (n = in.read(buf)) > 0;) os.write(buf, 0, n);
        }
        out.setReadable(true, false);
        return out;
    }

    private static String q(String s) {
        return "'" + s.replace("'", "'\\''") + "'";
    }

    private void startRecovery() {
        recover.setEnabled(false);
        status.setText("\nREQUESTING ROOT…");
        new Thread(() -> {
            StringBuilder out = new StringBuilder();
            int rc = -1;
            try {
                File recovery = copyAsset("recovery.sh");
                copyAsset("railway_bridge.sh");
                copyAsset("remote_updater.sh");
                String cmd = "sh " + q(recovery.getAbsolutePath()) + " " + q(getFilesDir().getAbsolutePath());
                Process p = new ProcessBuilder("su", "-c", cmd).redirectErrorStream(true).start();
                try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        out.append(line).append('\n');
                        final String snapshot = out.toString();
                        runOnUiThread(() -> status.setText("\n" + snapshot));
                    }
                }
                if (!p.waitFor(70, TimeUnit.SECONDS)) {
                    p.destroy();
                    p.destroyForcibly();
                    throw new IOException("RECOVERY_TIMEOUT");
                }
                rc = p.exitValue();
            } catch (Throwable t) {
                out.append("RECOVERY_APP_ERROR=").append(t.getClass().getSimpleName())
                   .append(":").append(t.getMessage()).append('\n');
            }
            final int frc = rc;
            final String text = out.toString();
            runOnUiThread(() -> {
                status.setText("\n" + text + "\nAPP_EXIT=" + frc);
                recover.setEnabled(true);
            });
        }).start();
    }
}
