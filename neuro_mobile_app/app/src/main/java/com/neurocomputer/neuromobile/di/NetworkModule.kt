package com.neurocomputer.neuromobile.di

import android.content.Context
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.repository.StartupRepository
import com.neurocomputer.neuromobile.data.service.OcrService
import com.neurocomputer.neuromobile.data.service.OpenClawService
import com.neurocomputer.neuromobile.data.service.VoiceService
import com.neurocomputer.neuromobile.data.service.WebSocketService
import com.neurocomputer.neuromobile.data.service.WindSurfService
import com.neurocomputer.neuromobile.data.service.LiveKitService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideBackendUrlRepository(
        @ApplicationContext context: Context
    ): BackendUrlRepository {
        return BackendUrlRepository(context)
    }

    @Provides
    @Singleton
    fun provideStartupRepository(): StartupRepository {
        return StartupRepository()
    }

    @Provides
    @Singleton
    fun provideWebSocketService(
        backendUrlRepository: BackendUrlRepository
    ): WebSocketService {
        return WebSocketService(backendUrlRepository)
    }

    @Provides
    @Singleton
    fun provideVoiceService(
        backendUrlRepository: BackendUrlRepository
    ): VoiceService {
        return VoiceService(backendUrlRepository)
    }

    @Provides
    @Singleton
    fun provideOcrService(
        @ApplicationContext context: Context
    ): OcrService {
        return OcrService(context)
    }

    @Provides
    @Singleton
    fun provideWindSurfService(
        backendUrlRepository: BackendUrlRepository
    ): WindSurfService {
        return WindSurfService(backendUrlRepository)
    }

    @Provides
    @Singleton
    fun provideOpenClawService(
        backendUrlRepository: BackendUrlRepository
    ): OpenClawService {
        return OpenClawService(backendUrlRepository)
    }
}
