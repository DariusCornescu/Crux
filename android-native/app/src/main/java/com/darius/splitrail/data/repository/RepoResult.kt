package com.darius.splitrail.data.repository

/**
 * Typed repository result — adapted from ListManagerApp's RepoResult.
 * Splitrail has no offline queue yet (no Room cache), so the read-side
 * variant is just Success/Error; QueuedOffline joins when Room lands.
 */
sealed class RepoResult<out T> {
    data class Success<T>(val data: T) : RepoResult<T>()
    data class Error(val message: String) : RepoResult<Nothing>()
}
