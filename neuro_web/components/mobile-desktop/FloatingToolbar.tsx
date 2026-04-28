'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { useDrag } from '@use-gesture/react';
import {
  Monitor, Hand, Keyboard, Mic, RotateCw, Maximize, Minimize as MinimizeIcon,
  MonitorUp, EyeOff, ChevronDown, ChevronUp, LogOut,
  Eye, CornerDownLeft, Delete, Space, MousePointer2, Move, Focus,
  Undo2, Redo2, Camera, ChevronsLeft, ChevronsRight,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  cycleDesktopMode, setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
  setHotkeysExpanded, setDisplaySwitching, setKioskActive,
} from '@/store/mobileDesktopSlice';
import { closeTab } from '@/store/conversationSlice';
import { closeTabFromWindow, removeWindow } from '@/store/osSlice';
import { apiSwitchDesktopDisplay } from '@/services/api';
import { useDesktopRoom } from './DesktopRoomContext';
import VoiceTypingPanel from './VoiceTypingPanel';

// Loose `icon` typing because lucide-react icons + our inline span shims
// don't share a single React.ComponentType signature.
type IconLike = (props: { size?: number }) => JSX.Element;
interface ButtonDef {
  icon: IconLike | React.ComponentType<any>;
  title: string;
  active?: boolean;
  activeColor?: string;
  onClick: () => void;
}

/**
 * Right-side docked floating toolbar for the remote-PC kiosk view. Mirrors
 * the Kotlin DraggableToolbar layout (vertical column, drag handle, two-tier
 * primary + expanded shortcuts) and adds Minimize / Exit Remote buttons the
 * web port specifically needs to leave kiosk mode cleanly.
 */
