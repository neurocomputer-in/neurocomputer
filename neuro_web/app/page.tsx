'use client';
import { useEffect, useCallback, useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchProjects, setSelectedProject } from '@/store/projectSlice';
import { fetchWorkspaces, setSelectedWorkspace } from '@/store/workspaceSlice';
import { fetchConversations, createConversation, openTab, switchProjectTabs, loadMessages, restoreTabs } from '@/store/conversationSlice';
import { fetchCapabilities } from '@/store/terminalSlice';
import { TERMINAL_LIVE_COL_PX, setPaneActiveCid } from '@/store/uiSlice';
import PaneFrame from '@/components/panes/PaneFrame';
import { usePaneShortcuts } from '@/components/panes/usePaneShortcuts';
import { useLiveKitContext } from '@/providers/LiveKitProvider';
import { AGENT_LIST, AgentType } from '@/types';
import dynamic from 'next/dynamic';
import Sidebar from '@/components/layout/Sidebar';
import TopBar from '@/components/layout/TopBar';
import TabBar from '@/components/layout/TabBar';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';

const ThreeBackground = dynamic(() => import('@/components/three/ThreeBackground'), { ssr: false });
const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });
const SpatialRoot = dynamic(() => import('@/components/spatial/SpatialRoot'), { ssr: false });
import SpatialErrorBoundary from '@/components/spatial/SpatialErrorBoundary';

export default function Home() {
  const dispatch = useAppDispatch();
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const { connectToConversation } = useLiveKitContext();
  const restoredRef = useRef(false);

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;

    (async () => {
      // Fetch workspaces first, then auto-select if none saved
      const workspacesResult = await dispatch(fetchWorkspaces());
      let savedWorkspace: string | null = null;
      try {
        const saved = localStorage.getItem('neuro_selected_workspace');
        if (saved) savedWorkspace = saved || null;
      } catch {}

      // Auto-select first workspace if none saved
      if (!savedWorkspace && fetchWorkspaces.fulfilled.match(workspacesResult)) {
        const workspaces = workspacesResult.payload;
        if (workspaces.length > 0) {
          savedWorkspace = workspaces[0].id;
        }
      }
      if (savedWorkspace) dispatch(setSelectedWorkspace(savedWorkspace));

      dispatch(fetchProjects(savedWorkspace));

      let savedProjectId: string | null = null;
      try {
        const saved = localStorage.getItem('neuro_selected_project');
        if (saved) savedProjectId = saved || null;
      } catch {}

      if (savedProjectId) {
        dispatch(setSelectedProject(savedProjectId));
      }
      dispatch(fetchConversations({ projectId: savedProjectId, agencyId: savedWorkspace }));
      dispatch(restoreTabs());
    })();
  }, [dispatch]);

  useEffect(() => {
    if (activeTabCid) {
      dispatch(loadMessages(activeTabCid));
      connectToConversation(activeTabCid);
    }
  }, [activeTabCid, connectToConversation, dispatch]);

  useEffect(() => {
    dispatch(fetchConversations({ projectId: selectedProjectId, agencyId: selectedWorkspaceId }));
  }, [selectedProjectId, selectedWorkspaceId, dispatch]);

  useEffect(() => {
    dispatch(fetchProjects(selectedWorkspaceId));
  }, [selectedWorkspaceId, dispatch]);

  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(fetchConversations({ projectId: selectedProjectId, agencyId: selectedWorkspaceId }));
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedProjectId, selectedWorkspaceId, dispatch]);

  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);

  const handleNewTab = useCallback(async () => {
    // Use the filtered agent for new conversations, default to 'neuro' if "All"
    const newAgentType = agentFilter === AgentType.ALL ? AgentType.NEURO : agentFilter;
    const result = await dispatch(createConversation({
      agentId: newAgentType,
      projectId: selectedProjectId,
    }));
    if (createConversation.fulfilled.match(result)) {
      const conv = result.payload;
      dispatch(openTab({
        cid: conv.id,
        title: conv.title || 'New Chat',
        agentId: conv.agentId ?? newAgentType,
        isActive: true,
      }));
      dispatch(setPaneActiveCid({ id: focusedPaneId, cid: conv.id }));
      await connectToConversation(conv.id);
    }
  }, [dispatch, agentFilter, selectedProjectId, connectToConversation, focusedPaneId]);

  // Probe terminal capability once at boot so the TerminalButton in
  // the top bar can gate itself and the dropdown knows availability.
  useEffect(() => { dispatch(fetchCapabilities()); }, [dispatch]);

  usePaneShortcuts();

  const tabBarPosition = useAppSelector(s => s.ui.tabBarPosition);
  const liveWallpaperEnabled = useAppSelector(s => s.ui.liveWallpaperEnabled);
  const interfaceMode = useAppSelector(s => s.ui.interfaceMode);
  const liveMode = useAppSelector(s => s.ui.liveMode);
  const panes = useAppSelector(s => s.ui.panes);
  const activeTabKind = useAppSelector(s => {
    const t = s.conversations.openTabs.find(x => x.cid === s.conversations.activeTabCid);
    return t?.type === 'terminal' ? 'terminal' : 'chat';
  });

  // Single-pane mode: keep the only pane's activeCid in lockstep with the
  // Redux activeTabCid that the TabBar already drives. Split-pane flows
  // own their own per-pane state via setPaneActiveCid.
  useEffect(() => {
    if (panes.length === 1 && panes[0].activeCid !== activeTabCid) {
      dispatch(setPaneActiveCid({ id: panes[0].id, cid: activeTabCid }));
    }
  }, [activeTabCid, panes, dispatch]);
  const terminalLiveColumn = liveMode && activeTabKind === 'terminal';

  // The Redux initial state reads localStorage (tabBarPosition,
  // interfaceMode, liveWallpaperEnabled, persisted panes/tabs), so
  // server-rendered HTML diverges from the client's first render.
  // Gate the whole page on mount — SSR emits an empty shell, the
  // client paints the real UI after hydration. Cheap and correct.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  if (!mounted) {
    return <div style={{ height: '100vh', background: '#0a0a0b' }} />;
  }

  return (
    <>
      {liveWallpaperEnabled && <ThreeBackground />}
      <div style={{
        display: 'flex', flexDirection: 'column',
        height: '100vh', overflow: 'hidden',
        position: 'relative', zIndex: 1,
      }}>
      <TopBar />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar />
        <div className="glass-panel" style={{
          flex: terminalLiveColumn ? `0 0 ${TERMINAL_LIVE_COL_PX}px` : 1,
          width: terminalLiveColumn ? TERMINAL_LIVE_COL_PX : undefined,
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
          transition: 'flex 0.25s ease, width 0.25s ease',
        }}>
          {tabBarPosition === 'top' && <TabBar onNewTab={handleNewTab} />}
          {interfaceMode === 'spatial' && panes.length === 1
            ? (<SpatialErrorBoundary
                 fallback={(
                   <div style={{
                     flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                     background: '#0a0a0b', color: '#d0d6e0', fontSize: 13, padding: 24,
                     textAlign: 'center',
                   }}>
                     3D view crashed. Reload or switch back to Classic in Settings.
                   </div>
                 )}>
                 <SpatialRoot />
               </SpatialErrorBoundary>)
            : (
              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'row' }}>
                {panes.map(p => (
                  <PaneFrame key={p.id} paneId={p.id} activeCid={p.activeCid} />
                ))}
              </div>
            )}
          {tabBarPosition === 'bottom' && <TabBar onNewTab={handleNewTab} />}
        </div>
      </div>
    </div>
    </>
  );
}
