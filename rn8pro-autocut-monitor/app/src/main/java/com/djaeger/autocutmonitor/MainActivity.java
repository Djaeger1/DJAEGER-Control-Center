package com.djaeger.autocutmonitor;

import android.app.Activity;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        AutoCutReceiver.startMonitor(this);

        int pad = Math.round(24 * getResources().getDisplayMetrics().density);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setGravity(Gravity.CENTER_VERTICAL);

        TextView title = new TextView(this);
        title.setText("DJAEGER AutoCut Monitor");
        title.setTextSize(24f);
        title.setTypeface(Typeface.DEFAULT_BOLD);

        TextView body = new TextView(this);
        body.setText("\nKhusus Redmi Note 8 Pro.\n\nNotifikasi selalu aktif dan menampilkan suhu serta daya baterai. Label BYPASS hanya aktif bila modul AutoCut membuktikan cut hardware.");
        body.setTextSize(16f);

        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(body, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(root);
    }
}
