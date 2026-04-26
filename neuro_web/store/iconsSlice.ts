import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { APP_LIST } from '@/lib/appRegistry';

interface IconPos { x: number; y: number; }

export interface IconsState {
  desktopLayout: Record<string, IconPos>;
  mobileOrder: string[];
  mobileDock: string[];
}

const DEFAULT_DOCK = ['neuro', 'openclaw', 'terminal', 'opencode'];

function defaultDesktopLayout(): Record<string, IconPos> {
  const layout: Record<string, IconPos> = {};
  APP_LIST.forEach((app, i) => {
    const col = Math.floor(i / 8);
    const row = i % 8;
    layout[app.id] = { x: 20 + col * 88, y: 20 + row * 88 };
  });
  return layout;
}

function _persistIcons(state: IconsState) {
  if (typeof window === 'undefined') return;
  try {
    const ws = localStorage.getItem('neuro_selected_workspace') || 'global';
    const proj = localStorage.getItem('neuro_selected_project') || 'global';
    localStorage.setItem(`neuro_icons_${ws}_${proj}`, JSON.stringify({
      desktopLayout: state.desktopLayout,
      mobileOrder: state.mobileOrder,
      mobileDock: state.mobileDock,
    }));
  } catch {}
}

const iconsSlice = createSlice({
  name: 'icons',
  initialState: {
    desktopLayout: defaultDesktopLayout(),
    mobileOrder: APP_LIST.map(a => a.id),
    mobileDock: DEFAULT_DOCK,
  } as IconsState,
  reducers: {
    moveDesktopIcon(state, action: PayloadAction<{ appId: string; x: number; y: number }>) {
      state.desktopLayout[action.payload.appId] = { x: action.payload.x, y: action.payload.y };
      _persistIcons(state);
    },
    setMobileOrder(state, action: PayloadAction<string[]>) {
      state.mobileOrder = action.payload;
      _persistIcons(state);
    },
    setMobileDock(state, action: PayloadAction<string[]>) {
      state.mobileDock = action.payload;
      _persistIcons(state);
    },
    restoreIcons(state, action: PayloadAction<{ desktopLayout?: Record<string, IconPos>; mobileOrder?: string[]; mobileDock?: string[] }>) {
      if (action.payload.desktopLayout) {
        state.desktopLayout = { ...state.desktopLayout, ...action.payload.desktopLayout };
      }
      if (action.payload.mobileOrder) {
        const saved = action.payload.mobileOrder;
        const allIds = APP_LIST.map(a => a.id);
        const newApps = allIds.filter(id => !saved.includes(id));
        state.mobileOrder = [...saved.filter(id => (allIds as string[]).includes(id)), ...newApps];
      }
      if (action.payload.mobileDock) {
        state.mobileDock = action.payload.mobileDock;
      }
    },
  },
});

export const { moveDesktopIcon, setMobileOrder, setMobileDock, restoreIcons } = iconsSlice.actions;
export default iconsSlice.reducer;
