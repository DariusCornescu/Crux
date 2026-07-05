package com.darius.splitrail

import android.app.Application
import com.darius.splitrail.push.PushRegistrar

/** Application entry point (cf. ListManagerApp.kt). */
class SplitrailApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // No-op until Firebase is configured — see README step 7 notes.
        PushRegistrar.register()
    }
}
