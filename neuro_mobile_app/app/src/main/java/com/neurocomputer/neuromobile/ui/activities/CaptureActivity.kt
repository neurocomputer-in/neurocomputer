package com.neurocomputer.neuromobile.ui.activities

import android.app.Activity
import android.content.Intent
import android.graphics.PixelFormat
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import com.neurocomputer.neuromobile.data.service.OverlayService
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class CaptureActivity : ComponentActivity() {

    private lateinit var projectionManager: MediaProjectionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Transparent activity
        window.setFormat(PixelFormat.TRANSLUCENT)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        window.setDimAmount(0f)
        
        projectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(projectionManager.createScreenCaptureIntent(), REQUEST_CODE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == REQUEST_CODE) {
            if (resultCode == RESULT_OK && data != null) {
                Log.d("CaptureActivity", "Permission granted, forwarding to OverlayService")
                // DO NOT call getMediaProjection here on Android 14!
                // Forward the raw data to the Service instead.
                val intent = Intent(this, OverlayService::class.java).apply {
                    action = OverlayService.ACTION_RECV_PROJECTION_DATA
                    putExtra("RESULT_CODE", resultCode)
                    putExtra("RESULT_DATA", data)
                }
                startService(intent)
            } else {
                Log.e("CaptureActivity", "MediaProjection permission denied")
            }
            finish()
        }
    }

    companion object {
        private const val REQUEST_CODE = 100
    }
}
