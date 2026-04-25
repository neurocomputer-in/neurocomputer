'use client';
import { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Globe, Code, Briefcase, Terminal, Layers, LayoutGrid } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { focusWindow, minimizeWindow, maximizeWindow, toggleLauncher } from '@/store/osSlice';
import { APP_LIST, APP_MAP, AppDef, AppId } from '@/lib/appRegistry';
import { useIsMobile } from '@/hooks/useIsMobile';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
};

function DockIcon({ app, running, hasWindows, onClick, onRightClick }: {
  app: AppDef;
  running: boolean;
  hasWindows: boolean;
  onClick: () => void;
  onRightClick: (e: React.MouseEvent) => void;
}) {
  const LucideIcon = ICON_MAP[app.icon] || Globe;
  const [hover, setHover] = useState(false);
  const isMobile = useIsMobile();

  const size = isMobile ? 40 : hover ? 52 : 46;

  return (
    <motion.div
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.9, y: 0 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onClick}
      onContextMenu={onRightClick}
      title={app.name}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px',
        cursor: 'pointer', padding: '2px 4px',
        WebkitTapHighlightColor: 'transparent',
        position: 'relative',
      }}
    >
      {hover && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          background: 'rgba(20,20,22,0.95)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '6px',
          padding: '4px 10px',
          fontSize: '11px',
          fontWeight: 500,
          color: '#e0e0e0',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          zIndex: 9999,
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        }}>
          {app.name}
        </div>
      )}
      <motion.div
        animate={{ width: size, height: size }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        style={{
          borderRadius: '10px',
          background: app.color,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: running
            ? `0 2px 12px ${app.color}66`
            : '0 1px 4px rgba(0,0,0,0.2)',
          opacity: running ? 1 : 0.7,
        }}
      >
        <LucideIcon size={size * 0.45} color="#fff" strokeWidth={1.6} />
      </motion.div>
      {/* Running dot */}
      <div style={{
        width: '4px', height: '4px', borderRadius: '50%',
        background: running ? '#fff' : 'transparent',
        transition: 'background 0.2s',
      }} />
    </motion.div>
  );
}

function LauncherButton({ isMobile, onClick }: { isMobile: boolean; onClick: () => void }) {
  const [hover, setHover] = useState(false);
  const size = isMobile ? 40 : hover ? 52 : 46;

  return (
    <motion.div
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.9, y: 0 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onClick}
      title="Launcher"
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px',
        cursor: 'pointer', padding: '2px 4px',
        WebkitTapHighlightColor: 'transparent',
        position: 'relative',
      }}
    >
      {hover && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%',
          transform: 'translateX(-50%)', marginBottom: '8px',
          background: 'rgba(20,20,22,0.95)', border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '6px', padding: '4px 10px',
          fontSize: '11px', fontWeight: 500, color: '#e0e0e0',
          whiteSpace: 'nowrap', pointerEvents: 'none',
          zIndex: 9999, boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        }}>
          Launcher
        </div>
      )}
      <motion.div
        animate={{ width: size, height: size }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        style={{
          borderRadius: '10px',
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
        }}
      >
        <LayoutGrid size={size * 0.42} color="rgba(255,255,255,0.8)" strokeWidth={1.6} />
      </motion.div>
      <div style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'transparent' }} />
    </motion.div>
  );
}

interface Props {
  onLaunch: (app: AppDef) => void;
}

