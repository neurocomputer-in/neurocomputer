import { createSlice, PayloadAction } from '@reduxjs/toolkit';

type ThemeId = 'neural-network' | 'deep-space' | 'digital-rain' | 'minimal-dark';
export type TabBarPosition = 'bottom' | 'top';
export type InterfaceMode = 'classic' | 'spatial';

/** Width in px of the terminal column when live voice mode is on a
 *  terminal tab. Shared between page.tsx (column width) and LiveSession
 *  (left offset) so they stay in lockstep and there's no gap or overlap. */
export const TERMINAL_LIVE_COL_PX = 1100;

export interface PaneState { id: string; activeCid: string | null }
const MAX_PANES = 3;
const DEFAULT_PANE_ID = 'p0';

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
  interfaceMode: InterfaceMode;
  focusedCid: string | null;
  /** True while VoiceCallPanel's fullscreen "live" mode is engaged.
   *  page.tsx uses it to reserve a narrow left column for terminal tabs
   *  so the xterm stays visible alongside the live voice UI. */
  liveMode: boolean;
  /** Split-pane state. In single-pane mode (length===1) everything
   *  behaves as before; UI chrome only appears when length > 1. */
  panes: PaneState[];
  focusedPaneId: string;
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
  interfaceMode: _readStored<InterfaceMode>('neuro_interface_mode', 'classic'),
  focusedCid: null,
  liveMode: false,
  panes: [{ id: DEFAULT_PANE_ID, activeCid: null }],
  focusedPaneId: DEFAULT_PANE_ID,
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
    setInterfaceMode(state, action: PayloadAction<InterfaceMode>) {
      state.interfaceMode = action.payload;
      if (typeof window !== 'undefined') {
        localStorage.setItem('neuro_interface_mode', JSON.stringify(action.payload));
      }
    },
    setFocusedCid(state, action: PayloadAction<string | null>) {
      state.focusedCid = action.payload;
    },
    setLiveMode(state, action: PayloadAction<boolean>) {
      state.liveMode = action.payload;
    },
    splitPane(state) {
      if (state.panes.length >= MAX_PANES) return;
      // Seed new pane with the focused pane's active cid so the user
      // immediately sees something instead of an empty frame.
      const seedCid = state.panes.find(p => p.id === state.focusedPaneId)?.activeCid ?? null;
      const id = 'p' + Date.now().toString(36);
      state.panes.push({ id, activeCid: seedCid });
      state.focusedPaneId = id;
    },
    closePane(state, action: PayloadAction<string>) {
      if (state.panes.length <= 1) return;
      const id = action.payload;
      state.panes = state.panes.filter(p => p.id !== id);
      if (state.focusedPaneId === id) {
        state.focusedPaneId = state.panes[0].id;
      }
    },
    setPaneActiveCid(state, action: PayloadAction<{ id: string; cid: string | null }>) {
      const pane = state.panes.find(p => p.id === action.payload.id);
      if (pane) pane.activeCid = action.payload.cid;
    },
    setFocusedPaneId(state, action: PayloadAction<string>) {
      if (state.panes.some(p => p.id === action.payload)) {
        state.focusedPaneId = action.payload;
      }
    },
  },
});

export const {
  setSidebarOpen, setSidebarWidth, setShowProjectCreate,
  setShowAgentDropdown, setConnectionStatus, setTtsAutoPlay, setTheme,
  setTabBarPosition, setLiveWallpaperEnabled,
  setInterfaceMode, setFocusedCid, setLiveMode,
  splitPane, closePane, setPaneActiveCid, setFocusedPaneId,
} = uiSlice.actions;
export default uiSlice.reducer;
