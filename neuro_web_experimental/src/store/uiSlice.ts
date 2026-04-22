import { createSlice, PayloadAction } from '@reduxjs/toolkit';

type ThemeId = 'neural-network' | 'deep-space' | 'digital-rain' | 'minimal-dark';
export type TabBarPosition = 'bottom' | 'top';

interface UIState {
  sidebarOpen: boolean;
  sidebarWidth: number;
  showProjectCreate: boolean;
  showAgentDropdown: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  ttsAutoPlay: boolean;
  theme: ThemeId;
  tabBarPosition: TabBarPosition;
  liveWallpaperEnabled: boolean;
}

function _readStored<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    return JSON.parse(raw) as T;
  } catch { return fallback; }
}

const initialState: UIState = {
  sidebarOpen: true,
  sidebarWidth: 260,
  showProjectCreate: false,
  showAgentDropdown: false,
  connectionStatus: 'disconnected',
  ttsAutoPlay: false,
  theme: 'neural-network' as ThemeId,
  tabBarPosition: _readStored<TabBarPosition>('neuro_tabbar_pos', 'bottom'),
  liveWallpaperEnabled: _readStored<boolean>('neuro_live_wallpaper', true),
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setSidebarOpen(state, action: PayloadAction<boolean>) {
      state.sidebarOpen = action.payload;
    },
    setSidebarWidth(state, action: PayloadAction<number>) {
      state.sidebarWidth = Math.max(180, Math.min(400, action.payload));
    },
    setShowProjectCreate(state, action: PayloadAction<boolean>) {
      state.showProjectCreate = action.payload;
    },
    setShowAgentDropdown(state, action: PayloadAction<boolean>) {
      state.showAgentDropdown = action.payload;
    },
    setConnectionStatus(state, action: PayloadAction<UIState['connectionStatus']>) {
      state.connectionStatus = action.payload;
    },
    setTtsAutoPlay(state, action: PayloadAction<boolean>) {
      state.ttsAutoPlay = action.payload;
    },
    setTheme(state, action: PayloadAction<ThemeId>) {
      state.theme = action.payload;
      if (typeof window !== 'undefined') localStorage.setItem('neuro_theme', action.payload);
    },
    setTabBarPosition(state, action: PayloadAction<TabBarPosition>) {
      state.tabBarPosition = action.payload;
      if (typeof window !== 'undefined') {
        localStorage.setItem('neuro_tabbar_pos', JSON.stringify(action.payload));
      }
    },
    setLiveWallpaperEnabled(state, action: PayloadAction<boolean>) {
      state.liveWallpaperEnabled = action.payload;
      if (typeof window !== 'undefined') {
        localStorage.setItem('neuro_live_wallpaper', JSON.stringify(action.payload));
      }
    },
  },
});

export const {
  setSidebarOpen, setSidebarWidth, setShowProjectCreate,
  setShowAgentDropdown, setConnectionStatus, setTtsAutoPlay, setTheme,
  setTabBarPosition, setLiveWallpaperEnabled,
} = uiSlice.actions;
export default uiSlice.reducer;
