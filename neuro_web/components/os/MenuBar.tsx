'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Wifi, WifiOff, Loader2, Volume2, VolumeX, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSidebarOpen, setTtsAutoPlay } from '@/store/uiSlice';
import { toggleLauncher } from '@/store/osSlice';
import { APP_MAP } from '@/lib/appRegistry';
import ThemeSelector from '@/components/three/ThemeSelector';
import { useIsMobile } from '@/hooks/useIsMobile';
import WorkspaceSwitcher from '@/components/workspace/WorkspaceSwitcher';
import ProjectPanel from '@/components/project/ProjectPanel';

export default function MenuBar() {
  const dispatch = useAppDispatch();
  const connectionStatus = useAppSelector(s => s.ui.connectionStatus);
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const windows = useAppSelector(s => s.os.windows);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const isMobile = useIsMobile();

  const [isDesktop, setIsDesktop] = useState(false);
  const [time, setTime] = useState('');
  const [wsSwitcherOpen, setWsSwitcherOpen] = useState(false);
  const [projectPanelOpen, setProjectPanelOpen] = useState(false);

  useEffect(() => { setIsDesktop(!!(window as any).neuroDesktop?.isDesktop); }, []);
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    update(); const iv = setInterval(update, 30000); return () => clearInterval(iv);
  }, []);

  const activeWin = windows.find(w => w.id === activeWindowId);
  const activeWinActiveTab = activeWin?.tabs.find(t => t.id === activeWin.activeTabId);
  const activeApp = activeWinActiveTab ? APP_MAP[activeWinActiveTab.appId as keyof typeof APP_MAP] : null;
  const currentWs = workspaces.find(w => w.id === selectedWorkspaceId);
  const currentProject = projects.find(p => p.id === selectedProjectId);

  const statusColor =
    connectionStatus === 'connected' ? '#27a644' :
    connectionStatus === 'connecting' ? '#f59e0b' : '#62666d';

  const noAppRegion = isDesktop ? { WebkitAppRegion: 'no-drag', appRegion: 'no-drag' } as any : {};

  return (
    <>
      <div
        className="glass-panel"
        style={{
          height: '30px', minHeight: '30px',
          display: 'flex', alignItems: 'center',
          padding: '0 12px', gap: '6px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          flexShrink: 0, zIndex: 200, overflow: 'visible',
          background: 'rgba(30,30,34,0.82)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          ...(isDesktop ? { WebkitAppRegion: 'drag', appRegion: 'drag' } as any : {}),
        }}
      >
        {/* Sidebar toggle */}
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => dispatch(setSidebarOpen(!sidebarOpen))}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20, borderRadius: 4, cursor: 'pointer', opacity: 0.7, flexShrink: 0, ...noAppRegion }}>
          {sidebarOpen ? <PanelLeftClose size={13} color="#d0d6e0" /> : <PanelLeft size={13} color="#d0d6e0" />}
        </motion.div>

        {/* Workspace chip */}
        <div style={{ position: 'relative', flexShrink: 0, ...noAppRegion }}>
          <button
            onClick={() => setWsSwitcherOpen(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'transparent', border: 'none', cursor: 'pointer',
              padding: '2px 6px', borderRadius: 5, transition: 'background 0.12s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            {currentWs ? (
              <div style={{ width: 14, height: 14, borderRadius: 4, background: `linear-gradient(135deg, ${currentWs.color}dd, ${currentWs.color}88)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 700, color: '#fff', flexShrink: 0 }}>
                {currentWs.name[0]?.toUpperCase()}
              </div>
            ) : null}
            <span style={{ fontSize: 12, color: '#c0c4cc', fontWeight: 500, maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {currentWs?.name ?? 'Workspace'}
            </span>
          </button>
          <WorkspaceSwitcher open={wsSwitcherOpen} onClose={() => setWsSwitcherOpen(false)} />
        </div>

        {/* Separator */}
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)', flexShrink: 0 }}>/</span>

        {/* Project chip */}
        <div style={{ position: 'relative', flexShrink: 0, ...noAppRegion }}>
          <button
            onClick={() => setProjectPanelOpen(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'transparent', border: 'none', cursor: 'pointer',
              padding: '2px 6px', borderRadius: 5, transition: 'background 0.12s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            {currentProject && (
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: currentProject.color, flexShrink: 0 }} />
            )}
            <span style={{ fontSize: 12, color: '#c0c4cc', fontWeight: 500, maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {currentProject?.name ?? 'All Projects'}
            </span>
          </button>
          <ProjectPanel open={projectPanelOpen} onClose={() => setProjectPanelOpen(false)} />
        </div>

        <div style={{ flex: 1 }} />

        {/* Active app name */}
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#e0e0e0', flexShrink: 0, marginRight: 4 }}>
          {activeApp ? activeApp.name : 'Neuro'}
        </span>

        {/* Right side items */}
        <div style={{ flexShrink: 0, ...noAppRegion }}><ThemeSelector /></div>
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => dispatch(setTtsAutoPlay(!ttsAutoPlay))}
          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 6px', borderRadius: 4, cursor: 'pointer', ...noAppRegion }}>
          {ttsAutoPlay ? <Volume2 size={12} color="#7170ff" /> : <VolumeX size={12} color="#62666d" />}
        </motion.div>

        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          {connectionStatus === 'connected' ? <Wifi size={11} color={statusColor} /> :
           connectionStatus === 'connecting' ? <Loader2 size={11} color={statusColor} style={{ animation: 'spin 1s linear infinite' }} /> :
           <WifiOff size={11} color={statusColor} />}
        </div>

        <span style={{ fontSize: '11px', color: '#888', flexShrink: 0, fontWeight: 500 }}>{time}</span>

        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    </>
  );
}
