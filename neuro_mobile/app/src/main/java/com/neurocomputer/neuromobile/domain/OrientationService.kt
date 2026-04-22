package com.neurocomputer.neuromobile.domain

import android.content.Context
import android.view.Surface
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Translates Android's Display.rotation (the same signal the OS uses to
 * rotate the UI) into one of 4 orientation states and forwards the
 * result to the callback registered in [start]. State changes are
 * deduplicated and suppressed while the shared [RotationLockState] is
 * locked.
 *
 * Driven by a Compose config-change observer in the screen — NOT a raw
 * sensor listener. This is intentional: raw rotation-vector readings
 * flap around the landscape/portrait threshold and caused repeated
 * orientation emissions while the phone was held still. Display.rotation
 * already applies Android's sensor smoothing + respects auto-rotate.
 */
@Singleton
class OrientationService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val lockState: RotationLockState,
) {

    enum class OrientationState(val wire: String) {
        PORTRAIT("portrait"),
        LANDSCAPE_LEFT("landscape-left"),
        LANDSCAPE_RIGHT("landscape-right"),
        PORTRAIT_INVERTED("portrait-inverted"),
    }

    private var listener: ((OrientationState, Boolean) -> Unit)? = null
    private var lastEmitted: OrientationState? = null

    fun start(onState: (OrientationState, Boolean) -> Unit) {
        listener = onState
        lastEmitted = null
        android.util.Log.d(TAG, "start() — orientation callback registered")
    }

    /**
     * Re-fire the most recently classified orientation even if it matches
     * [lastEmitted]. Used after screen-share starts: the FIRST orientation
     * message can lose a race with the server's data-channel handler
     * registration, so we resend it after a short delay.
     */
    fun resendLast() {
        val s = lastEmitted ?: return
        if (lockState.locked.value) return
        android.util.Log.d(TAG, "resendLast state=$s")
        listener?.invoke(s, false)
    }

    fun stop() {
        listener = null
        lastEmitted = null
        android.util.Log.d(TAG, "stop()")
    }

    fun setLock(on: Boolean) {
        lockState.set(on)
        android.util.Log.d(TAG, "setLock($on)")
        if (on) lastEmitted?.let { listener?.invoke(it, true) }
    }

    /**
     * Called by the Composable whenever the Activity's configuration
     * changes (or at least once on screen-mode entry) with the current
     * Surface.ROTATION_* value.
     */
    fun onRotationChanged(surfaceRotation: Int) {
        val state = fromSurfaceRotation(surfaceRotation) ?: return
        if (lockState.locked.value) {
            android.util.Log.d(TAG, "rotation=$surfaceRotation suppressed (locked)")
            return
        }
        if (state == lastEmitted) return
        lastEmitted = state
        android.util.Log.d(TAG, "emit state=$state (rotation=$surfaceRotation)")
        listener?.invoke(state, false)
    }

    companion object {
        private const val TAG = "OrientationService"

        /**
         * Only the two rotations the user actually uses emit events:
         *   ROTATION_0  → PORTRAIT        (natural portrait)
         *   ROTATION_90 → LANDSCAPE_LEFT  (the "left" side rotation on this device)
         *
         * ROTATION_270 (other landscape) and ROTATION_180 (upside-down)
         * return null so the PC does NOT rotate in those directions.
         */
        internal fun fromSurfaceRotation(rotation: Int): OrientationState? = when (rotation) {
            Surface.ROTATION_0  -> OrientationState.PORTRAIT
            Surface.ROTATION_90 -> OrientationState.LANDSCAPE_LEFT
            else -> null
        }
    }
}
