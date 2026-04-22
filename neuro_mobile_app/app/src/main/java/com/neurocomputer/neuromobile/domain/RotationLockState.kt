package com.neurocomputer.neuromobile.domain

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** Shared lock flag for rotation. Toggled by RotationLockButton, read by OrientationService. */
@Singleton
class RotationLockState @Inject constructor() {
    private val _locked = MutableStateFlow(false)
    val locked: StateFlow<Boolean> = _locked

    fun toggle(): Boolean {
        _locked.value = !_locked.value
        return _locked.value
    }

    fun set(value: Boolean) { _locked.value = value }
}
