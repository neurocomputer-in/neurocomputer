import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WindowTab } from '@/types';

export interface WindowState {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  minimized: boolean;
  maximized: boolean;
  prevBounds?: { x: number; y: number; width: number; height: number } | null;
  tabs: WindowTab[];
  activeTabId: string;
}

interface OSState {
  launcherOpen: boolean;
  windows: WindowState[];
  activeWindowId: string | null;
  nextZIndex: number;
  closedCids: string[];
}

const initialState: OSState = {
  launcherOpen: false,
  windows: [],
  activeWindowId: null,
  nextZIndex: 1,
  closedCids: [],
};

function _persistWindows(state: OSState) {
  if (typeof window === 'undefined') return;
  try {
    const ws = localStorage.getItem('neuro_selected_workspace') || 'global';
    const proj = localStorage.getItem('neuro_selected_project') || 'global';
    localStorage.setItem(`neuro_os_${ws}_${proj}`, JSON.stringify({
      windows: state.windows,
      activeWindowId: state.activeWindowId,
    }));
  } catch {}
}

const osSlice = createSlice({
  name: 'os',
  initialState,
  reducers: {
    toggleLauncher(state) { state.launcherOpen = !state.launcherOpen; },
    openLauncher(state) { state.launcherOpen = true; },
    closeLauncher(state) { state.launcherOpen = false; },

    /** Open a new window with an initial set of tabs. */
    openWindow(state, action: PayloadAction<WindowState>) {
      const w = action.payload;
      if (!state.closedCids) state.closedCids = [];
      for (const tab of w.tabs) {
        state.closedCids = state.closedCids.filter(c => c !== tab.cid);
      }
      const existing = state.windows.find(win => win.id === w.id);
      if (existing) {
        existing.minimized = false;
        existing.zIndex = state.nextZIndex++;
        state.activeWindowId = w.id;
        _persistWindows(state);
        return;
      }
      state.windows.push(w);
      state.nextZIndex = w.zIndex + 1;
      state.activeWindowId = w.id;
      _persistWindows(state);
    },

    /** Add a tab to an existing window. */
    addTabToWindow(state, action: PayloadAction<{
      windowId: string;
      tab: WindowTab;
      makeActive?: boolean;
    }>) {
      const { windowId, tab, makeActive = true } = action.payload;
      if (!state.closedCids) state.closedCids = [];
      state.closedCids = state.closedCids.filter(c => c !== tab.cid);
      const win = state.windows.find(w => w.id === windowId);
      if (!win) return;
      const exists = win.tabs.find(t => t.id === tab.id);
      if (!exists) win.tabs.push(tab);
      if (makeActive) {
        win.activeTabId = tab.id;
        win.zIndex = state.nextZIndex++;
        state.activeWindowId = windowId;
      }
      _persistWindows(state);
    },

    /** Close a single tab inside a window. Closes window if it was the last tab. */
    closeTabFromWindow(state, action: PayloadAction<{ windowId: string; tabId: string }>) {
      const { windowId, tabId } = action.payload;
      const win = state.windows.find(w => w.id === windowId);
      if (!win) return;
      const closedTab = win.tabs.find(t => t.id === tabId);
      if (closedTab) {
        if (!state.closedCids) state.closedCids = [];
        state.closedCids.push(closedTab.cid);
      }
      win.tabs = win.tabs.filter(t => t.id !== tabId);
      if (win.tabs.length === 0) {
        state.windows = state.windows.filter(w => w.id !== windowId);
        if (state.activeWindowId === windowId) {
          const top = state.windows.filter(w => !w.minimized).sort((a, b) => b.zIndex - a.zIndex)[0];
          state.activeWindowId = top?.id ?? null;
        }
      } else if (win.activeTabId === tabId) {
        win.activeTabId = win.tabs[win.tabs.length - 1].id;
      }
      _persistWindows(state);
    },

    /** Switch active tab within a window. */
    setActiveTabInWindow(state, action: PayloadAction<{ windowId: string; tabId: string }>) {
      const win = state.windows.find(w => w.id === action.payload.windowId);
      if (win) {
        win.activeTabId = action.payload.tabId;
        win.zIndex = state.nextZIndex++;
        state.activeWindowId = action.payload.windowId;
      }
      _persistWindows(state);
    },

    /** Reorder tabs within a window (drag-and-drop). */
    reorderWindowTabs(state, action: PayloadAction<{ windowId: string; fromIndex: number; toIndex: number }>) {
      const { windowId, fromIndex, toIndex } = action.payload;
      const win = state.windows.find(w => w.id === windowId);
      if (!win) return;
      const tabs = [...win.tabs];
      const [moved] = tabs.splice(fromIndex, 1);
      tabs.splice(toIndex, 0, moved);
      win.tabs = tabs;
      _persistWindows(state);
    },

    /** Move a tab out of its window into a new window. */
    moveTabToNewWindow(state, action: PayloadAction<{
      fromWindowId: string; tabId: string;
      x: number; y: number; width: number; height: number;
    }>) {
      const { fromWindowId, tabId, x, y, width, height } = action.payload;
      const fromWin = state.windows.find(w => w.id === fromWindowId);
      if (!fromWin) return;
      const tab = fromWin.tabs.find(t => t.id === tabId);
      if (!tab) return;
      fromWin.tabs = fromWin.tabs.filter(t => t.id !== tabId);
      if (fromWin.tabs.length === 0) {
        state.windows = state.windows.filter(w => w.id !== fromWindowId);
      } else if (fromWin.activeTabId === tabId) {
        fromWin.activeTabId = fromWin.tabs[fromWin.tabs.length - 1].id;
      }
      const newWinId = 'w-new-' + Date.now().toString(36);
      state.windows.push({
        id: newWinId,
        x, y, width, height,
        zIndex: state.nextZIndex++,
        minimized: false,
        maximized: false,
        tabs: [tab],
        activeTabId: tab.id,
      });
      state.activeWindowId = newWinId;
      _persistWindows(state);
    },

    closeWindow(state, action: PayloadAction<string>) {
      if (!state.closedCids) state.closedCids = [];
      const w = state.windows.find(win => win.id === action.payload);
      if (w) {
        for (const tab of w.tabs) state.closedCids.push(tab.cid);
      }
      state.windows = state.windows.filter(win => win.id !== action.payload);
      if (state.activeWindowId === action.payload) {
        const top = state.windows.filter(w => !w.minimized).sort((a, b) => b.zIndex - a.zIndex)[0];
        state.activeWindowId = top?.id ?? null;
      }
      _persistWindows(state);
    },

    removeWindow(state, action: PayloadAction<string>) {
      state.windows = state.windows.filter(win => win.id !== action.payload);
      if (state.activeWindowId === action.payload) {
        const top = state.windows.filter(w => !w.minimized).sort((a, b) => b.zIndex - a.zIndex)[0];
        state.activeWindowId = top?.id ?? null;
      }
      _persistWindows(state);
    },

    focusWindow(state, action: PayloadAction<string>) {
      const w = state.windows.find(win => win.id === action.payload);
      if (w) {
        if (w.minimized) w.minimized = false;
        w.zIndex = state.nextZIndex++;
        state.activeWindowId = w.id;
      }
      _persistWindows(state);
    },

    minimizeWindow(state, action: PayloadAction<string>) {
      const w = state.windows.find(win => win.id === action.payload);
      if (w) {
        w.minimized = true;
        if (state.activeWindowId === action.payload) {
          const top = state.windows.filter(win => !win.minimized).sort((a, b) => b.zIndex - a.zIndex)[0];
          state.activeWindowId = top?.id ?? null;
        }
      }
      _persistWindows(state);
    },

    maximizeWindow(state, action: PayloadAction<string>) {
      const w = state.windows.find(win => win.id === action.payload);
      if (!w) return;
      if (w.maximized) {
        if (w.prevBounds) {
          w.x = w.prevBounds.x; w.y = w.prevBounds.y;
          w.width = w.prevBounds.width; w.height = w.prevBounds.height;
        }
        w.maximized = false; w.prevBounds = null;
      } else {
        w.prevBounds = { x: w.x, y: w.y, width: w.width, height: w.height };
        w.maximized = true;
      }
      _persistWindows(state);
    },

    moveWindow(state, action: PayloadAction<{ id: string; x: number; y: number }>) {
      const w = state.windows.find(win => win.id === action.payload.id);
      if (w && !w.maximized) { w.x = action.payload.x; w.y = action.payload.y; }
    },

    resizeWindow(state, action: PayloadAction<{ id: string; width: number; height: number; x?: number; y?: number }>) {
      const w = state.windows.find(win => win.id === action.payload.id);
      if (w && !w.maximized) {
        w.width = Math.max(320, action.payload.width);
        w.height = Math.max(200, action.payload.height);
        if (action.payload.x !== undefined) w.x = action.payload.x;
        if (action.payload.y !== undefined) w.y = action.payload.y;
      }
    },

    setWindowTitle(state, action: PayloadAction<{ id: string; title: string }>) {
      const w = state.windows.find(win => win.id === action.payload.id);
      if (w) {
        const tab = w.tabs.find(t => t.id === w.activeTabId);
        if (tab) tab.title = action.payload.title;
      }
      _persistWindows(state);
    },

    renameTab(state, action: PayloadAction<{ windowId: string; tabId: string; title: string }>) {
      const win = state.windows.find(w => w.id === action.payload.windowId);
      if (!win) return;
      const tab = win.tabs.find(t => t.id === action.payload.tabId);
      if (tab) tab.title = action.payload.title;
      _persistWindows(state);
    },

    /** Restore windows from localStorage on app boot. */
    restoreWindows(state, action: PayloadAction<{ windows: WindowState[]; activeWindowId: string | null }>) {
      state.windows = action.payload.windows;
      state.activeWindowId = action.payload.activeWindowId;
      if (action.payload.windows.length > 0) {
        state.nextZIndex = Math.max(...action.payload.windows.map(w => w.zIndex)) + 1;
      }
    },
  },
});

export const {
  toggleLauncher, openLauncher, closeLauncher,
  openWindow, addTabToWindow, closeTabFromWindow, setActiveTabInWindow,
  reorderWindowTabs, moveTabToNewWindow,
  closeWindow, removeWindow, focusWindow, minimizeWindow, maximizeWindow,
  moveWindow, resizeWindow, setWindowTitle, renameTab, restoreWindows,
} = osSlice.actions;

export default osSlice.reducer;
