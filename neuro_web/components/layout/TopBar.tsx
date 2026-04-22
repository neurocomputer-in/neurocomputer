'use client';
import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { PanelLeftClose, PanelLeft, Wifi, WifiOff, Loader2, Volume2, VolumeX, Minus, Square, X, Layout, Box, Columns } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSidebarOpen, setTtsAutoPlay, setInterfaceMode, splitPane } from '@/store/uiSlice';
import WorkspaceDropdown from '@/components/workspace/WorkspaceDropdown';
import ThemeSelector from '@/components/three/ThemeSelector';
import AgentDropdown from '@/components/agent/AgentDropdown';
import TerminalButton from '@/components/terminal/TerminalButton';
import NeuroIDEButton from '@/components/neuroide/NeuroIDEButton';
import ProjectDropdown from '@/components/project/ProjectDropdown';

export default function TopBar() {
  const dispatch = useAppDispatch();
  const connectionStatus = useAppSelector(s => s.ui.connectionStatus);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const interfaceMode = useAppSelector(s => s.ui.interfaceMode);
  const paneCount = useAppSelector(s => s.ui.panes.length);
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

  return (
    <div
      className="glass-panel"
      style={{
        height: '48px',
        minHeight: '48px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: '8px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
        zIndex: 50,
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
          cursor: 'pointer', opacity: 0.8,
          ...noDragStyle,
        }}
      >
        {sidebarOpen ? <PanelLeftClose size={15} color="#d0d6e0" /> : <PanelLeft size={15} color="#d0d6e0" />}
      </motion.div>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', userSelect: 'none' }}>
        <div style={{
          width: '26px', height: '26px', borderRadius: '6px',
          background: '#5e6ad2',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 590, color: '#fff',
        }}>
          N
        </div>
        <span style={{ fontSize: '14px', fontWeight: 510, color: '#f7f8f8', letterSpacing: '-0.3px' }}>
          Neuro
        </span>
      </div>

      <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.05)' }} />

      <div style={noDragStyle}><WorkspaceDropdown /></div>

      <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.05)' }} />

      <div style={noDragStyle}><ProjectDropdown /></div>

      <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.05)' }} />

      <div style={noDragStyle}><AgentDropdown /></div>

      <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.05)' }} />

      <div style={noDragStyle}><TerminalButton /></div>

      <div style={noDragStyle}><NeuroIDEButton /></div>

      <div style={{ flex: 1 }} />

      {/* Interface mode: Classic ↔ 3D */}
      <div
        style={{
          display: 'inline-flex', padding: 2, gap: 2,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 8,
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

      {/* Split panes */}
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
          fontFamily: 'inherit',
          ...noDragStyle,
        }}
      >
        <Columns size={12} />
        <span>Split</span>
      </button>

      {/* Theme selector */}
      <div style={noDragStyle}><ThemeSelector /></div>

      {/* TTS toggle */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => dispatch(setTtsAutoPlay(!ttsAutoPlay))}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: ttsAutoPlay ? 'rgba(94,106,210,0.1)' : 'rgba(255,255,255,0.02)',
          padding: '5px 10px', borderRadius: '6px', cursor: 'pointer',
          userSelect: 'none', transition: 'background 0.15s, border-color 0.15s',
          ...noDragStyle,
          border: `1px solid ${ttsAutoPlay ? 'rgba(94,106,210,0.2)' : 'rgba(255,255,255,0.05)'}`,
        }}
        title={ttsAutoPlay ? 'Voice replies ON' : 'Voice replies OFF'}
      >
        {ttsAutoPlay ? <Volume2 size={13} color="#7170ff" /> : <VolumeX size={13} color="#62666d" />}
        <span style={{ fontSize: '11px', color: ttsAutoPlay ? '#828fff' : '#62666d', fontWeight: 510 }}>
          {ttsAutoPlay ? 'Voice' : 'Mute'}
        </span>
      </motion.div>

      {/* Connection status */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '5px',
        padding: '4px 8px', borderRadius: '6px',
        background: 'rgba(255,255,255,0.02)',
      }}>
        {connectionStatus === 'connected' ? (
          <Wifi size={12} color={statusColor} />
        ) : connectionStatus === 'connecting' ? (
          <Loader2 size={12} color={statusColor} style={{ animation: 'spin 1s linear infinite' }} />
        ) : (
          <WifiOff size={12} color={statusColor} />
        )}
      </div>

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
