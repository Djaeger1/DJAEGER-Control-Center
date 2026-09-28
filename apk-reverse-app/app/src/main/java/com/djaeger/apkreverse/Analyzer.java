package com.djaeger.apkreverse;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public final class Analyzer {
    private Analyzer() {}

    public static final class Result {
        public long bytesRead;
        public String sha256;
        public int entryCount;
        public int dexCount;
        public int nativeCount;
        public boolean manifestPresent;
        public int signatureFileCount;
        public long uncompressedBytes;
        public final List<String> dexFiles = new ArrayList<>();
        public final List<String> nativeFiles = new ArrayList<>();
        public final Set<String> nativeAbis = new LinkedHashSet<>();
        public final List<String> signals = new ArrayList<>();
        public final List<String> sampleStrings = new ArrayList<>();

        public String toReport(String fileName) {
            StringBuilder b = new StringBuilder();
            b.append("DJAEGER APK Reverse\n");
            b.append("==================\n");
            b.append("File: ").append(fileName).append('\n');
            b.append("Size: ").append(formatBytes(bytesRead)).append('\n');
            b.append("SHA-256: ").append(sha256).append('\n');
            b.append("Entries: ").append(entryCount).append('\n');
            b.append("Uncompressed total: ").append(formatBytes(uncompressedBytes)).append('\n');
            b.append("AndroidManifest.xml: ").append(manifestPresent ? "present" : "missing").append('\n');
            b.append("DEX files: ").append(dexCount).append('\n');
            for (String s : dexFiles) b.append("  - ").append(s).append('\n');
            b.append("Native .so files: ").append(nativeCount).append('\n');
            if (!nativeAbis.isEmpty()) b.append("Native ABIs: ").append(join(nativeAbis)).append('\n');
            for (String s : nativeFiles) b.append("  - ").append(s).append('\n');
            b.append("Signature entries: ").append(signatureFileCount).append('\n');
            b.append("\nStatic signals:\n");
            if (signals.isEmpty()) b.append("  none detected by built-in heuristics\n");
            else for (String s : signals) b.append("  - ").append(s).append('\n');
            if (!sampleStrings.isEmpty()) {
                b.append("\nSample printable strings:\n");
                for (String s : sampleStrings) b.append("  - ").append(s).append('\n');
            }
            b.append("\nNote: v0.1 performs local, read-only APK reconnaissance.\n");
            b.append("It does not patch, bypass security controls, or modify the selected APK.\n");
            return b.toString();
        }
    }

    public static Result analyze(InputStream source) throws IOException {
        Result r = new Result();
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IOException("SHA-256 unavailable", e);
        }

        CountingDigestInputStream counted = new CountingDigestInputStream(
                new BufferedInputStream(source, 64 * 1024), digest);
        ZipInputStream zip = new ZipInputStream(counted);
        ZipEntry entry;
        byte[] buffer = new byte[64 * 1024];

        while ((entry = zip.getNextEntry()) != null) {
            r.entryCount++;
            String name = entry.getName();
            String lower = name.toLowerCase(Locale.ROOT);

            if ("AndroidManifest.xml".equals(name)) r.manifestPresent = true;

            if (name.startsWith("META-INF/") &&
                    (name.endsWith(".RSA") || name.endsWith(".DSA") ||
                     name.endsWith(".EC") || name.endsWith(".SF"))) {
                r.signatureFileCount++;
            }

            if (lower.matches("classes\\d*\\.dex")) {
                r.dexCount++;
                if (r.dexFiles.size() < 40) r.dexFiles.add(name);
                scanDexEntry(zip, r, buffer);
            } else if (lower.startsWith("lib/") && lower.endsWith(".so")) {
                r.nativeCount++;
                if (r.nativeFiles.size() < 80) r.nativeFiles.add(name);
                String[] parts = name.split("/");
                if (parts.length >= 3) r.nativeAbis.add(parts[1]);
                drain(zip, buffer);
            } else {
                if (lower.contains("frida")) addSignal(r, "entry name contains 'frida'");
                if (lower.contains("xposed")) addSignal(r, "entry name contains 'xposed'");
                drain(zip, buffer);
            }

            if (entry.getSize() > 0) r.uncompressedBytes += entry.getSize();
            zip.closeEntry();
        }

        zip.close();
        r.bytesRead = counted.count;
        r.sha256 = hex(digest.digest());

        if (r.dexCount == 0) addSignal(r, "no classes*.dex entry detected");
        if (r.nativeCount > 0) addSignal(r, "APK contains native libraries");
        if (r.signatureFileCount == 0) addSignal(r, "no conventional META-INF signature entries detected");
        return r;
    }

    private static void scanDexEntry(ZipInputStream zip, Result r, byte[] buffer) throws IOException {
        StringBuilder ascii = new StringBuilder();
        int n;
        while ((n = zip.read(buffer)) != -1) {
            for (int i = 0; i < n; i++) {
                int c = buffer[i] & 0xFF;
                if (c >= 32 && c <= 126) {
                    ascii.append((char)c);
                    if (ascii.length() > 96) ascii.delete(0, ascii.length() - 96);
                } else {
                    if (ascii.length() >= 8 && r.sampleStrings.size() < 80) {
                        String s = ascii.toString();
                        if (interestingString(s) && !r.sampleStrings.contains(s)) {
                            r.sampleStrings.add(s);
                            if (s.toLowerCase(Locale.ROOT).contains("frida")) addSignal(r, "DEX string contains 'frida'");
                            if (s.toLowerCase(Locale.ROOT).contains("xposed")) addSignal(r, "DEX string contains 'xposed'");
                        }
                    }
                    ascii.setLength(0);
                }
            }
        }
    }

    private static boolean interestingString(String s) {
        String v = s.toLowerCase(Locale.ROOT);
        return v.contains("http") || v.contains("certificate") || v.contains("signature") ||
                v.contains("root") || v.contains("debug") || v.contains("frida") ||
                v.contains("xposed") || v.contains("dex") || v.contains("ssl");
    }

    private static void drain(InputStream in, byte[] buffer) throws IOException {
        while (in.read(buffer) != -1) {}
    }

    private static void addSignal(Result r, String signal) {
        if (!r.signals.contains(signal) && r.signals.size() < 30) r.signals.add(signal);
    }

    private static String hex(byte[] data) {
        StringBuilder b = new StringBuilder(data.length * 2);
        for (byte value : data) b.append(String.format(Locale.US, "%02x", value & 0xFF));
        return b.toString();
    }

    private static String formatBytes(long n) {
        if (n < 1024) return n + " B";
        double v = n;
        String[] units = {"KB", "MB", "GB"};
        for (String unit : units) {
            v /= 1024.0;
            if (v < 1024.0) return String.format(Locale.US, "%.2f %s", v, unit);
        }
        return String.format(Locale.US, "%.2f TB", v / 1024.0);
    }

    private static String join(Set<String> set) {
        StringBuilder b = new StringBuilder();
        boolean first = true;
        for (String s : set) {
            if (!first) b.append(", ");
            b.append(s);
            first = false;
        }
        return b.toString();
    }

    private static final class CountingDigestInputStream extends InputStream {
        private final InputStream delegate;
        private final MessageDigest digest;
        long count;

        CountingDigestInputStream(InputStream delegate, MessageDigest digest) {
            this.delegate = delegate;
            this.digest = digest;
        }

        @Override public int read() throws IOException {
            int x = delegate.read();
            if (x != -1) {
                digest.update((byte) x);
                count++;
            }
            return x;
        }

        @Override public int read(byte[] b, int off, int len) throws IOException {
            int n = delegate.read(b, off, len);
            if (n > 0) {
                digest.update(b, off, n);
                count += n;
            }
            return n;
        }

        @Override public void close() throws IOException {
            delegate.close();
        }
    }
}
