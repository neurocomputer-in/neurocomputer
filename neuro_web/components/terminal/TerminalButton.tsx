'use client';
import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Plus, Terminal as TerminalIcon, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { createTerminal, fetchTerminalTabs, deleteTerminal } from '@/store/terminalSlice';
import { openTab, closeTab, setActiveTab } from '@/store/conversationSlice';
import { setPaneActiveCid } from '@/store/uiSlice';
import type { TerminalTab } from '@/types';

export default function TerminalButton() {
  const dispatch = useAppDispatch();
  const available = useAppSelector(s => s.terminal.available);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeCid = useAppSelector(s => s.conversations.activeTabCid);
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);

  const scopeKey = `${selectedWorkspaceId || 'default'}:${selectedProjectId || 'main-default'}`;
  const tabs = useAppSelector(s => s.terminal.tabsByProject[scopeKey] || []);

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    dispatch(fetchTerminalTabs({
      project_id: selectedProjectId,
      agency_id: selectedWorkspaceId,
    }));
  }, [open, selectedProjectId, selectedWorkspaceId, dispatch]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const createNew = async () => {
    setOpen(false);
    const r = await dispatch(createTerminal({
      workspace_id: selectedWorkspaceId || 'default',
      project_id: selectedProjectId,
    }));
    if (createTerminal.fulfilled.match(r)) {
      const t = r.payload;
      dispatch(openTab({
        cid: t.cid,
        title: t.title || 'terminal',
        agentId: 'terminal',
        isActive: true,
        type: 'terminal',
        tmuxSession: t.tmux_session,
      }));
      dispatch(setPaneActiveCid({ id: focusedPaneId, cid: t.cid }));
    }
  };

  const openExisting = (t: TerminalTab) => {
    setOpen(false);
    // If tab already open in this session, just activate it.
    const existing = openTabs.find(x => x.cid === t.cid);
    if (existing) {
      dispatch(setActiveTab(t.cid));
      dispatch(setPaneActiveCid({ id: focusedPaneId, cid: t.cid }));
      return;
    }
    dispatch(openTab({
      cid: t.cid,
      title: t.title || 'terminal',
      agentId: 'terminal',
      isActive: true,
      type: 'terminal',
      tmuxSession: t.tmux_session,
    }));
    dispatch(setPaneActiveCid({ id: focusedPaneId, cid: t.cid }));
  };

  const removeTab = async (t: TerminalTab, kill: boolean) => {
    await dispatch(deleteTerminal({ cid: t.cid, killSession: kill }));
    dispatch(closeTab(t.cid));
    dispatch(fetchTerminalTabs({
      project_id: selectedProjectId,
      agency_id: selectedWorkspaceId,
    }));
  };

  if (available === false) return null;

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => setOpen(v => !v)}
        title="Terminals"
        data-testid="terminal-button-trigger"
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: 'rgba(255,255,255,0.02)', padding: '5px 10px',
          borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
          transition: 'background 0.15s',
          border: '1px solid rgba(255,255,255,0.05)',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
      >
        <TerminalIcon size={13} color="#d0d6e0" />
        <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>Terminal</span>
        <ChevronDown size={12} color="#62666d" style={{
          transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }} />
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="glass-dropdown"
            style={{
              position: 'absolute', top: '100%', left: 0, marginTop: '6px',
              borderRadius: '8px', minWidth: '260px', zIndex: 100, overflow: 'hidden',
              boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            }}
          >
            <div style={{ padding: '4px' }}>
              <button
                onClick={createNew}
                style={actionItemStyle}
                data-testid="terminal-new"
              >
                <div style={iconBoxStyle}><Plus size={14} color="#c4b5fd" /></div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 510, color: '#f7f8f8' }}>New Terminal</div>
                  <div style={{ fontSize: '11px', color: '#62666d', marginTop: '1px' }}>
                    Creates a tmux session in current project
                  </div>
                </div>
              </button>

              {tabs.length > 0 && (
                <div style={{
                  padding: '8px 12px 4px',
                  fontSize: '10px', textTransform: 'uppercase',
                  letterSpacing: '0.6px', color: '#62666d', fontWeight: 510,
                }}>
                  Existing
                </div>
              )}

              {tabs.map(t => {
                const isOpen = openTabs.some(x => x.cid === t.cid);
                const isActive = t.cid === activeCid;
                return (
                  <div
                    key={t.cid}
                    onClick={() => openExisting(t)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                      color: isActive ? '#f7f8f8' : '#d0d6e0',
                      background: isActive ? 'rgba(255,255,255,0.05)' : 'transparent',
                      borderRadius: '6px', transition: 'background 0.12s',
                    }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <div style={iconBoxStyle}>
                      <TerminalIcon size={13} color={isActive ? '#c4b5fd' : '#8a8f98'} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '13px', fontWeight: 510, overflow: 'hidden',
                                    textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {t.title}{isOpen && <span style={{ color: '#7170ff' }}> •</span>}
                      </div>
                      <div style={{
                        fontSize: '10px', color: '#62666d', marginTop: '1px',
                        fontFamily: "'Berkeley Mono', ui-monospace, monospace",
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {t.tmux_session}
                      </div>
                    </div>
                    <button
                      title="Close tab + kill tmux session"
                      onClick={(e) => { e.stopPropagation(); removeTab(t, true); }}
                      style={{
                        border: 'none', background: 'transparent',
                        cursor: 'pointer', padding: '4px', borderRadius: '4px',
                        display: 'flex', alignItems: 'center',
                      }}
                    >
                      <X size={12} color="#62666d" />
                    </button>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const actionItemStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '10px',
  padding: '8px 10px', width: '100%', textAlign: 'left',
  cursor: 'pointer', fontSize: '13px', color: '#d0d6e0',
  background: 'transparent', border: 'none', borderRadius: '6px',
  fontFamily: 'inherit',
};

const iconBoxStyle: React.CSSProperties = {
  width: '30px', height: '30px', borderRadius: '6px',
  background: 'rgba(255,255,255,0.04)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flexShrink: 0,
};
