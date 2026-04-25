'use client';
import { useEffect, useCallback, useRef, useState } from 'react';
import { useGesture } from '@use-gesture/react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchProjects, setSelectedProject } from '@/store/projectSlice';
import { fetchWorkspaces, setSelectedWorkspace } from '@/store/workspaceSlice';
import { fetchConversations, createConversation, openTab, loadMessages, restoreTabs } from '@/store/conversationSlice';
import { fetchCapabilities, createTerminal } from '@/store/terminalSlice';
import { setSidebarOpen } from '@/store/uiSlice';
import {
  openWindow, addTabToWindow, focusWindow,
  restoreWindows, WindowState,
} from '@/store/osSlice';
import { useLiveKitContext } from '@/providers/LiveKitProvider';
import { AgentType, WindowTab } from '@/types';
import { AppDef, APP_MAP } from '@/lib/appRegistry';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import MenuBar from '@/components/os/MenuBar';
import Dock from '@/components/os/Dock';
import AppDrawer from '@/components/os/AppDrawer';
import WindowManager from '@/components/os/WindowManager';
import MobileTabStrip from '@/components/os/MobileTabStrip';
import AppSwitcher from '@/components/os/AppSwitcher';
import AppPicker from '@/components/os/AppPicker';
import Sidebar from '@/components/layout/Sidebar';
import { useIsMobile } from '@/hooks/useIsMobile';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

const ThreeBackground = dynamic(() => import('@/components/three/ThreeBackground'), { ssr: false });

function makeTab(cid: string, appId: string, title: string, type: WindowTab['type']): WindowTab {
  return { id: 'tab-' + cid, cid, appId, title, type };
}

