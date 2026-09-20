package com.djaeger.norebootrecovery;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    private TextView status;
    private Button runButton;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32,32,32,32);
        root.setBackgroundColor(Color.rgb(10,15,24));

        TextView title=new TextView(this);
        title.setText("DJAEGER • NO-REBOOT RECOVERY");
        title.setTextColor(Color.WHITE);
        title.setTextSize(22);
        title.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        root.addView(title,new LinearLayout.LayoutParams(-1,-2));

        TextView scope=new TextView(this);
        scope.setText("\nMemulihkan updater Railway, memastikan Arcane Legends kembali menjadi GAME, lalu me-refresh controller/snapshot secara hot.\n\nTidak flash • tidak reboot • tidak mengganti profil CPU/GPU • tidak mengganti controller/predictor.");
        scope.setTextColor(Color.LTGRAY);
        scope.setTextSize(15);
        root.addView(scope,new LinearLayout.LayoutParams(-1,-2));

        runButton=new Button(this);
        runButton.setText("PULIHKAN SEKARANG");
        LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,-2);
        bp.topMargin=28;
        root.addView(runButton,bp);

        ScrollView scroll=new ScrollView(this);
        status=new TextView(this);
        status.setText("Siap. Tekan tombol sekali dan izinkan root.");
        status.setTextColor(Color.rgb(180,255,200));
        status.setTextSize(13);
        status.setTypeface(Typeface.MONOSPACE);
        status.setPadding(0,24,0,24);
        scroll.addView(status,new ScrollView.LayoutParams(-1,-2));
        LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,0,1f);
        root.addView(scroll,sp);
        setContentView(root);

        runButton.setOnClickListener(v -> runRecovery());
    }

    private void runRecovery() {
        runButton.setEnabled(false);
        status.setText("RECOVERY=STARTING\nMeminta akses root...");
        new Thread(() -> {
            String result;
            try {
                File script=new File(getCacheDir(),"djaeger-repair.sh");
                try(InputStream in=getAssets().open("repair.sh"); FileOutputStream out=new FileOutputStream(script)){
                    byte[] buf=new byte[8192]; int n;
                    while((n=in.read(buf))>0) out.write(buf,0,n);
                }
                script.setReadable(true,false);
                Process p=new ProcessBuilder("su","-c","sh '"+script.getAbsolutePath()+"'").redirectErrorStream(true).start();
                boolean done=p.waitFor(75, TimeUnit.SECONDS);
                if(!done){
                    p.destroy();
                    if(p.isAlive()) p.destroyForcibly();
                    result="STATUS=FAIL\nREASON=RECOVERY_TIMEOUT";
                } else {
                    result=new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
                    if(result.isEmpty()) result="STATUS=FAIL\nREASON=EMPTY_OUTPUT\nRC="+p.exitValue();
                }
            } catch(Exception e) {
                result="STATUS=FAIL\nREASON="+e.getClass().getSimpleName()+": "+String.valueOf(e.getMessage());
            }
            final String output=result;
            runOnUiThread(() -> {
                status.setText(output);
                runButton.setEnabled(true);
                runButton.setText(output.contains("STATUS=PASS") ? "PULIH • JALANKAN LAGI JIKA PERLU" : "COBA LAGI");
            });
        }).start();
    }
}