export default function FloatingToolbar() {
  const dispatch = useAppDispatch();
  const { sendControl } = useDesktopRoom();
  const { mode, keyboardOpen, scrollMode, rotationLocked, hotkeysExpanded, kioskActive } =
    useAppSelector(s => s.mobileDesktop);

  // Selectors for closing the desktop tab (Exit Remote).
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const windows = useAppSelector(s => s.os.windows);
  const desktopTab = (() => {
    const w = windows.find(w => w.id === activeWindowId);
    return w?.tabs.find(t => t.id === w.activeTabId && t.type === 'desktop');
  })();

  // Initial position: docked left edge, vertically centered-ish (top:64).
  const [pos, setPos] = useState(() => ({
    x: 8,
    y: 64,
  }));
  const [collapsed, setCollapsed] = useState(false);
  const [showVoice, setShowVoice] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showLabels, setShowLabels] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleFullscreen = () => setIsFullscreen(!!document.fullscreenElement);
    const handleResize = () => {
      setPos(p => ({
        x: Math.min(Math.max(0, p.x), window.innerWidth - 56),
        y: Math.min(Math.max(0, p.y), window.innerHeight - 56),
      }));
    };
    
    document.addEventListener('fullscreenchange', handleFullscreen);
    window.addEventListener('resize', handleResize);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreen);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const bind = useDrag(({ offset: [ox, oy] }) => {
    setPos({ x: ox, y: oy });
  }, {
    from: () => [pos.x, pos.y],
    filterTaps: true,
  });

  const handleRotationLock = useCallback(async () => {
    const wantLocked = !rotationLocked;
    if (typeof window === 'undefined' || !('screen' in window) || !screen.orientation) return;
    try {
      if (wantLocked) await (screen.orientation as any).lock('landscape');
      else screen.orientation.unlock();
      dispatch(setRotationLocked(wantLocked));
    } catch {}
  }, [rotationLocked, dispatch]);

  const handleFullscreen = useCallback(async () => {
    const goingFullscreen = !kioskActive;
    dispatch(setKioskActive(goingFullscreen));
    try {
      if (goingFullscreen && !document.fullscreenElement) {
        await document.documentElement.requestFullscreen({ navigationUI: 'hide' } as any);
      } else if (!goingFullscreen && document.fullscreenElement) {
        await document.exitFullscreen();
      }
    } catch {}
  }, [dispatch, kioskActive]);

  const handleSwitchDisplay = useCallback(async () => {
    dispatch(setDisplaySwitching(true));
    try { await apiSwitchDesktopDisplay(); } catch (e) { console.error(e); }
    setTimeout(() => dispatch(setDisplaySwitching(false)), 1200);
  }, [dispatch]);

  // Minimize → drop kiosk so the OS chrome reappears + TapToConnect shows.
  // Connection stays alive; user can re-enter via the Tap-to-Start button.
  const handleMinimize = useCallback(async () => {
    dispatch(setKioskActive(false));
    try { if (document.fullscreenElement) await document.exitFullscreen(); } catch {}
    try { if ('screen' in window && screen.orientation) screen.orientation.unlock(); } catch {}
    dispatch(setRotationLocked(false));
  }, [dispatch]);

  // Exit Remote → close the desktop tab entirely. DesktopApp's unmount
  // cleanup will disconnect LiveKit and call apiStopDesktopStream.
  const handleExitRemote = useCallback(async () => {
    dispatch(setKioskActive(false));
    try { if (document.fullscreenElement) await document.exitFullscreen(); } catch {}
    try { if ('screen' in window && screen.orientation) screen.orientation.unlock(); } catch {}
    dispatch(setRotationLocked(false));
    if (desktopTab && activeWindowId) {
      dispatch(closeTab(desktopTab.cid));
      dispatch(closeTabFromWindow({ windowId: activeWindowId, tabId: desktopTab.id }));
      // If that was the last tab in the window, remove the window too.
      const w = windows.find(w => w.id === activeWindowId);
      if (w && w.tabs.length <= 1) dispatch(removeWindow(activeWindowId));
    }
  }, [dispatch, desktopTab, activeWindowId, windows]);

  const sendKey = (key: string) => sendControl({ type: 'key', key });

  // Mode icon (3-state: touchpad/tablet/none) — colored to match Kotlin.
  const modeIcon = mode === 'touchpad' ? <Hand size={18} />
    : mode === 'tablet' ? <Monitor size={18} />
    : <EyeOff size={18} />;
  const modeTitle = mode === 'touchpad' ? 'Touchpad'
    : mode === 'tablet' ? 'Tablet'
    : 'View only';

  // Primary buttons — same order/colors as Kotlin DraggableToolbar.
  const primary: ButtonDef[] = [
    { icon: () => <>{modeIcon}</>, title: modeTitle, onClick: () => dispatch(cycleDesktopMode()) },
    { icon: CornerDownLeft, title: 'Enter', activeColor: '#86efac', onClick: () => sendKey('Return') },
    { icon: Delete, title: 'Backspace', activeColor: '#fca5a5', onClick: () => sendKey('BackSpace') },
    { icon: Space, title: 'Space', onClick: () => sendKey('space') },
    { icon: Keyboard, title: 'Keyboard', active: keyboardOpen, activeColor: '#c4b5fd', onClick: () => dispatch(setDesktopKeyboardOpen(!keyboardOpen)) },
    { icon: Move, title: 'Scroll', active: scrollMode, activeColor: '#67e8f9', onClick: () => dispatch(setScrollMode(!scrollMode)) },
    { icon: Mic, title: 'Voice typing', active: showVoice, activeColor: '#fca5a5', onClick: () => setShowVoice(v => !v) },
    { icon: MonitorUp, title: 'Switch display', onClick: handleSwitchDisplay },
    { icon: RotateCw, title: 'Rotation lock', active: rotationLocked, activeColor: '#fca5a5', onClick: handleRotationLock },
    { icon: isFullscreen ? MinimizeIcon : Maximize, title: isFullscreen ? 'Exit fullscreen' : 'Fullscreen', onClick: handleFullscreen },
  ];

  // Expanded tier (toggled by the chevron).
  const expanded: ButtonDef[] = [
    { icon: () => <span style={{ fontSize: 10, fontWeight: 700 }}>ESC</span>, title: 'Escape', onClick: () => sendKey('Escape') },
    { icon: () => <span style={{ fontSize: 10, fontWeight: 700 }}>Tab</span>, title: 'Tab', onClick: () => sendKey('Tab') },
    { icon: Undo2, title: 'Undo', onClick: () => sendKey('ctrl+z') },
    { icon: Redo2, title: 'Redo', onClick: () => sendKey('ctrl+shift+z') },
    { icon: ChevronsLeft, title: 'Page Up', onClick: () => sendKey('Page_Up') },
    { icon: ChevronsRight, title: 'Page Down', onClick: () => sendKey('Page_Down') },
    { icon: Camera, title: 'Screenshot', onClick: () => sendKey('Print') },
  ];

  const btnStyle = (active?: boolean, activeColor?: string): React.CSSProperties => ({
    width: 40, height: 40, borderRadius: 10,
    background: active ? `${activeColor || '#6366f1'}26` : 'rgba(255,255,255,0.06)',
    border: `1px solid ${active ? `${activeColor || '#6366f1'}66` : 'rgba(255,255,255,0.06)'}`,
    color: active ? (activeColor || '#a5b4fc') : 'rgba(255,255,255,0.85)',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', padding: 0, gap: 1,
    transition: 'background 0.15s, border-color 0.15s',
  });

  const renderBtn = (b: ButtonDef, key: string) => {
    const Icon = b.icon;
    return (
      <button
        key={key}
        style={btnStyle(b.active, b.activeColor)}
        title={b.title}
        onPointerDown={e => { e.stopPropagation(); b.onClick(); }}
      >
        <Icon size={16} />
        {showLabels && (
          <span style={{ fontSize: 7, lineHeight: 1, opacity: 0.7 }}>
            {b.title.length > 7 ? b.title.slice(0, 7) : b.title}
          </span>
        )}
      </button>
    );
  };

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
        gap: 8,
        // Panels expand to the right of the main toolbar column.
        flexDirection: 'row',
      }}
    >
      <div style={{
        background: 'rgba(14,14,18,0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.1)',
        padding: 5,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        boxShadow: '0 6px 24px rgba(0,0,0,0.55)',
        maxHeight: 'calc(100vh - 16px)',
        overflowY: 'auto',
        overflowX: 'hidden',
        scrollbarWidth: 'none',
      }}
      className="floating-toolbar-inner"
    >
        {/* Drag handle */}
        <div style={{
          width: 32, height: 4, borderRadius: 2,
          background: 'rgba(255,255,255,0.25)',
          margin: '2px auto 4px',
          cursor: 'grab',
        }} />

        {/* Show-labels toggle (Kotlin's Eye/EyeOff button) */}
        <button
          style={btnStyle(showLabels, '#c4b5fd')}
          title="Toggle labels"
          onPointerDown={e => { e.stopPropagation(); setShowLabels(v => !v); }}
        >
          {showLabels ? <Eye size={16} /> : <EyeOff size={16} />}
        </button>

        {!collapsed && (
          <>
            <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '2px 4px' }} />
            {primary.map((b, i) => renderBtn(b, `p${i}`))}
            <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '2px 4px' }} />

            {/* Expand/collapse for second tier */}
            <button
              style={btnStyle(hotkeysExpanded, '#c4b5fd')}
              title={hotkeysExpanded ? 'Hide shortcuts' : 'Show shortcuts'}
              onPointerDown={e => { e.stopPropagation(); dispatch(setHotkeysExpanded(!hotkeysExpanded)); }}
            >
              {hotkeysExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {/* Minimize — exit kiosk only, keep connection */}
            <button
              style={{ ...btnStyle(), background: 'rgba(250,204,21,0.12)', border: '1px solid rgba(250,204,21,0.4)', color: '#fde047' }}
              title="Minimize"
              onPointerDown={e => { e.stopPropagation(); handleMinimize(); }}
            >
              <ChevronDown size={16} />
            </button>

            {/* Exit Remote — close tab + disconnect */}
            <button
              style={{ ...btnStyle(), background: 'rgba(239,68,68,0.18)', border: '1px solid rgba(239,68,68,0.5)', color: '#fca5a5' }}
              title="Exit remote"
              onPointerDown={e => { e.stopPropagation(); handleExitRemote(); }}
            >
              <LogOut size={16} />
            </button>
          </>
        )}

        <button
          style={{ ...btnStyle(), opacity: 0.55 }}
          title={collapsed ? 'Expand toolbar' : 'Collapse toolbar'}
          onPointerDown={e => { e.stopPropagation(); setCollapsed(v => !v); }}
        >
          {collapsed ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Side panels — to the RIGHT of the toolbar */}
      {!collapsed && (showVoice || hotkeysExpanded) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginLeft: 4 }}>
          {showVoice && <VoiceTypingPanel onClose={() => setShowVoice(false)} />}
          {hotkeysExpanded && (
            <div
              onPointerDown={e => e.stopPropagation()}
              style={{
                display: 'flex', flexWrap: 'wrap', gap: 4,
                background: 'rgba(14,14,18,0.92)',
                backdropFilter: 'blur(16px)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12,
                padding: 6,
                width: 200,
              }}
            >
              {expanded.map((b, i) => renderBtn(b, `e${i}`))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
