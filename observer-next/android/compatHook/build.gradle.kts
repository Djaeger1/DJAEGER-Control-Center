plugins {
    id("com.android.application")
}

android {
    namespace = "com.djaeger.compat"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.djaeger.compat.buildonly"
        minSdk = 26
        targetSdk = 33
        versionCode = 1
        versionName = "1.0"
        ndk { abiFilters += listOf("arm64-v8a") }
        externalNativeBuild {
            cmake {
                cppFlags += listOf("-std=c++17", "-fvisibility=hidden")
                arguments += listOf("-DANDROID_STL=c++_static")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    ndkVersion = "27.0.12077973"
}

dependencies {
    implementation("top.canyie.pine:core:0.3.0")
}
