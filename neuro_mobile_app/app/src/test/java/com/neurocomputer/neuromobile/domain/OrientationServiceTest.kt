package com.neurocomputer.neuromobile.domain

import android.view.Surface
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OrientationServiceTest {
    @Test
    fun rotation_0_maps_to_portrait() {
        assertEquals(
            OrientationService.OrientationState.PORTRAIT,
            OrientationService.fromSurfaceRotation(Surface.ROTATION_0),
        )
    }

    @Test
    fun rotation_90_maps_to_landscape_left() {
        // the user's preferred landscape direction
        assertEquals(
            OrientationService.OrientationState.LANDSCAPE_LEFT,
            OrientationService.fromSurfaceRotation(Surface.ROTATION_90),
        )
    }

    @Test
    fun rotation_180_is_ignored() {
        assertNull(OrientationService.fromSurfaceRotation(Surface.ROTATION_180))
    }

    @Test
    fun rotation_270_is_ignored() {
        // the other landscape direction — user doesn't want this to trigger
        assertNull(OrientationService.fromSurfaceRotation(Surface.ROTATION_270))
    }

    @Test
    fun unknown_rotation_returns_null() {
        assertNull(OrientationService.fromSurfaceRotation(999))
    }
}
