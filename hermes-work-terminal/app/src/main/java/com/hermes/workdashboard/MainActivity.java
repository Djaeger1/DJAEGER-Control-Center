package com.hermes.workdashboard;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(9, 13, 18);
    private static final int PANEL = Color.rgb(18, 24, 32);
    private static final int PANEL2 = Color.rgb(13, 19, 26);
    private static final int LINE = Color.rgb(42, 53, 67);
    private static final int TEXT = Color.rgb(236, 242, 248);
    private static final int MUTED = Color.rgb(145, 158, 173);
    private static final int OK = Color.rgb(79, 209, 123);
    private static final int WARN = Color.rgb(229, 181, 77);
    private static final int BAD = Color.rgb(255, 107, 107);
    private static final int ACCENT = Color.rgb(77, 145, 255);

    private static final String DEFAULT_RUNTIME = "http://192.168.42.129:8766";
    private static final String DEFAULT_BOOTSTRAP = "http://192.168.42.129:8765";
    private static final String PREFS = "hermes_work_dashboard";

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;

    private FrameLayout content;
    private TextView online;
    private TextView pageTitle;
    private LinearLayout navBar;
    private int currentPage = 0;
    private boolean destroyed = false;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        buildShell();
        showPage(0);
    }

    private void buildShell() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setPadding(dp(16), dp(12), dp(12), dp(10));
        top.setBackgroundColor(PANEL);

        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        TextView brand = text("HERMES WORK", 18, TEXT, true);
        pageTitle = text("WORK", 12, MUTED, true);
        titles.addView(brand);
        titles.addView(pageTitle);
        top.addView(titles, new LinearLayout.LayoutParams(0, -2, 1f));

        online = text("● CHECKING", 12, MUTED, true);
        online.setPadding(dp(8), dp(4), dp(8), dp(4));
        top.addView(online);
        root.addView(top);

        content = new FrameLayout(this);
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1f));

        HorizontalScrollView navScroll = new HorizontalScrollView(this);
        navScroll.setHorizontalScrollBarEnabled(false);
        navScroll.setFillViewport(true);
        navScroll.setBackgroundColor(PANEL);
        navBar = new LinearLayout(this);
        navBar.setOrientation(LinearLayout.HORIZONTAL);
        navBar.setPadding(dp(4), dp(5), dp(4), dp(7));
        navScroll.addView(navBar, new HorizontalScrollView.LayoutParams(-1, -2));

        String[] labels = {"WORK", "RESEARCH", "PLANNER", "INSIGHTS", "SYSTEM", "UPDATE"};
        for (int i = 0; i < labels.length; i++) {
            final int p = i;
            Button b = navButton(labels[i]);
            b.setOnClickListener(v -> showPage(p));
            navBar.addView(b, new LinearLayout.LayoutParams(dp(76), dp(50)));
        }
        root.addView(navScroll);
        setContentView(root);
    }

    private void showPage(int page) {
        currentPage = page;
        String[] names = {"WORK", "RESEARCH", "PLANNER", "INSIGHTS", "SYSTEM", "UPDATE"};
        pageTitle.setText(names[page]);
        updateNav();

        content.removeAllViews();
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(dp(14), dp(12), dp(14), dp(18));
        scroll.addView(body);
        content.addView(scroll, new FrameLayout.LayoutParams(-1, -1));

        switch (page) {
            case 0: buildWork(body); break;
            case 1: buildResearch(body); break;
            case 2: buildPlanner(body); break;
            case 3: buildInsights(body); break;
            case 4: buildSystem(body); break;
            case 5: buildUpdate(body); break;
        }
        refreshOnlineOnly();
    }

    private void updateNav() {
        for (int i = 0; i < navBar.getChildCount(); i++) {
            Button b = (Button) navBar.getChildAt(i);
            boolean active = i == currentPage;
            b.setTextColor(active ? Color.WHITE : MUTED);
            b.setBackgroundColor(active ? Color.rgb(33, 75, 134) : PANEL);
        }
    }

    private void buildWork(LinearLayout body) {
        body.addView(sectionTitle("Today's Work", "Fokus utama: apa yang harus dikerjakan hari ini."));

        LinearLayout health = card();
        health.addView(text("WORKER STATUS", 11, MUTED, true));
        LinearLayout healthRow = row();
        TextView modem = metric(healthRow, "MODEM", "…");
        TextView worker = metric(healthRow, "WORKER", "…");
        health.addView(healthRow);
        body.addView(health);

        LinearLayout stats = card();
        stats.addView(text("RESEARCH TODAY", 11, MUTED, true));
        LinearLayout r1 = row();
        TextView sources = metric(r1, "SOURCES", "—");
        TextView found = metric(r1, "FOUND", "—");
        stats.addView(r1);
        LinearLayout r2 = row();
        TextView added = metric(r2, "NEW", "—");
        TextView dup = metric(r2, "DUPLICATES", "—");
        stats.addView(r2);
        TextView last = text("Last research: —", 12, MUTED, false);
        last.setPadding(0, dp(8), 0, 0);
        stats.addView(last);

        Button run = actionButton("RUN RESEARCH NOW", true);
        stats.addView(run);
        TextView runOut = mono("Ready.");
        stats.addView(runOut);
        body.addView(stats);

        LinearLayout briefCard = card();
        briefCard.addView(text("DAILY BRIEF", 11, MUTED, true));
        TextView brief = text("Belum ada brief.", 14, TEXT, false);
        brief.setPadding(0, dp(8), 0, 0);
        briefCard.addView(brief);
        body.addView(briefCard);

        run.setOnClickListener(v -> {
            run.setEnabled(false);
            runOut.setText("Research berjalan…");
            apiAsync("POST", "/api/work/run-research", null, true, (code, s) -> {
                run.setEnabled(true);
                runOut.setText(s.trim());
                loadWorkData(modem, worker, sources, found, added, dup, last, brief);
            });
        });

        loadWorkData(modem, worker, sources, found, added, dup, last, brief);
    }

    private void loadWorkData(TextView modem, TextView worker, TextView sources, TextView found, TextView added, TextView dup, TextView last, TextView brief) {
        apiAsync("GET", "/api/work/status", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(modem, j.optString("tether_state", "—"), "UP".equals(j.optString("tether_state")) ? OK : BAD);
                String w = j.optBoolean("safe_mode") ? "SAFE MODE" : (j.optBoolean("worker_paused") ? "PAUSED" : "READY");
                setMetric(worker, w, "READY".equals(w) ? OK : WARN);
            } catch (Exception ignored) {}
        });
        apiAsync("GET", "/api/work/daily", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                JSONObject lr = j.optJSONObject("last_run");
                if (lr != null) {
                    setMetric(sources, val(lr, "sources_checked"), TEXT);
                    setMetric(found, val(lr, "found"), TEXT);
                    setMetric(added, val(lr, "added"), OK);
                    setMetric(dup, val(lr, "duplicates"), MUTED);
                }
            } catch (Exception ignored) {}
        });
        apiAsync("GET", "/api/work/research", null, false, (code, s) -> {
            try { last.setText("Last research: " + dash(new JSONObject(s).optString("last_research"))); } catch (Exception ignored) {}
        });
        apiAsync("GET", "/api/work/brief", null, false, (code, s) -> {
            try {
                JSONArray a = new JSONObject(s).optJSONArray("ideas");
                if (a == null || a.length() == 0) { brief.setText("Belum ada ide. Jalankan research."); return; }
                StringBuilder x = new StringBuilder();
                for (int i = 0; i < Math.min(3, a.length()); i++) {
                    JSONObject o = a.getJSONObject(i);
                    x.append(i + 1).append(". ").append(dash(o.optString("Title", o.optString("title"))));
                    String cat = o.optString("Category", o.optString("category"));
                    if (!cat.isEmpty()) x.append("  ·  ").append(cat);
                    x.append("\n");
                }
                brief.setText(x.toString().trim());
            } catch (Exception ignored) {}
        });
    }

    private void buildResearch(LinearLayout body) {
        body.addView(sectionTitle("Research Intelligence", "Apa yang dicari dan dibutuhkan, lalu dikelompokkan menjadi topik."));

        LinearLayout summary = card();
        summary.addView(text("RESEARCH SUMMARY", 11, MUTED, true));
        LinearLayout r = row();
        TextView total = metric(r, "TOTAL ITEMS", "—");
        TextView last = metric(r, "LAST RUN", "—");
        summary.addView(r);
        body.addView(summary);

        LinearLayout catCard = card();
        catCard.addView(text("TOPIC CATEGORIES", 11, MUTED, true));
        LinearLayout cats = new LinearLayout(this);
        cats.setOrientation(LinearLayout.VERTICAL);
        catCard.addView(cats);
        body.addView(catCard);

        LinearLayout searchCard = card();
        searchCard.addView(text("WHAT PEOPLE NEED / SEARCH", 11, MUTED, true));
        TextView top = text("Belum ada data.", 14, TEXT, false);
        top.setPadding(0, dp(8), 0, 0);
        searchCard.addView(top);
        body.addView(searchCard);

        apiAsync("GET", "/api/work/research", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(total, String.valueOf(j.optInt("total_items")), TEXT);
                String lr = dash(j.optString("last_research"));
                setMetric(last, lr.length() > 10 ? lr.substring(0, 10) : lr, MUTED);
                JSONObject c = j.optJSONObject("categories");
                if (c != null) renderCategories(cats, c);
            } catch (Exception e) { cats.addView(text("Data belum tersedia.", 13, MUTED, false)); }
        });

        apiAsync("GET", "/api/work/brief", null, false, (code, s) -> {
            try {
                JSONArray a = new JSONObject(s).optJSONArray("ideas");
                if (a == null || a.length() == 0) return;
                StringBuilder x = new StringBuilder();
                for (int i = 0; i < Math.min(8, a.length()); i++) {
                    JSONObject o = a.getJSONObject(i);
                    double score = o.optDouble("Score", o.optDouble("score", 0));
                    x.append("• ").append(dash(o.optString("Title", o.optString("title"))))
                            .append("   [").append(Math.round(score)).append("]\n");
                }
                top.setText(x.toString().trim());
            } catch (Exception ignored) {}
        });
    }

    private void renderCategories(LinearLayout target, JSONObject c) {
        target.removeAllViews();
        try {
            Iterator<String> it = c.keys();
            boolean any = false;
            while (it.hasNext()) {
                any = true;
                String k = it.next();
                LinearLayout line = row();
                TextView name = text(k.toUpperCase(Locale.US), 13, TEXT, true);
                TextView count = text(String.valueOf(c.optInt(k)), 15, ACCENT, true);
                line.addView(name, new LinearLayout.LayoutParams(0, dp(38), 1f));
                line.addView(count, new LinearLayout.LayoutParams(dp(70), dp(38)));
                line.setGravity(Gravity.CENTER_VERTICAL);
                target.addView(line);
            }
            if (!any) target.addView(text("NO DATA YET", 13, WARN, true));
        } catch (Exception e) {
            target.addView(text("NO DATA YET", 13, WARN, true));
        }
    }

    private void buildPlanner(LinearLayout body) {
        body.addView(sectionTitle("Content Planner", "Dari hasil research menjadi prioritas konten yang siap dikerjakan."));

        LinearLayout pipe = card();
        pipe.addView(text("WORKFLOW", 11, MUTED, true));
        pipe.addView(text("Research  →  Dedup  →  Categorize  →  Score", 13, TEXT, true));
        pipe.addView(text("Idea  →  Script  →  Production  →  Published  →  Performance", 13, TEXT, true));
        body.addView(pipe);

        LinearLayout state = card();
        state.addView(text("PRODUCTION STATE", 11, MUTED, true));
        LinearLayout r1 = row();
        TextView ideas = metric(r1, "IDEAS READY", "—");
        TextView scripts = metric(r1, "SCRIPTS READY", "NOT CONNECTED");
        state.addView(r1);
        LinearLayout r2 = row();
        TextView produced = metric(r2, "PRODUCED", "NOT CONNECTED");
        TextView uploaded = metric(r2, "UPLOADED", "NOT CONNECTED");
        state.addView(r2);
        scripts.setTextColor(WARN); produced.setTextColor(WARN); uploaded.setTextColor(WARN);
        body.addView(state);

        LinearLayout listCard = card();
        listCard.addView(text("TOP OPPORTUNITIES", 11, MUTED, true));
        TextView list = text("Belum ada ide.", 14, TEXT, false);
        list.setPadding(0, dp(8), 0, 0);
        listCard.addView(list);
        body.addView(listCard);

        apiAsync("GET", "/api/work/brief", null, false, (code, s) -> {
            try {
                JSONArray a = new JSONObject(s).optJSONArray("ideas");
                int n = a == null ? 0 : a.length();
                setMetric(ideas, String.valueOf(n), n > 0 ? OK : MUTED);
                if (n == 0) { list.setText("Belum ada ide. Jalankan research."); return; }
                StringBuilder x = new StringBuilder();
                for (int i = 0; i < Math.min(10, n); i++) {
                    JSONObject o = a.getJSONObject(i);
                    String title = dash(o.optString("Title", o.optString("title")));
                    String cat = dash(o.optString("Category", o.optString("category")));
                    double score = o.optDouble("Score", o.optDouble("score", 0));
                    x.append(i + 1).append(". ").append(title)
                            .append("\n   ").append(cat).append("  ·  score ").append(Math.round(score)).append("\n\n");
                }
                list.setText(x.toString().trim());
            } catch (Exception ignored) {}
        });
    }

    private void buildInsights(LinearLayout body) {
        body.addView(sectionTitle("Insights & Memory", "Performa channel dan pengetahuan yang sudah dikumpulkan HERMES WORK."));

        LinearLayout channel = card();
        channel.addView(text("MY CHANNEL", 11, MUTED, true));
        LinearLayout r1 = row();
        TextView conn = metric(r1, "CONNECTION", "—");
        TextView views = metric(r1, "VIEWS", "—");
        channel.addView(r1);
        LinearLayout r2 = row();
        TextView retention = metric(r2, "RETENTION", "—");
        TextView ctr = metric(r2, "CTR / ENGAGEMENT", "—");
        channel.addView(r2);
        LinearLayout r3 = row();
        TextView watch = metric(r3, "WATCH TIME", "—");
        TextView best = metric(r3, "BEST TOPIC", "—");
        channel.addView(r3);
        body.addView(channel);

        LinearLayout memory = card();
        memory.addView(text("MEMORY / KNOWLEDGE", 11, MUTED, true));
        LinearLayout m1 = row();
        TextView items = metric(m1, "RESEARCH ITEMS", "—");
        TextView unique = metric(m1, "UNIQUE KEYS", "—");
        memory.addView(m1);
        LinearLayout m2 = row();
        TextView success = metric(m2, "SUCCESSFUL", "—");
        TextView under = metric(m2, "UNDERPERFORM", "—");
        memory.addView(m2);
        LinearLayout m3 = row();
        TextView pending = metric(m3, "NOT PRODUCED", "—");
        TextView cats = metric(m3, "CATEGORIES", "—");
        memory.addView(m3);
        body.addView(memory);

        apiAsync("GET", "/api/work/channel", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(conn, dash(j.optString("state")), "CONNECTED".equals(j.optString("state")) ? OK : WARN);
                JSONObject m = j.optJSONObject("metrics");
                if (m == null) m = j;
                setMetric(views, value(m, "views"), TEXT);
                setMetric(retention, value(m, "retention"), TEXT);
                setMetric(ctr, value(m, "ctr"), TEXT);
                setMetric(watch, value(m, "watch_time"), TEXT);
                setMetric(best, value(m, "best_topic"), TEXT);
            } catch (Exception ignored) {}
        });
        apiAsync("GET", "/api/work/knowledge", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(items, value(j, "research_items"), TEXT);
                setMetric(unique, value(j, "unique_keys"), TEXT);
                setMetric(success, value(j, "successful"), WARN);
                setMetric(under, value(j, "underperforming"), WARN);
                setMetric(pending, value(j, "ideas_not_produced"), WARN);
                JSONObject c = j.optJSONObject("categories");
                setMetric(cats, c == null ? "0" : String.valueOf(c.length()), TEXT);
            } catch (Exception ignored) {}
        });
    }

    private void buildSystem(LinearLayout body) {
        body.addView(sectionTitle("System", "Status worker, modem priority, resource guard, dan automation."));

        LinearLayout device = card();
        device.addView(text("REDMI 5A / MODEM", 11, MUTED, true));
        LinearLayout r1 = row();
        TextView tether = metric(r1, "TETHER", "—");
        TextView ip = metric(r1, "IP", "—");
        device.addView(r1);
        LinearLayout r2 = row();
        TextView temp = metric(r2, "TEMP", "—");
        TextView ram = metric(r2, "FREE RAM", "—");
        device.addView(r2);
        LinearLayout r3 = row();
        TextView worker = metric(r3, "WORKER", "—");
        TextView bridge = metric(r3, "BRIDGE", "—");
        device.addView(r3);
        body.addView(device);

        LinearLayout auto = card();
        auto.addView(text("AUTOMATION", 11, MUTED, true));
        LinearLayout a1 = row();
        TextView schedule = metric(a1, "MORNING RESEARCH", "—");
        TextView guard = metric(a1, "GUARD", "—");
        auto.addView(a1);
        auto.addView(text("Dedup · READY", 13, OK, true));
        auto.addView(text("Categorization · READY", 13, OK, true));
        auto.addView(text("Trend Scoring · READY_V1", 13, OK, true));
        auto.addView(text("Local Reasoning · DEFERRED", 13, WARN, true));
        body.addView(auto);

        LinearLayout comps = card();
        comps.addView(text("COMPONENTS", 11, MUTED, true));
        TextView comp = text("Loading…", 13, TEXT, false);
        comp.setPadding(0, dp(8), 0, 0);
        comps.addView(comp);
        body.addView(comps);

        apiAsync("GET", "/api/work/status", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(tether, dash(j.optString("tether_state")), "UP".equals(j.optString("tether_state")) ? OK : BAD);
                setMetric(ip, dash(j.optString("tether_ip")), TEXT);
                setMetric(temp, String.format(Locale.US, "%.1f °C", j.optDouble("temperature_c")), j.optDouble("temperature_c") >= 44 ? BAD : OK);
                setMetric(ram, j.optInt("mem_available_mb") + " MB", j.optInt("mem_available_mb") < 220 ? BAD : OK);
                String w = j.optBoolean("safe_mode") ? "SAFE MODE" : (j.optBoolean("worker_paused") ? "PAUSED" : "READY");
                setMetric(worker, w, "READY".equals(w) ? OK : WARN);
                setMetric(bridge, j.optBoolean("bridge_enabled") ? "CONNECTED" : "OFF", j.optBoolean("bridge_enabled") ? OK : MUTED);
                JSONObject c = j.optJSONObject("components");
                if (c != null) {
                    StringBuilder x = new StringBuilder();
                    Iterator<String> it = c.keys();
                    while (it.hasNext()) {
                        String k = it.next();
                        x.append(k.toUpperCase(Locale.US).replace('_',' ')).append("  ·  ").append(c.optString(k)).append("\n");
                    }
                    comp.setText(x.toString().trim());
                }
            } catch (Exception ignored) {}
        });
        apiAsync("GET", "/api/work/schedule", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(schedule, j.optBoolean("enabled") ? dash(j.optString("schedule")) : "OFF", TEXT);
                setMetric(guard, j.optBoolean("guard_ready") ? "READY" : dash(j.optString("guard_reason")), j.optBoolean("guard_ready") ? OK : WARN);
            } catch (Exception ignored) {}
        });
    }

    private void buildUpdate(LinearLayout body) {
        body.addView(sectionTitle("Updater & Recovery", "Halaman terakhir khusus update, backup, rollback, safe mode, dan diagnostics."));

        LinearLayout rel = card();
        rel.addView(text("RELEASE STATUS", 11, MUTED, true));
        LinearLayout r = row();
        TextView current = metric(r, "CURRENT", "—");
        TextView previous = metric(r, "LAST GOOD", "—");
        rel.addView(r);
        body.addView(rel);

        LinearLayout conn = card();
        conn.addView(text("CONNECTION", 11, MUTED, true));
        EditText runtime = field("Runtime URL", runtimeUrl(), false);
        EditText token = field("ADMIN TOKEN", token(), true);
        conn.addView(runtime);
        conn.addView(token);
        Button save = actionButton("SAVE CONNECTION", false);
        conn.addView(save);
        body.addView(conn);

        LinearLayout actions = card();
        actions.addView(text("UPDATER", 11, MUTED, true));
        Button update = actionButton("CHECK / UPDATE NOW", true);
        Button backup = actionButton("BACKUP", false);
        Button rollback = actionButton("ROLLBACK", false);
        Button safe = actionButton("SAFE MODE", false);
        Button resume = actionButton("RESUME", false);
        Button recover = actionButton("RECOVER RUNTIME", false);
        Button diag = actionButton("DIAGNOSTICS", false);
        actions.addView(update); actions.addView(backup); actions.addView(rollback);
        actions.addView(safe); actions.addView(resume); actions.addView(recover); actions.addView(diag);
        TextView out = mono("Ready.");
        actions.addView(out);
        body.addView(actions);

        save.setOnClickListener(v -> {
            String u = runtime.getText().toString().trim();
            if (u.isEmpty()) u = DEFAULT_RUNTIME;
            prefs.edit().putString("runtime", clean(u)).putString("token", token.getText().toString().trim()).apply();
            out.setText("Connection saved.");
            refreshOnlineOnly();
        });

        update.setOnClickListener(v -> {
            save.performClick();
            update.setEnabled(false);
            out.setText("Checking release channel and updating…");
            apiAsync("POST", "/api/work/update", null, true, (code, s) -> {
                if (code >= 200 && code < 300) {
                    out.setText(s.trim());
                    out.append("\n\nHandoff scheduled. Waiting for health check…");
                    out.postDelayed(() -> {
                        loadRecovery(current, previous);
                        refreshOnlineOnly();
                        update.setEnabled(true);
                    }, 5000);
                } else {
                    out.setText("Native updater unavailable. Using bootstrap recovery updater…\n\n" + s.trim());
                    bootstrapFallbackUpdate(out, update, current, previous);
                }
            });
        });

        backup.setOnClickListener(v -> action("backup", out, current, previous));
        rollback.setOnClickListener(v -> confirm("Rollback ke last-good release?", () -> action("rollback", out, current, previous)));
        safe.setOnClickListener(v -> confirm("Aktifkan Safe Mode? Workload akan dipause, modem/control plane tetap hidup.", () -> action("safe_mode", out, current, previous)));
        resume.setOnClickListener(v -> action("resume", out, current, previous));
        recover.setOnClickListener(v -> recover(out, current, previous));
        diag.setOnClickListener(v -> apiAsync("GET", "/api/work/diagnostics", null, true, (code, s) -> out.setText(s.trim())));

        loadRecovery(current, previous);
    }

    private void bootstrapFallbackUpdate(TextView out, Button update, TextView current, TextView previous) {
        io.execute(() -> {
            try {
                String channelUrl = "https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/hermes-work-release-channel/hermes-work-runtime/channel.json";
                HttpResult ch = request("GET", channelUrl, null, false);
                if (ch.code != 200) throw new Exception("Channel HTTP " + ch.code);
                JSONObject j = new JSONObject(ch.body);
                String ver = j.getString("version");
                String bundle = j.getString("bundle");
                String sha = j.getString("sha256").toLowerCase(Locale.US);
                if (!ver.matches("[A-Za-z0-9._-]+") || !bundle.matches("[A-Za-z0-9._-]+") || !sha.matches("[0-9a-f]{64}")) {
                    throw new Exception("Invalid release metadata");
                }
                String raw = "https://raw.githubusercontent.com/Djaeger1/DJAEGER-Control-Center/hermes-work-release-channel/hermes-work-runtime/" + bundle;
                String cmd =
                        "ROOT=/data/adb/hermes_work; " +
                        "VER='" + ver + "'; URL='" + raw + "'; SHA='" + sha + "'; " +
                        "mkdir -p \"$ROOT/updates\" \"$ROOT/releases\"; " +
                        "TMP=\"$ROOT/updates/$VER.zip\"; STAGE=\"$ROOT/releases/.stage-$VER\"; DEST=\"$ROOT/releases/$VER\"; " +
                        "rm -f \"$TMP\"; " +
                        "/system/bin/wget -qO \"$TMP\" \"$URL\" || exit 10; " +
                        "GOT=$(sha256sum \"$TMP\" 2>/dev/null | awk '{print $1}'); [ \"$GOT\" = \"$SHA\" ] || exit 11; " +
                        "rm -rf \"$STAGE\" \"$DEST.new\"; mkdir -p \"$STAGE\" \"$DEST.new\"; " +
                        "if command -v unzip >/dev/null 2>&1; then unzip -oq \"$TMP\" -d \"$STAGE\" || exit 12; " +
                        "elif [ -x /data/adb/magisk/busybox ]; then /data/adb/magisk/busybox unzip -oq \"$TMP\" -d \"$STAGE\" || exit 12; " +
                        "elif command -v busybox >/dev/null 2>&1; then busybox unzip -oq \"$TMP\" -d \"$STAGE\" || exit 12; " +
                        "else exit 13; fi; " +
                        "[ -f \"$STAGE/manifest.json\" ] && [ -x \"$STAGE/payload/bin/workd\" -o -f \"$STAGE/payload/bin/workd\" ] || exit 14; " +
                        "cp \"$STAGE/manifest.json\" \"$DEST.new/manifest.json\" || exit 15; " +
                        "cp -R \"$STAGE/payload/.\" \"$DEST.new/\" || exit 15; " +
                        "chmod 755 \"$DEST.new/bin/workd\" \"$DEST.new/worker/tick.sh\" \"$DEST.new/worker/handoff.sh\" 2>/dev/null; " +
                        "CUR=$(cat \"$ROOT/current_release\" 2>/dev/null); [ -n \"$CUR\" ] && [ \"$CUR\" != \"$VER\" ] && printf '%s\\n' \"$CUR\" > \"$ROOT/previous_release\"; " +
                        "rm -rf \"$DEST\"; mv \"$DEST.new\" \"$DEST\" || exit 16; printf '%s\\n' \"$VER\" > \"$ROOT/current_release\"; " +
                        "PREV=$(cat \"$ROOT/previous_release\" 2>/dev/null); " +
                        "sh \"$DEST/worker/handoff.sh\" \"$ROOT\" \"$VER\" \"$PREV\" || exit 17; " +
                        "sleep 2; /system/bin/wget -qO- http://127.0.0.1:8766/api/work/status || exit 18";
                JSONObject body = new JSONObject();
                body.put("command", cmd);
                HttpResult ex = request("POST", bootstrapUrl() + "/api/exec", body.toString(), true);
                if (ex.code < 200 || ex.code >= 300) throw new Exception("Bootstrap HTTP " + ex.code + "\\n" + ex.body);
                ui(() -> {
                    out.setText("BOOTSTRAP UPDATE SUCCESS\\n\\n" + ex.body.trim());
                    loadRecovery(current, previous);
                    refreshOnlineOnly();
                    update.setEnabled(true);
                });
            } catch (Exception e) {
                ui(() -> {
                    out.setText("UPDATE FAILED\\n\\n" + e.getMessage());
                    update.setEnabled(true);
                });
            }
        });
    }

    private void loadRecovery(TextView current, TextView previous) {
        apiAsync("GET", "/api/work/recovery", null, false, (code, s) -> {
            try {
                JSONObject j = new JSONObject(s);
                setMetric(current, dash(j.optString("current")), TEXT);
                setMetric(previous, dash(j.optString("previous")), MUTED);
            } catch (Exception ignored) {}
        });
    }

    private void action(String a, TextView out, TextView current, TextView previous) {
        JSONObject j = new JSONObject();
        try { j.put("action", a); } catch (Exception ignored) {}
        apiAsync("POST", "/api/work/action", j.toString(), true, (code, s) -> {
            out.setText(s.trim());
            loadRecovery(current, previous);
            refreshOnlineOnly();
        });
    }

    private void recover(TextView out, TextView current, TextView previous) {
        out.setText("Recovering runtime…");
        io.execute(() -> {
            try {
                String cmd = "ROOT=/data/adb/hermes_work; VER=$(cat $ROOT/current_release 2>/dev/null); REL=$ROOT/releases/$VER; [ -x \"$REL/bin/workd\" ] || exit 7; PID=$ROOT/state/workd.pid; OLD=$(cat $PID 2>/dev/null); [ -n \"$OLD\" ] && kill \"$OLD\" 2>/dev/null; nohup \"$REL/bin/workd\" --root \"$ROOT\" --release \"$REL\" >>\"$ROOT/logs/workd.log\" 2>&1 & echo $! > \"$PID\"; sleep 2";
                JSONObject b = new JSONObject(); b.put("command", cmd);
                HttpResult r = request("POST", bootstrapUrl() + "/api/exec", b.toString(), true);
                ui(() -> {
                    out.setText(r.body.trim());
                    loadRecovery(current, previous);
                    refreshOnlineOnly();
                });
            } catch (Exception e) {
                ui(() -> out.setText("Recovery failed: " + e.getMessage()));
            }
        });
    }

    private void refreshOnlineOnly() {
        apiAsync("GET", "/api/work/status", null, false, (code, s) -> {
            if (code >= 200 && code < 300) {
                online.setText("● ONLINE"); online.setTextColor(OK);
            } else {
                online.setText("● OFFLINE"); online.setTextColor(BAD);
            }
        });
    }

    private interface ApiCallback { void done(int code, String body); }

    private void apiAsync(String method, String path, String body, boolean auth, ApiCallback cb) {
        io.execute(() -> {
            try {
                HttpResult r = request(method, runtimeUrl() + path, body, auth);
                ui(() -> cb.done(r.code, r.body));
            } catch (Exception e) {
                ui(() -> {
                    online.setText("● OFFLINE"); online.setTextColor(BAD);
                    cb.done(0, "ERROR: " + e.getMessage());
                });
            }
        });
    }

    private HttpResult request(String method, String target, String body, boolean auth) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(target).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(5000);
        c.setReadTimeout(60000);
        c.setUseCaches(false);
        c.setRequestProperty("Accept", "application/json, text/plain, */*");
        if (auth) c.setRequestProperty("X-Hermes-Token", token());
        if (body != null) {
            byte[] data = body.getBytes(StandardCharsets.UTF_8);
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            c.setFixedLengthStreamingMode(data.length);
            try (OutputStream os = c.getOutputStream()) { os.write(data); }
        } else if ("POST".equals(method)) {
            c.setDoOutput(true);
            c.setFixedLengthStreamingMode(0);
            try (OutputStream os = c.getOutputStream()) {}
        }
        int code = c.getResponseCode();
        InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
        StringBuilder sb = new StringBuilder();
        if (in != null) try (BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line; while ((line = br.readLine()) != null) sb.append(line).append('\n');
        }
        c.disconnect();
        return new HttpResult(code, sb.toString());
    }

    private String runtimeUrl() { return clean(prefs.getString("runtime", DEFAULT_RUNTIME)); }
    private String token() { return prefs.getString("token", "").trim(); }
    private String bootstrapUrl() {
        try {
            URL u = new URL(runtimeUrl());
            return u.getProtocol() + "://" + u.getHost() + ":8765";
        } catch (Exception e) { return DEFAULT_BOOTSTRAP; }
    }
    private String clean(String s) {
        s = s == null ? "" : s.trim();
        if (s.isEmpty()) s = DEFAULT_RUNTIME;
        if (!s.startsWith("http://") && !s.startsWith("https://")) s = "http://" + s;
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        return s;
    }

    private LinearLayout card() {
        LinearLayout x = new LinearLayout(this);
        x.setOrientation(LinearLayout.VERTICAL);
        x.setPadding(dp(14), dp(14), dp(14), dp(14));
        x.setBackgroundColor(PANEL);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 0, 0, dp(12));
        x.setLayoutParams(p);
        return x;
    }

    private LinearLayout row() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setPadding(0, dp(8), 0, 0);
        return r;
    }

    private TextView metric(LinearLayout row, String label, String initial) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(11), dp(10), dp(11), dp(10));
        box.setBackgroundColor(PANEL2);
        TextView k = text(label, 10, MUTED, true);
        TextView v = text(initial, 16, TEXT, true);
        v.setPadding(0, dp(4), 0, 0);
        box.addView(k); box.addView(v);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, -2, 1f);
        p.setMargins(0, 0, dp(6), dp(6));
        row.addView(box, p);
        return v;
    }

    private View sectionTitle(String title, String sub) {
        LinearLayout x = new LinearLayout(this);
        x.setOrientation(LinearLayout.VERTICAL);
        x.setPadding(dp(2), dp(4), dp(2), dp(12));
        x.addView(text(title, 22, TEXT, true));
        TextView s = text(sub, 13, MUTED, false);
        s.setPadding(0, dp(3), 0, 0);
        x.addView(s);
        return x;
    }

    private TextView text(String s, int sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(s);
        v.setTextSize(sp);
        v.setTextColor(color);
        if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return v;
    }

    private TextView mono(String s) {
        TextView v = text(s, 12, Color.rgb(205, 236, 212), false);
        v.setTypeface(Typeface.MONOSPACE);
        v.setTextIsSelectable(true);
        v.setPadding(dp(10), dp(10), dp(10), dp(10));
        v.setBackgroundColor(Color.rgb(5, 9, 13));
        return v;
    }

    private Button actionButton(String label, boolean primary) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setBackgroundColor(primary ? Color.rgb(35, 105, 216) : Color.rgb(31, 41, 54));
        b.setAllCaps(false);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(48));
        p.setMargins(0, dp(8), 0, 0);
        b.setLayoutParams(p);
        return b;
    }

    private Button navButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(10);
        b.setAllCaps(false);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(3), 0, dp(3), 0);
        return b;
    }

    private EditText field(String hint, String value, boolean secret) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setText(value);
        e.setTextColor(TEXT);
        e.setHintTextColor(MUTED);
        e.setSingleLine(true);
        e.setBackgroundColor(PANEL2);
        e.setPadding(dp(12), dp(10), dp(12), dp(10));
        if (secret) e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(50));
        p.setMargins(0, dp(8), 0, 0);
        e.setLayoutParams(p);
        return e;
    }

    private void setMetric(TextView v, String s, int color) {
        v.setText(dash(s));
        v.setTextColor(color);
    }

    private String dash(String s) { return (s == null || s.trim().isEmpty()) ? "—" : s; }
    private String value(JSONObject j, String k) {
        Object o = j.opt(k);
        return o == null || o == JSONObject.NULL ? "—" : String.valueOf(o);
    }
    private String val(JSONObject j, String k) { return value(j, k); }

    private void confirm(String msg, Runnable yes) {
        new AlertDialog.Builder(this).setTitle("HERMES WORK").setMessage(msg)
                .setNegativeButton("CANCEL", null)
                .setPositiveButton("CONTINUE", (d, w) -> yes.run()).show();
    }

    private void ui(Runnable r) { if (!destroyed) runOnUiThread(r); }
    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    @Override protected void onDestroy() {
        destroyed = true;
        io.shutdownNow();
        super.onDestroy();
    }

    static class HttpResult {
        final int code; final String body;
        HttpResult(int c, String b) { code = c; body = b == null ? "" : b; }
    }
}
