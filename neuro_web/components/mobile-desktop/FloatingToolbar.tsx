'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { useDrag } from '@use-gesture/react';
import { Monitor, Hand, Keyboard, Volume2, Minimize2, RotateCw, Maximize, Minimize } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  cycleDesktopMode, setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
} from '@/store/mobileDesktopSlice';
import VoiceRecordingPanel from './VoiceRecordingPanel';

export default function FloatingToolbar() {
  const dispatch = useAppDispatch();
  const { mode, keyboardOpen, scrollMode, rotationLocked } = useAppSelector(s => s.mobileDesktop);
  const [pos, setPos] = useState({ x: 16, y: 200 });
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
    const locked = !rotationLocked;
    dispatch(setRotationLocked(locked));
    if (typeof window !== 'undefined' && 'screen' in window && screen.orientation) {
      try {
        if (locked) {
          await (screen.orientation as any).lock('landscape');
        } else {
          screen.orientation.unlock();
        }
      } catch {}
    }
  }, [rotationLocked, dispatch]);

  const handleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {}
  }, []);

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
              title={mode === 'touchpad' ? 'Touchpad mode' : 'Tablet mode'}
              onPointerDown={e => { e.stopPropagation(); dispatch(cycleDesktopMode()); }}
            >
              {mode === 'touchpad' ? <Hand size={16} /> : <Monitor size={16} />}
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
              <Volume2 size={16} />
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

      {showVoice && !collapsed && (
        <div style={{ marginTop: 6 }}>
          <VoiceRecordingPanel />
        </div>
      )}
    </div>
  );
}