export default function Home() {
  const dispatch = useAppDispatch();
  const isMobile = useIsMobile();
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const windows = useAppSelector(s => s.os.windows);
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const nextZIndex = useAppSelector(s => s.os.nextZIndex);
  const closedCids = useAppSelector(s => s.os.closedCids ?? []);
  const liveWallpaperEnabled = useAppSelector(s => s.ui.liveWallpaperEnabled);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const { connectToConversation } = useLiveKitContext();
  const restoredRef = useRef(false);
  const desktopRef = useRef<HTMLDivElement | null>(null);
  const [desktopSize, setDesktopSize] = useState({ w: 800, h: 600 });
  const [mounted, setMounted] = useState(false);
  const [dockHidden, setDockHidden] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [mobilePickerWindowId, setMobilePickerWindowId] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    const el = desktopRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setDesktopSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [mounted]);

  // Mobile swipe-up gesture → AppSwitcher
  const swipeGestureBind = useGesture({
    onDrag: ({ direction: [, dy], distance: [, dist], last, xy: [, y] }) => {
      if (!isMobile || !last) return;
      const screenH = window.innerHeight;
      if (dy < 0 && dist > 60 && y > screenH - 120) {
        setSwitcherOpen(true);
      }
    },
  }, { drag: { filterTaps: true, pointer: { touch: true } } });

  // Keyboard shortcuts
  const handleNewTabFromKeyboard = useCallback((windowId: string) => {
    setMobilePickerWindowId(windowId);
  }, []);
  useKeyboardShortcuts(handleNewTabFromKeyboard);

  // Boot: restore workspace/project/tabs/windows
  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    if (isMobile) dispatch(setSidebarOpen(false));

    (async () => {
      const workspacesResult = await dispatch(fetchWorkspaces());
      let savedWorkspace: string | null = null;
      try { savedWorkspace = localStorage.getItem('neuro_selected_workspace') || null; } catch {}
      if (!savedWorkspace && fetchWorkspaces.fulfilled.match(workspacesResult)) {
        const ws = workspacesResult.payload;
        if (ws.length > 0) savedWorkspace = ws[0].id;
      }
      if (savedWorkspace) dispatch(setSelectedWorkspace(savedWorkspace));

      dispatch(fetchProjects(savedWorkspace));
      let savedProjectId: string | null = null;
      try { savedProjectId = localStorage.getItem('neuro_selected_project') || null; } catch {}
      if (savedProjectId) dispatch(setSelectedProject(savedProjectId));

      await dispatch(fetchConversations({ projectId: savedProjectId, agencyId: savedWorkspace }));
      await dispatch(restoreTabs());

      // Restore OS window layout
      try {
        const ws = savedWorkspace || 'global';
        const proj = savedProjectId || 'global';
        const saved = localStorage.getItem(`neuro_os_${ws}_${proj}`);
        if (saved) {
          const parsed = JSON.parse(saved) as { windows: WindowState[]; activeWindowId: string | null };
          if (parsed.windows?.length > 0) {
            dispatch(restoreWindows({ windows: parsed.windows, activeWindowId: parsed.activeWindowId }));
          }
        }
      } catch {}
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

  useEffect(() => { dispatch(fetchProjects(selectedWorkspaceId)); }, [selectedWorkspaceId, dispatch]);

  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(fetchConversations({ projectId: selectedProjectId, agencyId: selectedWorkspaceId }));
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedProjectId, selectedWorkspaceId, dispatch]);

  useEffect(() => { dispatch(fetchCapabilities()); }, [dispatch]);

  // Auto-window: attach orphan tabs to active window (or spawn one)
  useEffect(() => {
    const allTabCidsInWindows = new Set(windows.flatMap(w => w.tabs.map(t => t.cid)));
    const closedSet = new Set(closedCids);
    const orphans = openTabs.filter(t => !allTabCidsInWindows.has(t.cid) && !closedSet.has(t.cid));
    if (orphans.length === 0) return;

    const ww = desktopSize.w;
    const wh = desktopSize.h;
    const targetWindow = windows.find(w => w.id === activeWindowId);

    orphans.forEach((tab) => {
      const appId = tab.type === 'terminal' ? 'terminal'
                  : tab.type === 'neuroide' ? 'ide'
                  : (tab.agentId && APP_MAP[tab.agentId as keyof typeof APP_MAP]) ? tab.agentId as keyof typeof APP_MAP
                  : 'neuro';
      const newTab = makeTab(tab.cid, appId, tab.title || APP_MAP[appId as keyof typeof APP_MAP]?.name || 'Tab', tab.type ?? 'chat');

      if (targetWindow) {
        dispatch(addTabToWindow({ windowId: targetWindow.id, tab: newTab, makeActive: true }));
      } else {
        const winId = 'w-' + tab.cid;
        dispatch(openWindow({
          id: winId,
          x: isMobile ? 0 : 60,
          y: isMobile ? 0 : 40,
          width: isMobile ? ww : Math.min(ww * 0.6, 900),
          height: isMobile ? wh : Math.min(wh * 0.7, 700),
          zIndex: nextZIndex,
          minimized: false,
          maximized: isMobile,
          tabs: [newTab],
          activeTabId: newTab.id,
        }));
      }
    });
  }, [openTabs, windows, closedCids, desktopSize, nextZIndex, activeWindowId, dispatch, isMobile]);

  // Add tab to specific window
  const handleNewTabInWindow = useCallback(async (windowId: string, appId: string, tabKind: string) => {
    const app = APP_MAP[appId as keyof typeof APP_MAP];
    if (!app) return;

    if (tabKind === 'terminal') {
      const r = await dispatch(createTerminal({ workspace_id: selectedWorkspaceId || 'default', project_id: selectedProjectId }));
      if (createTerminal.fulfilled.match(r)) {
        const t = r.payload;
        dispatch(openTab({ cid: t.cid, title: t.title || 'Terminal', agentId: 'terminal', isActive: true, type: 'terminal', tmuxSession: t.tmux_session }));
        dispatch(addTabToWindow({ windowId, tab: makeTab(t.cid, 'terminal', t.title || 'Terminal', 'terminal'), makeActive: true }));
      }
      return;
    }
    if (tabKind === 'neuroide') {
      const cid = 'neuroide-' + Date.now().toString(36);
      dispatch(openTab({ cid, title: 'NeuroIDE', agentId: 'neuroide', isActive: true, type: 'neuroide' }));
      dispatch(addTabToWindow({ windowId, tab: makeTab(cid, 'ide', 'NeuroIDE', 'neuroide'), makeActive: true }));
      return;
    }
    const agentType = app.agentType || AgentType.NEURO;
    const result = await dispatch(createConversation({ agentId: agentType, projectId: selectedProjectId }));
    if (createConversation.fulfilled.match(result)) {
      const conv = result.payload;
      dispatch(openTab({ cid: conv.id, title: conv.title || app.name, agentId: conv.agentId ?? agentType, isActive: true }));
      dispatch(addTabToWindow({ windowId, tab: makeTab(conv.id, app.id, conv.title || app.name, 'chat'), makeActive: true }));
      connectToConversation(conv.id);
    }
  }, [dispatch, selectedProjectId, selectedWorkspaceId, connectToConversation]);

  // Helper: add tab to active window or spawn new window
  const _openOrAddTab = useCallback((newTab: WindowTab, ww: number, wh: number) => {
    const targetWindow = windows.find(w => w.id === activeWindowId);
    if (targetWindow) {
      dispatch(addTabToWindow({ windowId: targetWindow.id, tab: newTab, makeActive: true }));
    } else {
      dispatch(openWindow({
        id: 'w-' + newTab.cid,
        x: isMobile ? 0 : 80 + Math.random() * 100,
        y: isMobile ? 0 : 50 + Math.random() * 60,
        width: isMobile ? ww : Math.min(ww * 0.55, 800),
        height: isMobile ? wh : Math.min(wh * 0.65, 600),
        zIndex: nextZIndex,
        minimized: false,
        maximized: isMobile,
        tabs: [newTab],
        activeTabId: newTab.id,
      }));
    }
  }, [windows, activeWindowId, dispatch, isMobile, nextZIndex]);

  // Launch app from Dock/AppDrawer
  const handleLaunchApp = useCallback(async (app: AppDef) => {
    const ww = desktopSize.w;
    const wh = desktopSize.h;

    if (app.tabKind === 'terminal') {
      const r = await dispatch(createTerminal({ workspace_id: selectedWorkspaceId || 'default', project_id: selectedProjectId }));
      if (createTerminal.fulfilled.match(r)) {
        const t = r.payload;
        dispatch(openTab({ cid: t.cid, title: t.title || 'Terminal', agentId: 'terminal', isActive: true, type: 'terminal', tmuxSession: t.tmux_session }));
        _openOrAddTab(makeTab(t.cid, 'terminal', t.title || 'Terminal', 'terminal'), ww, wh);
      }
      return;
    }
    if (app.tabKind === 'neuroide') {
      const cid = 'neuroide-' + Date.now().toString(36);
      dispatch(openTab({ cid, title: 'NeuroIDE', agentId: 'neuroide', isActive: true, type: 'neuroide' }));
      _openOrAddTab(makeTab(cid, 'ide', 'NeuroIDE', 'neuroide'), ww, wh);
      return;
    }
    const agentType = app.agentType || AgentType.NEURO;
    const result = await dispatch(createConversation({ agentId: agentType, projectId: selectedProjectId }));
    if (createConversation.fulfilled.match(result)) {
      const conv = result.payload;
      dispatch(openTab({ cid: conv.id, title: conv.title || app.name, agentId: conv.agentId ?? agentType, isActive: true }));
      _openOrAddTab(makeTab(conv.id, app.id, conv.title || app.name, 'chat'), ww, wh);
      connectToConversation(conv.id);
    }
  }, [dispatch, selectedProjectId, selectedWorkspaceId, connectToConversation, desktopSize, _openOrAddTab]);

  if (!mounted) return <div style={{ height: '100vh', background: '#0a0a0b' }} />;

  // Mobile shell
  if (isMobile) {
    return (
      <>
        {liveWallpaperEnabled && <ThreeBackground />}
        <div style={{
          display: 'flex', flexDirection: 'column',
          height: 'var(--app-height)', overflow: 'hidden',
          position: 'relative', zIndex: 1,
        }}>
          <MobileTabStrip
            activeWindowId={activeWindowId}
            onMenuOpen={() => {}}
            onNewTab={(windowId) => setMobilePickerWindowId(windowId)}
            onSwitcherOpen={() => setSwitcherOpen(true)}
          />
          <div
            ref={contentRef}
            {...(swipeGestureBind() as any)}
            style={{ flex: 1, position: 'relative', overflow: 'hidden', touchAction: 'pan-x pan-y' }}
          >
            <WindowManager onNewTab={handleNewTabInWindow} />
          </div>
        </div>

        {mobilePickerWindowId && (
          <AppPicker
            onPick={(appId, tabKind) => { handleNewTabInWindow(mobilePickerWindowId, appId, tabKind); setMobilePickerWindowId(null); }}
            onClose={() => setMobilePickerWindowId(null)}
          />
        )}

        <AppSwitcher
          open={switcherOpen}
          onClose={() => setSwitcherOpen(false)}
          onNewWindow={() => { setSwitcherOpen(false); setMobilePickerWindowId('__new__'); }}
        />
      </>
    );
  }

  // Desktop shell
  return (
    <>
      {liveWallpaperEnabled && <ThreeBackground />}
      <div style={{
        display: 'flex', flexDirection: 'column',
        height: 'var(--app-height)', overflow: 'hidden',
        position: 'relative', zIndex: 1,
      }}>
        <MenuBar />
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
          {sidebarOpen && <Sidebar />}
          <div ref={desktopRef} style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
            <WindowManager onNewTab={handleNewTabInWindow} />
          </div>
        </div>

        <div
          onClick={() => setDockHidden(h => !h)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: 14, flexShrink: 0, cursor: 'pointer',
            background: 'transparent', zIndex: 101, position: 'relative',
          }}
        >
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '2px 12px', borderRadius: 6,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}>
            <div style={{ width: 24, height: 2, borderRadius: 1, background: 'rgba(255,255,255,0.2)' }} />
            {dockHidden
              ? <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>▲</span>
              : <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>▼</span>
            }
          </div>
        </div>

        <AnimatePresence initial={false}>
          {!dockHidden && (
            <motion.div
              key="dock"
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '100%', opacity: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.8 }}
              style={{ flexShrink: 0 }}
            >
              <Dock onLaunch={handleLaunchApp} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AppDrawer onLaunch={handleLaunchApp} />

      <AppSwitcher
        open={switcherOpen}
        onClose={() => setSwitcherOpen(false)}
        onNewWindow={() => { setSwitcherOpen(false); }}
      />
    </>
  );
}
