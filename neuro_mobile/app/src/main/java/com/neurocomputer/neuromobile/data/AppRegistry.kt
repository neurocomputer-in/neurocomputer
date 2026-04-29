package com.neurocomputer.neuromobile.data

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.StickyNote2
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import com.neurocomputer.neuromobile.R
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.data.model.TabType

/**
 * Either a Material vector icon or a drawable resource. Drawable gets priority
 * at render time; vector is the fallback. Most "system" apps (Terminal, IDE,
 * etc.) keep using the material icons; the four branded apps and the desktop
 * launcher use real logo PNGs.
 */
data class AppDef(
    val id: AppId,
    val name: String,
    val icon: ImageVector,
    val color: Color,
    val agentType: String?,
    val tabType: TabType,
    val pinned: Boolean,
    val iconResId: Int? = null,
)

val APP_LIST: List<AppDef> = listOf(
    AppDef(AppId.NEURO,          "Neuro",           Icons.Default.Psychology,                  Color(0xFF8B5CF6), "neuro",        TabType.CHAT,    true,  iconResId = R.drawable.logo),
    AppDef(AppId.OPENCLAW,       "OpenClaw",        Icons.Default.Language,                    Color(0xFFf97316), "openclaw",     TabType.CHAT,    true,  iconResId = R.drawable.openclaw_logo),
    AppDef(AppId.OPENCODE,       "OpenCode",        Icons.Default.Code,                        Color(0xFF3b82f6), "opencode",     TabType.CHAT,    true,  iconResId = R.drawable.opencode_logo),
    AppDef(AppId.NEUROUPWORK,    "NeuroUpwork",     Icons.Default.Work,                        Color(0xFF14b8a6), "neuroupwork",  TabType.CHAT,    true,  iconResId = R.drawable.upwork_logo),
    AppDef(AppId.NL_DEV,         "NL Dev",          Icons.Default.AutoAwesome,                 Color(0xFF22d3ee), "nl_dev",       TabType.CHAT,    true),
    AppDef(AppId.TERMINAL,       "Terminal",        Icons.Default.Terminal,                    Color(0xFF6b7280), null,           TabType.TERMINAL,true),
    AppDef(AppId.IDE,            "IDE",             Icons.Default.Layers,                      Color(0xFFa855f7), null,           TabType.IDE,     true),
    AppDef(AppId.NEURODESKTOP,   "Desktop",         Icons.Default.Tv,                          Color(0xFF1d4ed8), null,           TabType.DESKTOP, true,  iconResId = R.drawable.logo),
    AppDef(AppId.NEURORESEARCH,  "NeuroResearch",   Icons.Default.Search,                      Color(0xFF0ea5e9), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROWRITE,     "NeuroWrite",      Icons.Default.Edit,                        Color(0xFFec4899), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEURODATA,      "NeuroData",       Icons.Default.BarChart,                    Color(0xFFf59e0b), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROFILES,     "NeuroFiles",      Icons.Default.Folder,                      Color(0xFF84cc16), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROEMAIL,     "NeuroEmail",      Icons.Default.Email,                       Color(0xFF8b5cf6), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROCALENDAR,  "NeuroCalendar",   Icons.Default.CalendarMonth,               Color(0xFF10b981), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEURONOTES,     "NeuroNotes",      Icons.AutoMirrored.Filled.StickyNote2,     Color(0xFFf97316), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROBROWSE,    "NeuroBrowse",     Icons.Default.Explore,                     Color(0xFF6366f1), "openclaw",     TabType.CHAT,    false),
    AppDef(AppId.NEUROVOICE,     "NeuroVoice",      Icons.Default.Mic,                         Color(0xFFe11d48), "neuro",        TabType.CHAT,    false),
    AppDef(AppId.NEUROTRANSLATE, "NeuroTranslate",  Icons.Default.Translate,                   Color(0xFF06b6d4), "neuro",        TabType.CHAT,    false),
)

val APP_MAP: Map<AppId, AppDef> = APP_LIST.associateBy { it.id }
