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
        versionCode = 2
        versionName = "1.0.1-observer-ai"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}
