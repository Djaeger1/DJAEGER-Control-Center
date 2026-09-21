plugins {
    id("com.android.application")
}

android {
    namespace = "com.djaeger.recovery2"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.djaeger.recovery2"
        minSdk = 26
        targetSdk = 33
        versionCode = 2
        versionName = "2.0.0"
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
