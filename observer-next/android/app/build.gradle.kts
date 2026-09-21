plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.djaeger.observer"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.djaeger.observer"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0-observer"
    }
}
