package com.darius.crux.network

object ApiConfig {
    // TODO(domain): replace with the real domain once the app is deployed
    // (App Platform gives you https://<app>.ondigitalocean.app, or use your own
    // domain — see backend-fastapi/docs/DEPLOY.md), then rebuild the APK.
    // Production backend behind HTTPS.
    // Local dev alternatives: emulator "http://10.0.2.2:8000/",
    // LAN device "http://<pc-lan-ip>:8000/".
    const val BASE_URL = "https://your-domain.example/"
}
