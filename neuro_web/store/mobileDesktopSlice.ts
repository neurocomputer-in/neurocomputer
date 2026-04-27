import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface MobileDesktopState {
  connected: boolean;
  serverScreenW: number;
  serverScreenH: number;
  mode: 'touchpad' | 'tablet';
  keyboardOpen: boolean;
  scrollMode: boolean;
  rotationLocked: boolean;
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean };
}

const initialState: MobileDesktopState = {
  connected: false,
  serverScreenW: 1920,
  serverScreenH: 1080,
  mode: 'touchpad',
  keyboardOpen: false,
  scrollMode: false,
  rotationLocked: false,
  modifiers: { ctrl: false, alt: false, shift: false },
};

const mobileDesktopSlice = createSlice({
  name: 'mobileDesktop',
  initialState,
  reducers: {
    setDesktopConnected(state, action: PayloadAction<boolean>) {
      state.connected = action.payload;
    },
    setServerScreenSize(state, action: PayloadAction<{ w: number; h: number }>) {
      state.serverScreenW = action.payload.w;
      state.serverScreenH = action.payload.h;
    },
    cycleDesktopMode(state) {
      state.mode = state.mode === 'touchpad' ? 'tablet' : 'touchpad';
    },
    setDesktopKeyboardOpen(state, action: PayloadAction<boolean>) {
      state.keyboardOpen = action.payload;
    },
    setScrollMode(state, action: PayloadAction<boolean>) {
      state.scrollMode = action.payload;
    },
    setRotationLocked(state, action: PayloadAction<boolean>) {
      state.rotationLocked = action.payload;
    },
    toggleDesktopModifier(state, action: PayloadAction<'ctrl' | 'alt' | 'shift'>) {
      state.modifiers[action.payload] = !state.modifiers[action.payload];
    },
    clearDesktopModifiers(state) {
      state.modifiers = { ctrl: false, alt: false, shift: false };
    },
  },
});

export const {
  setDesktopConnected, setServerScreenSize, cycleDesktopMode,
  setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
  toggleDesktopModifier, clearDesktopModifiers,
} = mobileDesktopSlice.actions;

export default mobileDesktopSlice.reducer;
