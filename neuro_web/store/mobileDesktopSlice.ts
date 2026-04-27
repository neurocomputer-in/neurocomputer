import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type DesktopTouchMode = 'touchpad' | 'tablet' | 'none';

export interface MobileDesktopState {
  connected: boolean;
  serverScreenW: number;
  serverScreenH: number;
  /**
   * touchpad — relative pointer (mouse-deltas, accelerated)
   * tablet   — absolute pointer (tap = jump cursor + click)
   * none     — touches pass through to nothing (read-only / display only)
   */
  mode: DesktopTouchMode;
  keyboardOpen: boolean;
  hotkeysExpanded: boolean;
  scrollMode: boolean;
  rotationLocked: boolean;
  displaySwitching: boolean;
  /**
   * Kiosk mode — desktop view covers the entire viewport (above MobileTabStrip
   * and any other app chrome). Set true after the user taps TapToConnect.
   * Clears on unmount.
   */
  kioskActive: boolean;
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean };
}

const initialState: MobileDesktopState = {
  connected: false,
  serverScreenW: 1920,
  serverScreenH: 1080,
  mode: 'touchpad',
  keyboardOpen: false,
  hotkeysExpanded: false,
  scrollMode: false,
  rotationLocked: false,
  displaySwitching: false,
  kioskActive: false,
  modifiers: { ctrl: false, alt: false, shift: false },
};

const NEXT_MODE: Record<DesktopTouchMode, DesktopTouchMode> = {
  touchpad: 'tablet',
  tablet: 'none',
  none: 'touchpad',
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
      state.mode = NEXT_MODE[state.mode];
    },
    setDesktopMode(state, action: PayloadAction<DesktopTouchMode>) {
      state.mode = action.payload;
    },
    setDesktopKeyboardOpen(state, action: PayloadAction<boolean>) {
      state.keyboardOpen = action.payload;
    },
    setHotkeysExpanded(state, action: PayloadAction<boolean>) {
      state.hotkeysExpanded = action.payload;
    },
    setScrollMode(state, action: PayloadAction<boolean>) {
      state.scrollMode = action.payload;
    },
    setRotationLocked(state, action: PayloadAction<boolean>) {
      state.rotationLocked = action.payload;
    },
    setDisplaySwitching(state, action: PayloadAction<boolean>) {
      state.displaySwitching = action.payload;
    },
    setKioskActive(state, action: PayloadAction<boolean>) {
      state.kioskActive = action.payload;
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
  setDesktopConnected, setServerScreenSize, cycleDesktopMode, setDesktopMode,
  setDesktopKeyboardOpen, setHotkeysExpanded, setScrollMode, setRotationLocked,
  setDisplaySwitching, setKioskActive, toggleDesktopModifier, clearDesktopModifiers,
} = mobileDesktopSlice.actions;

export default mobileDesktopSlice.reducer;
