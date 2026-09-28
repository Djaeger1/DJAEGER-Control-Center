package com.djaeger.apkreverse;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import org.junit.Test;

public class AnalyzerTest {
    @Test
    public void analyzesZipShapeDexNativeAndSignature() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ZipOutputStream zip = new ZipOutputStream(bytes);
        put(zip, "AndroidManifest.xml", new byte[] {1, 2, 3});
        put(zip, "classes.dex", "dex certificate https://example.test ssl root".getBytes(StandardCharsets.UTF_8));
        put(zip, "lib/arm64-v8a/libfoo.so", new byte[] {0, 1, 2, 3});
        put(zip, "META-INF/CERT.RSA", new byte[] {1, 2});
        zip.close();

        Analyzer.Result r = Analyzer.analyze(new ByteArrayInputStream(bytes.toByteArray()));

        assertEquals(4, r.entryCount);
        assertEquals(1, r.dexCount);
        assertEquals(1, r.nativeCount);
        assertTrue(r.nativeAbis.contains("arm64-v8a"));
        assertTrue(r.manifestPresent);
        assertEquals(1, r.signatureFileCount);
        assertEquals(64, r.sha256.length());
        assertTrue(r.bytesRead > 0);
        assertTrue(r.signals.size() > 0);
    }

    @Test
    public void reportIsUserReadable() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ZipOutputStream zip = new ZipOutputStream(bytes);
        put(zip, "classes.dex", "hello http certificate".getBytes(StandardCharsets.UTF_8));
        zip.close();

        Analyzer.Result r = Analyzer.analyze(new ByteArrayInputStream(bytes.toByteArray()));
        String report = r.toReport("fixture.apk");

        assertTrue(report.contains("fixture.apk"));
        assertTrue(report.contains("SHA-256"));
        assertTrue(report.contains("DEX files: 1"));
        assertTrue(report.contains("read-only"));
    }

    private static void put(ZipOutputStream zip, String name, byte[] data) throws Exception {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(data);
        zip.closeEntry();
    }
}
