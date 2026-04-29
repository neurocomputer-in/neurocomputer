package com.neurocomputer.neuromobile.data.model

import kotlinx.serialization.Serializable

@Serializable
data class WindowTab(
    val id: String,
    val cid: String,
    val appId: AppId,
    val title: String,
    val type: TabType,
)
