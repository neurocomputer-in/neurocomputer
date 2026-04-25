'use client';
import { Plus, X, MessageSquare, Folder, Settings, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setShowProjectCreate, setSidebarOpen } from '@/store/uiSlice';
import { AGENT_LIST, AgentType } from '@/types';
import AgentIcon from '@/components/agent/AgentIcon';
import ProjectList from '@/components/project/ProjectList';
import ProjectCreate from '@/components/project/ProjectCreate';
import WorkspaceDropdown from '@/components/workspace/WorkspaceDropdown';
import ProjectDropdown from '@/components/project/ProjectDropdown';
import { useLiveKitContext } from '@/providers/LiveKitProvider';
import { setActiveTab, closeTab, loadMessages, openTab } from '@/store/conversationSlice';
import { openWindow, focusWindow } from '@/store/osSlice';
import { APP_MAP } from '@/lib/appRegistry';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function Sidebar() {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const showProjectCreate = useAppSelector(s => s.ui.showProjectCreate);
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const conversations = useAppSelector(s => s.conversations.conversations);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const isMobile = useIsMobile();

  const projectIndex: Record<string, { name: string; color: string }> = {};
  for (const p of projects) {
    if (p.id) projectIndex[p.id] = { name: p.name, color: p.color };
  }
  const showProjectBadge = !selectedProjectId;

  const projectFor = (cid: string | undefined | null) => {
    if (!cid) return null;
    const conv = conversations.find(c => c.id === cid);
    const pid = conv?.projectId;
    return pid ? projectIndex[pid] || null : null;
  };

  const visibleTabs = agentFilter === AgentType.ALL
    ? openTabs
    : openTabs.filter(t => t.agentId === agentFilter);

  const openTabCids = new Set(openTabs.map(t => t.cid));
  const chatHistory = conversations.filter(c => {
    if (agentFilter !== AgentType.ALL && c.agentId !== agentFilter) return false;
    return true;
  });

  const { connectToConversation } = useLiveKitContext();
  const osWindows = useAppSelector(s => s.os.windows);
  const osNextZIndex = useAppSelector(s => s.os.nextZIndex);

  const handleTabClick = async (cid: string) => {
    dispatch(setActiveTab(cid));
    dispatch(loadMessages(cid));
    await connectToConversation(cid);

    const existing = osWindows.find(w => w.tabs.some(t => t.cid === cid));
    if (existing) {
      dispatch(focusWindow(existing.id));
    } else {
      const tab = openTabs.find(t => t.cid === cid);
      if (tab) {
        const appId = tab.type === 'terminal' ? 'terminal'
                    : tab.type === 'neuroide' ? 'ide'
                    : (tab.agentId && APP_MAP[tab.agentId as keyof typeof APP_MAP]) ? tab.agentId as keyof typeof APP_MAP
                    : 'neuro';
        const app = APP_MAP[appId] || APP_MAP.neuro;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const tabId = 'tab-' + cid;
        dispatch(openWindow({
          id: 'w-' + cid,
          tabs: [{ id: tabId, cid, appId: app.id, title: tab.title || app.name, type: tab.type ?? 'chat' }],
          activeTabId: tabId,
          x: 80 + Math.random() * 60,
          y: 50 + Math.random() * 40,
          width: Math.min(vw * 0.55, 900),
          height: Math.min(vh * 0.65, 700),
          zIndex: osNextZIndex,
          minimized: false,
          maximized: false,
        }));
      }
    }
  };

  const handleCloseTab = (e: React.MouseEvent, cid: string) => {
    e.stopPropagation();
    dispatch(closeTab(cid));
  };

  const closeSidebar = () => { if (isMobile && sidebarOpen) dispatch(setSidebarOpen(false)); };

  const sidebarWidth = isMobile ? '85vw' : '272px';
  const sidebarMaxWidth = isMobile ? '320px' : undefined;

  const sidebarContent = (
    <>
      {/* Workspace & Project selectors */}
      <div style={{ padding: '14px 12px 4px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <WorkspaceDropdown />
        <ProjectDropdown />
      </div>

      <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '4px 16px' }} />

      {/* Projects */}
      <div style={{ padding: '14px 16px 8px' }}>
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginBottom: '10px',
        }}>
          <span style={{
            fontSize: '11px', textTransform: 'uppercase',
            letterSpacing: '0.8px', color: '#62666d', fontWeight: 510,
          }}>
            Projects
          </span>
          <motion.div
            whileHover={{ scale: 1.1, opacity: 0.8, backgroundColor: 'rgba(255,255,255,0.05)' }}
            whileTap={{ scale: 0.95 }}
            onClick={() => dispatch(setShowProjectCreate(true))}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '20px', height: '20px', borderRadius: '4px',
              cursor: 'pointer', opacity: 0.4,
            }}
          >
            <Plus size={14} color="#8a8f98" />
          </motion.div>
        </div>
        <ProjectList projects={projects} />
      </div>

      <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '4px 16px' }} />

      {/* Open Sessions */}
      <div style={{ padding: '10px 16px 6px' }}>
        <span style={{
          fontSize: '11px', textTransform: 'uppercase',
          letterSpacing: '0.8px', color: '#62666d', fontWeight: 510,
        }}>
          Open Sessions
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 12px 14px' }}>
        {visibleTabs.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: '8px', padding: '24px 8px', color: '#62666d',
          }}>
            <MessageSquare size={18} strokeWidth={1.5} />
            <span style={{ fontSize: '12px', fontWeight: 400 }}>No open sessions</span>
          </div>
        ) : (
          visibleTabs.map(tab => {
            const isActive = activeTabCid === tab.cid;
            const agent = AGENT_LIST.find(a => a.type === tab.agentId) ?? AGENT_LIST[1];
            return (
              <motion.div
                key={tab.cid}
                whileHover={!isActive ? { backgroundColor: 'rgba(255,255,255,0.03)' } : {}}
                whileTap={{ scale: 0.98 }}
                onClick={() => { handleTabClick(tab.cid); closeSidebar(); }}
                style={{
                  padding: '8px 10px',
                  background: isActive ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.01)',
                  border: isActive ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
                  borderRadius: '8px',
                  marginBottom: '2px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <div style={{
                  width: '28px', height: '28px', borderRadius: '6px',
                  background: 'rgba(255,255,255,0.04)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <AgentIcon agent={agent} size={14} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '13px', color: isActive ? '#f7f8f8' : '#d0d6e0',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    fontWeight: isActive ? 510 : 400,
                  }}>
                    {tab.title || 'New Chat'}
                  </div>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    marginTop: '1px',
                  }}>
                    <span style={{ fontSize: '11px', color: '#62666d', fontWeight: 400 }}>
                      {agent.name}
                    </span>
                    {showProjectBadge && (() => {
                      const p = projectFor(tab.cid);
                      if (!p) return null;
                      return (
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: '4px',
                          fontSize: '10px', color: '#8a8f98', fontWeight: 400,
                        }}>
                          <span style={{
                            width: '6px', height: '6px', borderRadius: '50%',
                            background: p.color, flexShrink: 0,
                          }} />
                          {p.name}
                        </span>
                      );
                    })()}
                  </div>
                  {tab.workdir && (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: '3px',
                      marginTop: '2px',
                    }}>
                      <Folder size={9} color="#7170ff" />
                      <span style={{
                        fontSize: '10px', color: 'var(--accent)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                      }}>
                        {tab.workdir.length > 28 ? '…' + tab.workdir.slice(-25) : tab.workdir}
                      </span>
                    </div>
                  )}
                </div>
                {isActive && (
                  <div style={{
                    width: '5px', height: '5px', borderRadius: '50%',
                    background: 'var(--accent)', flexShrink: 0,
                  }} />
                )}
                <motion.div
                  whileHover={{ opacity: 1, backgroundColor: 'rgba(239,68,68,0.1)' }}
                  onClick={(e) => handleCloseTab(e, tab.cid)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: '18px', height: '18px', borderRadius: '4px',
                    flexShrink: 0, opacity: 0.3,
                  }}
                >
                  <X size={12} color="#8a8f98" />
                </motion.div>
              </motion.div>
            );
          })
        )}
      </div>

      {/* Chat History */}
      {chatHistory.length > 0 && (
        <>
          <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '4px 16px' }} />
          <div style={{ padding: '10px 16px 6px', display: 'flex',
                        alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{
              fontSize: '11px', textTransform: 'uppercase',
              letterSpacing: '0.8px', color: '#62666d', fontWeight: 510,
            }}>
              Chat History
            </span>
            <span style={{ fontSize: '10px', color: '#62666d' }}>
              {chatHistory.length}
            </span>
          </div>
          <div style={{ padding: '4px 12px 14px', overflowY: 'auto', maxHeight: '260px' }}>
            {chatHistory.map(conv => {
              const agent = AGENT_LIST.find(a => a.type === conv.agentId)
                ?? AGENT_LIST.find(a => a.type === AgentType.NEURO)!;
              const isOpen = openTabCids.has(conv.id);
              return (
                <motion.div
                  key={conv.id}
                  whileHover={!isOpen ? { backgroundColor: 'rgba(255,255,255,0.03)', opacity: 1 } : {}}
                  whileTap={{ scale: 0.98 }}
                  onClick={async () => {
                    if (isOpen) {
                      dispatch(setActiveTab(conv.id));
                      dispatch(loadMessages(conv.id));
                      await connectToConversation(conv.id);
                    } else {
                      dispatch(openTab({
                        cid: conv.id,
                        title: conv.title || 'New Chat',
                        agentId: conv.agentId || AgentType.NEURO,
                        isActive: true,
                        workdir: conv.workdir,
                      }));
                      dispatch(setActiveTab(conv.id));
                      dispatch(loadMessages(conv.id));
                      await connectToConversation(conv.id);
                    }
                    closeSidebar();
                  }}
                  style={{
                    padding: '7px 10px',
                    background: isOpen ? 'rgba(113,112,255,0.05)' : 'rgba(255,255,255,0.01)',
                    border: isOpen ? '1px solid rgba(113,112,255,0.15)' : '1px solid transparent',
                    borderRadius: '8px',
                    marginBottom: '2px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    opacity: isOpen ? 1 : 0.65,
                  }}
                >
                  <div style={{
                    width: '26px', height: '26px', borderRadius: '6px',
                    background: 'rgba(255,255,255,0.04)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, position: 'relative',
                  }}>
                    <AgentIcon agent={agent} size={13} />
                    {isOpen && (
                      <span style={{
                        position: 'absolute', top: '-2px', right: '-2px',
                        width: '7px', height: '7px', borderRadius: '50%',
                        background: 'var(--accent)',
                        border: '1.5px solid #0f1011',
                      }} />
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '12px', color: '#8a8f98',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {conv.title || 'New Chat'}
                    </div>
                    {showProjectBadge && conv.projectId && projectIndex[conv.projectId] && (
                      <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: '4px',
                        marginTop: '2px',
                        fontSize: '10px', color: '#62666d', fontWeight: 400,
                      }}>
                        <span style={{
                          width: '6px', height: '6px', borderRadius: '50%',
                          background: projectIndex[conv.projectId].color, flexShrink: 0,
                        }} />
                        {projectIndex[conv.projectId].name}
                      </div>
                    )}
                    {conv.workdir && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginTop: '2px' }}>
                        <Folder size={9} color="#7170ff" />
                        <span style={{
                          fontSize: '10px', color: 'var(--accent)',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                        }}>
                          {conv.workdir.length > 28 ? '…' + conv.workdir.slice(-25) : conv.workdir}
                        </span>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </>
      )}

      {/* Bottom nav */}
      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.05)',
        padding: '6px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        flexShrink: 0,
      }}>
        <Link
          href="/settings?tab=profile"
          onClick={closeSidebar}
          style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 10px', borderRadius: '6px',
            color: '#d0d6e0', fontSize: '13px', fontWeight: 400,
            textDecoration: 'none', transition: 'background 0.12s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <User size={14} color="#8a8f98" />
          <span>Profile</span>
        </Link>
        <Link
          href="/settings"
          onClick={closeSidebar}
          style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 10px', borderRadius: '6px',
            color: '#d0d6e0', fontSize: '13px', fontWeight: 400,
            textDecoration: 'none', transition: 'background 0.12s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <Settings size={14} color="#8a8f98" />
          <span>Settings</span>
        </Link>
      </div>

      {showProjectCreate && <ProjectCreate />}
    </>
  );

  if (isMobile) {
    return (
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={closeSidebar}
              style={{
                position: 'fixed', inset: 0,
                background: 'rgba(0,0,0,0.6)',
                zIndex: 200,
              }}
            />
            <motion.div
              key="sidebar"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="glass-panel"
              style={{
                position: 'fixed', top: 0, left: 0, bottom: 0,
                width: sidebarWidth, maxWidth: sidebarMaxWidth,
                display: 'flex', flexDirection: 'column',
                borderRight: '1px solid rgba(255,255,255,0.05)',
                overflow: 'visible',
                zIndex: 201,
              }}
            >
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    );
  }

  return (
    <div
      className="glass-panel"
      style={{
        width: sidebarOpen ? '272px' : '0px',
        minWidth: sidebarOpen ? '272px' : '0px',
        display: 'flex',
        flexDirection: 'column',
        borderRight: sidebarOpen ? '1px solid rgba(255,255,255,0.05)' : 'none',
        overflow: sidebarOpen ? 'visible' : 'hidden',
        flexShrink: 0,
        transition: 'width 0.2s ease, min-width 0.2s ease',
      }}
    >
      {sidebarContent}
    </div>
  );
}
