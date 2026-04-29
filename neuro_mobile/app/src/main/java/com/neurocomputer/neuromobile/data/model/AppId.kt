package com.neurocomputer.neuromobile.data.model

import kotlinx.serialization.Serializable

@Serializable
enum class AppId {
    NEURO, OPENCLAW, OPENCODE, NEUROUPWORK, NL_DEV,
    TERMINAL, IDE, NEURODESKTOP,
    NEURORESEARCH, NEUROWRITE, NEURODATA, NEUROFILES,
    NEUROEMAIL, NEUROCALENDAR, NEURONOTES, NEUROBROWSE,
    NEUROVOICE, NEUROTRANSLATE
}