export default function Dock({ onLaunch }: Props) {
  const dispatch = useAppDispatch();
  const windows = useAppSelector(s => s.os.windows);
  const isMobile = useIsMobile();
  const [contextApp, setContextApp] = useState<{ app: AppDef; x: number; y: number } | null>(null);

  const runningAppIds = new Set(windows.flatMap(w => w.tabs.map(t => t.appId)));
  const pinnedApps = APP_LIST.filter(a => a.pinned);

  const handleAppClick = useCallback((app: AppDef) => {
    setContextApp(null);
    const appWindows = windows.filter(w => w.tabs.some(t => t.appId === app.id) && !w.minimized);
    const minimizedWindows = windows.filter(w => w.tabs.some(t => t.appId === app.id) && w.minimized);

    if (appWindows.length > 0) {
      dispatch(focusWindow(appWindows.sort((a, b) => b.zIndex - a.zIndex)[0].id));
    } else if (minimizedWindows.length > 0) {
      dispatch(focusWindow(minimizedWindows[0].id));
    } else {
      onLaunch(app);
    }
  }, [windows, dispatch, onLaunch]);

  const handleContextMenu = useCallback((e: React.MouseEvent, app: AppDef) => {
    e.preventDefault();
    setContextApp({ app, x: e.clientX, y: e.clientY });
  }, []);

  const appWindows = (appId: AppId) => windows.filter(w => w.tabs.some(t => t.appId === appId));

  return (
    <>
      <div
        className="glass-panel"
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          gap: isMobile ? '4px' : '8px',
          padding: isMobile ? '6px 12px 8px' : '8px 16px 10px',
          borderRadius: '16px 16px 0 0',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          flexShrink: 0,
          position: 'relative',
          zIndex: 100,
        }}
      >
        {pinnedApps.map(app => (
          <DockIcon
            key={app.id}
            app={app}
            running={runningAppIds.has(app.id)}
            hasWindows={appWindows(app.id).length > 0}
            onClick={() => handleAppClick(app)}
            onRightClick={(e) => handleContextMenu(e, app)}
          />
        ))}

        {/* Divider */}
        <div style={{
          width: '1px', height: '32px', alignSelf: 'center',
          background: 'rgba(255,255,255,0.12)', margin: isMobile ? '0 2px' : '0 4px',
        }} />

        {/* Launcher button */}
        <LauncherButton isMobile={isMobile} onClick={() => dispatch(toggleLauncher())} />
      </div>

      {/* Context menu for app sessions */}
      {typeof window !== 'undefined' && contextApp && createPortal(
        <AnimatePresence>
          <>
            <motion.div
              key="ctx-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setContextApp(null)}
              style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
            />
            <motion.div
              key="ctx-menu"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.12 }}
              style={{
                position: 'fixed',
                left: contextApp.x, top: contextApp.y - 8,
                transform: 'translateY(-100%)',
                zIndex: 9999,
                background: '#1a1b1d',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '10px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                minWidth: '180px',
                padding: '4px',
                overflow: 'visible',
              }}
            >
              {/* Sessions */}
              {appWindows(contextApp.app.id).map(w => (
                <button
                  key={w.id}
                  onClick={() => {
                    if (w.minimized) dispatch(focusWindow(w.id));
                    else dispatch(focusWindow(w.id));
                    setContextApp(null);
                  }}
                  style={{
                    width: '100%', padding: '8px 12px',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    background: 'transparent', border: 'none',
                    borderRadius: '6px',
                    color: '#d0d6e0', fontSize: '13px', fontFamily: 'inherit',
                    cursor: 'pointer', textAlign: 'left',
                  }}
                >
                  {w.minimized ? '◉' : '●'} {w.tabs.find(t => t.id === w.activeTabId)?.title ?? 'Window'}
                </button>
              ))}
              {appWindows(contextApp.app.id).length > 0 && (
                <div style={{ height: '1px', background: 'rgba(255,255,255,0.08)', margin: '4px 0' }} />
              )}
              <button
                onClick={() => { onLaunch(contextApp.app); setContextApp(null); }}
                style={{
                  width: '100%', padding: '8px 12px',
                  display: 'flex', alignItems: 'center', gap: '8px',
                  background: 'transparent', border: 'none',
                  borderRadius: '6px',
                  color: '#8B5CF6', fontSize: '13px', fontWeight: 500,
                  fontFamily: 'inherit', cursor: 'pointer', textAlign: 'left',
                }}
              >
                + New {contextApp.app.name} Session
              </button>
            </motion.div>
          </>
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}
