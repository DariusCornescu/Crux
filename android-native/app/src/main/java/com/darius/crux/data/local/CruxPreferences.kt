package com.darius.crux.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "crux_prefs")

/**
 * Small on-device cache so the philosophy zone never shows blank on a cold or
 * offline launch: the last-seen quote and reflection persist across restarts.
 * Initialized once from [com.darius.crux.CruxApp.onCreate].
 */
object CruxPreferences {
    private lateinit var appContext: Context

    fun init(context: Context) {
        appContext = context.applicationContext
    }

    private val QUOTE = stringPreferencesKey("quote_text")
    private val REFLECTION = stringPreferencesKey("reflection_text")

    suspend fun saveQuote(text: String) {
        appContext.dataStore.edit { it[QUOTE] = text }
    }

    suspend fun lastQuote(): String? =
        appContext.dataStore.data.map { it[QUOTE] }.first()

    suspend fun saveReflection(text: String) {
        appContext.dataStore.edit { it[REFLECTION] = text }
    }

    suspend fun lastReflection(): String? =
        appContext.dataStore.data.map { it[REFLECTION] }.first()
}
