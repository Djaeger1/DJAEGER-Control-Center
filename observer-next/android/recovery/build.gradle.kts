plugins {
    id("com.android.application")
}

android {
    namespace = "com.djaeger.recovery"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.djaeger.recovery"
        minSdk = 26
        targetSdk = 33
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isDebuggable = false
            isJniDebuggable = false
            isMinifyEnabled = false
            isShrinkResources = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
