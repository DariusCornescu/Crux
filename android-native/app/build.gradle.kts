plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    id("com.google.gms.google-services")
}

android {
    namespace = "com.darius.crux"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.darius.crux"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.2.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.navigation.compose)

    // Network stack (same libraries/style as ListManagerApp)
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coroutines + ViewModel/Compose bridges
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")

    // On-device cache for the philosophy zone (last quote/reflection survive restarts)
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Health Connect — real sleep / resting HR / HRV / steps for CONDITIONS + readiness.
    // Pinned to alpha10: it is the newest release that still builds on compileSdk 35 +
    // AGP 8.7.3. 1.1.0-rc03 / stable require compileSdk 36 and AGP 8.9.1+ — do NOT bump
    // this without also bumping compileSdk and AGP together (see gradle/libs.versions.toml).
    implementation("androidx.health.connect:connect-client:1.1.0-alpha10")

    // FCM (step 7) — compiles without Firebase config; runtime is guarded
    implementation("com.google.firebase:firebase-messaging:24.1.0")

    debugImplementation(libs.androidx.compose.ui.tooling)
}
