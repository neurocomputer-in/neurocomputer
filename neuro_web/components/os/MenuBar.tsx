'use client';
import { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, WifiOff, Loader2, Volume2, VolumeX, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSidebarOpen, setTtsAutoPlay } from '@/store/uiSlice';
import { toggleLauncher } from '@/store/osSlice';
import { APP_MAP } from '@/lib/appRegistry';
import ThemeSelector from '@/components/three/ThemeSelector';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function MenuBar() {
  const dispatch = useAppDispatch();
  const connectionStatus = useAppSelector(s => s.ui.connectionStatus);
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const windows = useAppSelector(s => s.os.windows);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const isMobile = useIsMobile();

  const activeWin = windows.find(w => w.id === activeWindowId);
  const activeWinActiveTab = activeWin?.tabs.find(t => t.id === activeWin.activeTabId);
  const activeApp = activeWinActiveTab ? APP_MAP[activeWinActiveTab.appId as keyof typeof APP_MAP] : null;

  const statusColor =
    connectionStatus === 'connected' ? '#27a644' :
    connectionStatus === 'connecting' ? '#f59e0b' : '#62666d';

  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    setIsDesktop(!!(window as any).neuroDesktop?.isDesktop);
  }, []);

  const [time, setTime] = useState('');
  useEffect(() => {
    const update = () => {
      const d = new Date();
      setTime(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    };
    update();
    const iv = setInterval(update, 30000);
    return () => clearInterval(iv);
  }, []);

  const barH = isMobile ? '28px' : '30px';

  return (
    <div
      className="glass-panel"
      style={{
        height: barH, minHeight: barH,
        display: 'flex', alignItems: 'center',
        padding: isMobile ? '0 8px' : '0 12px',
        gap: isMobile ? '4px' : '8px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        flexShrink: 0,
        zIndex: 200,
        overflow: 'visible',
        background: 'rgba(30,30,34,0.82)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        ...(isDesktop ? { WebkitAppRegion: 'drag', appRegion: 'drag' } as any : {}),
      }}
    >
      {/* Sidebar toggle */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => dispatch(setSidebarOpen(!sidebarOpen))}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: '20px', height: '20px', borderRadius: '4px',
          cursor: 'pointer', opacity: 0.7,
          flexShrink: 0,
          ...(isDesktop ? { WebkitAppRegion: 'no-drag', appRegion: 'no-drag' } as any : {}),
        }}
      >
        {sidebarOpen ? <PanelLeftClose size={13} color="#d0d6e0" /> : <PanelLeft size={13} color="#d0d6e0" />}
      </motion.div>

      {/* N Launcher button */}
      <motion.div
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        onClick={() => dispatch(toggleLauncher())}
        style={{
          width: '22px', height: '22px', borderRadius: '5px',
          background: '#5e6ad2',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '11px', fontWeight: 700, color: '#fff',
          cursor: 'pointer', flexShrink: 0,
          ...(isDesktop ? { WebkitAppRegion: 'no-drag', appRegion: 'no-drag' } as any : {}),
        }}
      >
        N
      </motion.div>

      {/* Active app name */}
      <span style={{
        fontSize: '12px', fontWeight: 600, color: '#e0e0e0',
        flexShrink: 0, marginLeft: '4px',
      }}>
        {activeApp ? activeApp.name : 'Neuro'}
      </span>

      <div style={{ flex: 1 }} />

      {/* Right side items */}
      {!isMobile && (
        <>
          <div style={{ flexShrink: 0 }}>
            <ThemeSelector />
          </div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => dispatch(setTtsAutoPlay(!ttsAutoPlay))}
            style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '2px 6px', borderRadius: '4px', cursor: 'pointer',
              ...(isDesktop ? { WebkitAppRegion: 'no-drag', appRegion: 'no-drag' } as any : {}),
            }}
          >
            {ttsAutoPlay ? <Volume2 size={12} color="#7170ff" /> : <VolumeX size={12} color="#62666d" />}
          </motion.div>
        </>
      )}

      {/* Connection */}
      <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
        {connectionStatus === 'connected' ? (
          <Wifi size={11} color={statusColor} />
        ) : connectionStatus === 'connecting' ? (
          <Loader2 size={11} color={statusColor} style={{ animation: 'spin 1s linear infinite' }} />
        ) : (
          <WifiOff size={11} color={statusColor} />
        )}
      </div>

      {/* Clock */}
      {!isMobile && (
        <span style={{ fontSize: '11px', color: '#888', flexShrink: 0, fontWeight: 500 }}>
          {time}
        </span>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
