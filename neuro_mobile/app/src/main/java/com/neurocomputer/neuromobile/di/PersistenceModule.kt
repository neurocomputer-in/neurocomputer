package com.neurocomputer.neuromobile.di

import android.content.Context
import com.neurocomputer.neuromobile.data.persistence.OsPersistence
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object PersistenceModule {
    @Provides @Singleton
    fun provideOsPersistence(@ApplicationContext ctx: Context) = OsPersistence(ctx)
}
