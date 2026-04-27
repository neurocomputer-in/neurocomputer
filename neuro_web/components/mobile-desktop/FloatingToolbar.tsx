'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { useDrag } from '@use-gesture/react';
import {
  Monitor, Hand, Keyboard, Mic, Minimize2, RotateCw, Maximize, Minimize,
  MonitorUp, EyeOff, ChevronDown, ChevronUp, LogOut,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  cycleDesktopMode, setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
  setHotkeysExpanded, setDisplaySwitching, setKioskActive,
} from '@/store/mobileDesktopSlice';
import { apiSwitchDesktopDisplay } from '@/services/api';
import VoiceTypingPanel from './VoiceTypingPanel';
import ExpandedHotkeysRow from './ExpandedHotkeysRow';

export default function FloatingToolbar() {
  const dispatch = useAppDispatch();
  const { mode, keyboardOpen, scrollMode, rotationLocked, hotkeysExpanded, kioskActive } =
    useAppSelector(s => s.mobileDesktop);
  // Top-left so it's the first thing the user sees after entering kiosk —
  // dragging is supported but a discoverable starting position matters more
  // than balancing visually on first paint.
  const [pos, setPos] = useState({ x: 8, y: 60 });
  const [collapsed, setCollapsed] = useState(false);
  const [showVoice, setShowVoice] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const bind = useDrag(({ offset: [ox, oy] }) => {
    setPos({ x: ox, y: oy });
  }, {
    from: () => [pos.x, pos.y],
    filterTaps: true,
  });

  const btnStyle = (active?: boolean): React.CSSProperties => ({
    width: 36, height: 36, borderRadius: 8,
    background: active ? '#6366f1' : 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: active ? '#fff' : 'rgba(255,255,255,0.85)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', padding: 0,
  });

  const handleRotationLock = useCallback(async () => {
    const wantLocked = !rotationLocked;
    if (typeof window === 'undefined' || !('screen' in window) || !screen.orientation) return;
    try {
      if (wantLocked) {
        await (screen.orientation as any).lock('landscape');
      } else {
        screen.orientation.unlock();
      }
      dispatch(setRotationLocked(wantLocked));
    } catch {
      // Lock failed (browser unsupported, or page not in fullscreen). Leave
      // Redux untouched so the UI stays accurate to actual screen state.
    }
  }, [rotationLocked, dispatch]);

  const handleFullscreen = useCallback(async () => {
    // Toggle kiosk from Redux state, NOT document.fullscreenElement. In PWA
    // standalone mode the Fullscreen API can be a no-op (app is already
    // immersive in the OS sense), so `fullscreenElement` stays null even when
    // the visual outcome is fullscreen. Driving kiosk from Redux makes the
    // chrome-hide deterministic regardless of what the API reports.
    const goingFullscreen = !kioskActive;
    dispatch(setKioskActive(goingFullscreen));
    try {
      if (goingFullscreen && !document.fullscreenElement) {
        await document.documentElement.requestFullscreen({ navigationUI: 'hide' } as any);
      } else if (!goingFullscreen && document.fullscreenElement) {
        await document.exitFullscreen();
      }
    } catch {
      // Any Fullscreen-API rejection — kiosk state already toggled in Redux,
      // chrome hides via class + conditional render either way.
    }
  }, [dispatch, kioskActive]);

  const handleExitKiosk = useCallback(async () => {
    // Drop kiosk first so the OS chrome (MobileTabStrip + dock) reappears
    // immediately — even if exiting fullscreen has to await.
    dispatch(setKioskActive(false));
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
    } catch {}
    try {
      if ('screen' in window && screen.orientation) screen.orientation.unlock();
    } catch {}
    dispatch(setRotationLocked(false));
  }, [dispatch]);

  const handleSwitchDisplay = useCallback(async () => {
    dispatch(setDisplaySwitching(true));
    try {
      await apiSwitchDesktopDisplay();
    } catch (e) {
      console.error('[Toolbar] Switch display failed:', e);
    }
    // Match the Kotlin app's UX: hold the spinner briefly so the user can
    // register that something is happening, even if the request finishes
    // instantly. The video stream takes a frame or two to repaint anyway.
    setTimeout(() => dispatch(setDisplaySwitching(false)), 1200);
  }, [dispatch]);

  // Pick the right icon for the current touch mode. Three states match the
  // Kotlin app: touchpad (relative pointer), tablet (absolute pointer), none
  // (display-only, view without controlling).
  const modeIcon = mode === 'touchpad' ? <Hand size={16} />
    : mode === 'tablet' ? <Monitor size={16} />
    : <EyeOff size={16} />;
  const modeTitle = mode === 'touchpad' ? 'Touchpad mode'
    : mode === 'tablet' ? 'Tablet mode'
    : 'View only (no input)';

  return (
    <div
      ref={toolbarRef}
      {...bind()}
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        zIndex: 40,
        touchAction: 'none',
        userSelect: 'none',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 6,
      }}
    >
      <div style={{
        background: 'rgba(14,14,18,0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.1)',
        padding: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
      }}>
        {/* Drag handle */}
        <div style={{
          width: 28, height: 4, borderRadius: 2,
          background: 'rgba(255,255,255,0.2)',
          margin: '0 auto 2px',
          cursor: 'grab',
        }} />

        {!collapsed && (
          <>
            <button
              style={btnStyle()}
              title={modeTitle}
              onPointerDown={e => { e.stopPropagation(); dispatch(cycleDesktopMode()); }}
            >
              {modeIcon}
            </button>
            <button
              style={btnStyle(scrollMode)}
              title="Scroll mode"
              onPointerDown={e => { e.stopPropagation(); dispatch(setScrollMode(!scrollMode)); }}
            >
              <span style={{ fontSize: 11, fontWeight: 700 }}>SCR</span>
            </button>
            <button
              style={btnStyle(keyboardOpen)}
              title="Keyboard"
              onPointerDown={e => { e.stopPropagation(); dispatch(setDesktopKeyboardOpen(!keyboardOpen)); }}
            >
              <Keyboard size={16} />
            </button>
            <button
              style={btnStyle(showVoice)}
              title="Voice typing"
              onPointerDown={e => { e.stopPropagation(); setShowVoice(v => !v); }}
            >
              <Mic size={16} />
            </button>
            <button
              style={btnStyle()}
              title="Switch display"
              onPointerDown={e => { e.stopPropagation(); handleSwitchDisplay(); }}
            >
              <MonitorUp size={16} />
            </button>
            <button
              style={btnStyle(hotkeysExpanded)}
              title={hotkeysExpanded ? 'Hide hotkeys' : 'Show hotkeys'}
              onPointerDown={e => {
                e.stopPropagation();
                dispatch(setHotkeysExpanded(!hotkeysExpanded));
              }}
            >
              {hotkeysExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            <button
              style={btnStyle(rotationLocked)}
              title="Rotation lock"
              onPointerDown={e => { e.stopPropagation(); handleRotationLock(); }}
            >
              <RotateCw size={16} />
            </button>
            <button
              style={btnStyle(isFullscreen)}
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
              onPointerDown={e => { e.stopPropagation(); handleFullscreen(); }}
            >
              {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
            </button>
            {/* Kiosk exit — only visible while in kiosk so it doesn't add
                noise to the desktop-tab-as-window experience. Returns the
                user to the normal mobile shell with tab strip + dock. */}
            {kioskActive && (
              <button
                style={{ ...btnStyle(), background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.4)', color: '#fca5a5' }}
                title="Exit kiosk mode"
                onPointerDown={e => { e.stopPropagation(); handleExitKiosk(); }}
              >
                <LogOut size={16} />
              </button>
            )}
          </>
        )}

        <button
          style={{ ...btnStyle(), opacity: 0.55 }}
          title={collapsed ? 'Expand' : 'Collapse'}
          onPointerDown={e => { e.stopPropagation(); setCollapsed(v => !v); }}
        >
          <Minimize2 size={14} />
        </button>
      </div>

      {/* Side panels — laid out next to the toolbar (not overlapping). The
          parent flex row keeps them aligned to the toolbar's top edge. */}
      {!collapsed && (showVoice || hotkeysExpanded) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {showVoice && <VoiceTypingPanel onClose={() => setShowVoice(false)} />}
          {hotkeysExpanded && <ExpandedHotkeysRow />}
        </div>
      )}
    </div>
  );
}
