plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    // Step 7: uncomment after dropping google-services.json into app/
    // id("com.google.gms.google-services") version "4.4.2" apply false
}
