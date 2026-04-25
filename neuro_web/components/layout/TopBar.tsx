'use client';
import { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { PanelLeftClose, PanelLeft, Wifi, WifiOff, Loader2, Volume2, VolumeX, Minus, Square, X, Layout, Box, Columns, MoreVertical } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSidebarOpen, setTtsAutoPlay, setInterfaceMode, splitPane } from '@/store/uiSlice';
import ThemeSelector from '@/components/three/ThemeSelector';
import AgentDropdown from '@/components/agent/AgentDropdown';
import TerminalButton from '@/components/terminal/TerminalButton';
import NeuroIDEButton from '@/components/neuroide/NeuroIDEButton';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function TopBar() {
  const dispatch = useAppDispatch();
  const connectionStatus = useAppSelector(s => s.ui.connectionStatus);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const interfaceMode = useAppSelector(s => s.ui.interfaceMode);
  const paneCount = useAppSelector(s => s.ui.panes.length);
  const isMobile = useIsMobile();
  const statusColor =
    connectionStatus === 'connected' ? '#27a644' :
    connectionStatus === 'connecting' ? '#f59e0b' : '#62666d';

  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    setIsDesktop(!!(window as any).neuroDesktop?.isDesktop);
  }, []);

  const winMinimize = useCallback(() => (window as any).neuroDesktop?.minimize(), []);
  const winMaximize = useCallback(() => (window as any).neuroDesktop?.maximize(), []);
  const winClose = useCallback(() => (window as any).neuroDesktop?.close(), []);

  const dragStyle = isDesktop ? { WebkitAppRegion: 'drag', appRegion: 'drag' } as any : {};
  const noDragStyle = isDesktop ? { WebkitAppRegion: 'no-drag', appRegion: 'no-drag' } as any : {};

  const [moreOpen, setMoreOpen] = useState(false);

  const Separator = () => <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.05)' }} />;

  return (
    <div
      className="glass-panel"
      style={{
        height: isMobile ? '44px' : '48px',
        minHeight: isMobile ? '44px' : '48px',
        display: 'flex',
        alignItems: 'center',
        padding: isMobile ? '0 8px' : '0 16px',
        gap: isMobile ? '4px' : '8px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
        zIndex: 50,
        overflow: 'hidden',
        ...dragStyle,
      }}
    >
      {/* Sidebar toggle */}
      <motion.div
        whileHover={{ scale: 1.05, backgroundColor: 'rgba(255,255,255,0.04)' }}
        whileTap={{ scale: 0.95 }}
        onClick={() => dispatch(setSidebarOpen(!sidebarOpen))}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: '28px', height: '28px', borderRadius: '6px',
          cursor: 'pointer', opacity: 0.8, flexShrink: 0,
          ...noDragStyle,
        }}
      >
        {sidebarOpen ? <PanelLeftClose size={15} color="#d0d6e0" /> : <PanelLeft size={15} color="#d0d6e0" />}
      </motion.div>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '6px' : '8px', userSelect: 'none', flexShrink: 0 }}>
        <div style={{
          width: '26px', height: '26px', borderRadius: '6px',
          background: '#5e6ad2',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 590, color: '#fff',
        }}>
          N
        </div>
        {!isMobile && (
          <span style={{ fontSize: '14px', fontWeight: 510, color: '#f7f8f8', letterSpacing: '-0.3px' }}>
            Neuro
          </span>
        )}
       </div>

      <Separator />

      <div style={noDragStyle}><AgentDropdown /></div>

      <Separator />

      <div style={noDragStyle}><TerminalButton /></div>
      <div style={noDragStyle}><NeuroIDEButton /></div>

      <div style={{ flex: 1 }} />

      {/* Interface mode toggle — hidden on mobile */}
      {!isMobile && (
        <div
          style={{
            display: 'inline-flex', padding: 2, gap: 2,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, flexShrink: 0,
            ...noDragStyle,
          }}
          title="Toggle Classic tabs / 3D spatial view"
        >
          {([
            { id: 'classic', label: 'Classic', Icon: Layout },
            { id: 'spatial', label: '3D',      Icon: Box },
          ] as const).map(opt => {
            const active = interfaceMode === opt.id;
            const Icon = opt.Icon;
            return (
              <button
                key={opt.id}
                onClick={() => dispatch(setInterfaceMode(opt.id))}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  padding: '4px 9px', borderRadius: 6,
                  background: active ? 'rgba(94,106,210,0.15)' : 'transparent',
                  border: 'none',
                  color: active ? '#f7f8f8' : '#8a8f98',
                  fontSize: 12, fontWeight: active ? 510 : 400,
                  cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'background 0.12s, color 0.12s',
                }}
              >
                <Icon size={12} />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Split panes — hidden on mobile */}
      {!isMobile && (
        <button
          onClick={() => paneCount < 3 && dispatch(splitPane())}
          disabled={paneCount >= 3}
          title={paneCount >= 3 ? 'Max 3 panes' : `Split pane (${paneCount}/3)`}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '5px 10px', borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.02)',
            color: paneCount >= 3 ? '#50565d' : '#d0d6e0',
            fontSize: 12, cursor: paneCount >= 3 ? 'default' : 'pointer',
            fontFamily: 'inherit', flexShrink: 0,
            ...noDragStyle,
          }}
        >
          <Columns size={12} />
          <span>Split</span>
        </button>
      )}

      {/* Theme selector — hidden on mobile (in overflow) */}
      {!isMobile && <div style={noDragStyle}><ThemeSelector /></div>}

      {/* TTS toggle — compact on mobile */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => dispatch(setTtsAutoPlay(!ttsAutoPlay))}
        style={{
          display: 'flex', alignItems: 'center', gap: isMobile ? '4px' : '6px',
          background: ttsAutoPlay ? 'rgba(94,106,210,0.1)' : 'rgba(255,255,255,0.02)',
          padding: isMobile ? '4px 6px' : '5px 10px', borderRadius: '6px', cursor: 'pointer',
          userSelect: 'none', transition: 'background 0.15s, border-color 0.15s',
          ...noDragStyle, flexShrink: 0,
          border: `1px solid ${ttsAutoPlay ? 'rgba(94,106,210,0.2)' : 'rgba(255,255,255,0.05)'}`,
        }}
        title={ttsAutoPlay ? 'Voice replies ON' : 'Voice replies OFF'}
      >
        {ttsAutoPlay ? <Volume2 size={13} color="#7170ff" /> : <VolumeX size={13} color="#62666d" />}
        {!isMobile && (
          <span style={{ fontSize: '11px', color: ttsAutoPlay ? '#828fff' : '#62666d', fontWeight: 510 }}>
            {ttsAutoPlay ? 'Voice' : 'Mute'}
          </span>
        )}
      </motion.div>

      {/* Connection status */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '5px',
        padding: '4px 8px', borderRadius: '6px',
        background: 'rgba(255,255,255,0.02)', flexShrink: 0,
      }}>
        {connectionStatus === 'connected' ? (
          <Wifi size={12} color={statusColor} />
        ) : connectionStatus === 'connecting' ? (
          <Loader2 size={12} color={statusColor} style={{ animation: 'spin 1s linear infinite' }} />
        ) : (
          <WifiOff size={12} color={statusColor} />
        )}
      </div>

      {/* Mobile overflow menu */}
      {isMobile && (
        <div style={{ flexShrink: 0 }}>
          <button
            onClick={(e) => { e.stopPropagation(); setMoreOpen(o => !o); }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '44px', height: '44px', borderRadius: '8px',
              cursor: 'pointer', background: 'rgba(255,255,255,0.05)', border: 'none',
              touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent',
              padding: 0,
            }}
            type="button"
          >
            {moreOpen ? <X size={18} color="#d0d6e0" /> : <MoreVertical size={18} color="#d0d6e0" />}
          </button>
          {typeof window !== 'undefined' && createPortal(
            <AnimatePresence>
              {moreOpen && (
                <>
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setMoreOpen(false)}
                    style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
                  />
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.15 }}
                    style={{
                      position: 'fixed', top: '48px', right: '8px',
                      zIndex: 9999, borderRadius: '12px',
                      minWidth: '220px', maxWidth: 'calc(100vw - 16px)',
                      background: '#1a1b1d',
                      border: '1px solid rgba(255,255,255,0.12)',
                      boxShadow: '0 16px 48px rgba(0,0,0,0.8)',
        overflow: 'visible',
                    }}
                  >
                    {[
                      { label: 'Classic View', Icon: Layout, action: () => { dispatch(setInterfaceMode('classic')); setMoreOpen(false); } },
                      { label: '3D View',      Icon: Box,    action: () => { dispatch(setInterfaceMode('spatial')); setMoreOpen(false); } },
                      { label: `Split Pane (${paneCount}/3)`, Icon: Columns, action: () => { paneCount < 3 && dispatch(splitPane()); setMoreOpen(false); }, disabled: paneCount >= 3 },
                    ].map(item => (
                      <button
                        key={item.label}
                        onClick={item.action}
                        disabled={item.disabled}
                        style={{
                          width: '100%', padding: '14px 16px',
                          display: 'flex', alignItems: 'center', gap: '12px',
                          background: 'transparent', border: 'none',
                          borderBottom: '1px solid rgba(255,255,255,0.06)',
                          color: item.disabled ? '#50565d' : '#d0d6e0',
                          fontSize: '15px', fontFamily: 'inherit',
                          cursor: item.disabled ? 'default' : 'pointer',
                          textAlign: 'left', touchAction: 'manipulation',
                          WebkitTapHighlightColor: 'transparent',
                        }}
                      >
                        <item.Icon size={16} />
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </motion.div>
                </>
              )}
            </AnimatePresence>,
            document.body
          )}
        </div>
      )}

      {/* Desktop window controls */}
      {isDesktop && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0px', marginLeft: '8px',
          ...noDragStyle,
        }}>
          <motion.button
            whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            whileTap={{ scale: 0.9 }}
            onClick={winMinimize}
            style={{
              width: '46px', height: '48px', border: 'none', background: 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Minimize"
          >
            <Minus size={15} color="#8a8f98" />
          </motion.button>
          <motion.button
            whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            whileTap={{ scale: 0.9 }}
            onClick={winMaximize}
            style={{
              width: '46px', height: '48px', border: 'none', background: 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Maximize"
          >
            <Square size={11} color="#8a8f98" />
          </motion.button>
          <motion.button
            whileHover={{ backgroundColor: 'rgba(239,68,68,0.2)' }}
            whileTap={{ scale: 0.9 }}
            onClick={winClose}
            style={{
              width: '46px', height: '48px', border: 'none', background: 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
            }}
            title="Close"
          >
            <X size={15} color="#8a8f98" />
          </motion.button>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
