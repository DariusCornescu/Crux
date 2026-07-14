package com.darius.crux

import android.app.Application
import com.darius.crux.data.health.HealthConnectManager
import com.darius.crux.data.local.CruxPreferences
import com.darius.crux.push.PushRegistrar
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** Application entry point (cf. ListManagerApp.kt). */
class CruxApp : Application() {
    override fun onCreate() {
        super.onCreate()
        CruxPreferences.init(this)
        // No-op until Firebase is configured — see README step 7 notes.
        PushRegistrar.register()
        // Pull fresh Health Connect data on launch (no-op until permissions granted).
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { HealthConnectManager(this@CruxApp).sync() }
        }
    }
}
