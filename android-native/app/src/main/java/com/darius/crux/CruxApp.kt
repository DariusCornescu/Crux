package com.darius.crux

import android.app.Application
import com.darius.crux.push.PushRegistrar

/** Application entry point (cf. ListManagerApp.kt). */
class CruxApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // No-op until Firebase is configured — see README step 7 notes.
        PushRegistrar.register()
    }
}
