'use client';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, Building2, Settings, Plus } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedWorkspace, fetchWorkspaces } from '@/store/workspaceSlice';
import { setAgentFilter } from '@/store/agentSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';
import { fetchProjects, setSelectedProject } from '@/store/projectSlice';
import { AGENT_LIST, AgentType } from '@/types';
import AgentIcon from '@/components/agent/AgentIcon';
import { apiUpdateWorkspace } from '@/services/api';
import WorkspaceCreate from './WorkspaceCreate';

export default function WorkspaceDropdown() {
  const dispatch = useAppDispatch();
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const [open, setOpen] = useState(false);
  const [editingWorkspaceId, setEditingWorkspaceId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setEditingWorkspaceId(null);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selected = workspaces.find(a => a.id === selectedWorkspaceId);
  const label = selected?.name ?? 'All';
  const color = selected?.color ?? '#8a8f98';

  const handleSelect = (workspaceId: string | null) => {
    if (workspaceId === selectedWorkspaceId) { setOpen(false); return; }
    dispatch(switchProjectTabs({
      fromProjectId: selectedProjectId, toProjectId: null,
      fromAgencyId: selectedWorkspaceId, toAgencyId: workspaceId,
    }));
    dispatch(setSelectedWorkspace(workspaceId));

    const workspace = workspaces.find(a => a.id === workspaceId);
    if (workspace) {
      dispatch(setAgentFilter(AgentType.ALL));
    }

    dispatch(setSelectedProject(null));
    dispatch(fetchProjects(workspaceId));
    dispatch(fetchConversations({ projectId: null, agencyId: workspaceId }));
    setOpen(false);
  };

  const editingWorkspace = editingWorkspaceId ? workspaces.find(a => a.id === editingWorkspaceId) : null;
  const allAgents = AGENT_LIST.filter(a => a.type !== AgentType.ALL);

  const handleToggleAgent = async (agentType: string) => {
    if (!editingWorkspace) return;
    const current = editingWorkspace.agents ?? [];
    const updated = current.includes(agentType)
      ? current.filter(a => a !== agentType)
      : [...current, agentType];
    if (updated.length === 0) return;
    try {
      await apiUpdateWorkspace(editingWorkspace.id, { agents: updated });
      dispatch(fetchWorkspaces());
    } catch {}
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => { setOpen(!open); setEditingWorkspaceId(null); }}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          background: 'rgba(255,255,255,0.02)', padding: '5px 10px',
          borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
          borderLeft: `3px solid ${color}`,
          transition: 'background 0.15s',
          border: '1px solid rgba(255,255,255,0.05)',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
      >
        <Building2 size={13} color={color} />
        <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>{label}</span>
        <ChevronDown size={12} color="#62666d" style={{
          transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }} />
      </div>

      <AnimatePresence>
        {open && !editingWorkspaceId && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="glass-dropdown"
            style={{
              position: 'absolute', top: '100%', left: 0, marginTop: '6px',
              borderRadius: '8px', minWidth: '280px', zIndex: 100, overflow: 'hidden',
              boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            }}
          >
          <div style={{ padding: '4px' }}>
            <div
              onClick={() => { setOpen(false); setShowCreate(true); }}
              style={{
                padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                display: 'flex', alignItems: 'center', gap: '10px',
                color: '#8a8f98', borderRadius: '6px',
                background: 'transparent', transition: 'background 0.12s',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                marginBottom: '2px',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(94,106,210,0.08)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <div style={{
                width: '30px', height: '30px', borderRadius: '6px',
                background: 'rgba(94,106,210,0.12)',
                border: '1px dashed rgba(94,106,210,0.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Plus size={14} color="#7170ff" />
              </div>
              <div style={{ fontWeight: 510, color: '#d0d6e0' }}>New Workspace</div>
            </div>
            {workspaces.map(workspace => {
              const isSelected = selectedWorkspaceId === workspace.id;
              return (
                <div
                  key={workspace.id}
                  style={{
                    padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                    color: isSelected ? '#f7f8f8' : '#d0d6e0',
                    background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                    display: 'flex', alignItems: 'center', gap: '10px',
                    borderRadius: '6px', transition: 'background 0.12s',
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? 'rgba(255,255,255,0.05)' : 'transparent'; }}
                >
                  <div
                    onClick={() => handleSelect(workspace.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px', flex: 1,
                    }}
                  >
                    <div style={{
                      width: '30px', height: '30px', borderRadius: '6px',
                      background: 'rgba(255,255,255,0.04)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <Building2 size={14} color={workspace.color} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 510, fontSize: '13px' }}>{workspace.name}</div>
                      <div style={{ fontSize: '11px', color: '#62666d', marginTop: '1px', fontWeight: 400 }}>{workspace.description}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isSelected && <Check size={14} color="#7170ff" strokeWidth={2.5} />}
                    <div
                      onClick={(e) => { e.stopPropagation(); setEditingWorkspaceId(workspace.id); }}
                      style={{
                        width: '24px', height: '24px', borderRadius: '6px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        opacity: 0.3, transition: 'all 0.15s', cursor: 'pointer',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                      onMouseLeave={e => { e.currentTarget.style.opacity = '0.3'; e.currentTarget.style.background = 'transparent'; }}
                      title="Manage agents"
                    >
                      <Settings size={12} color="#8a8f98" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Agent management panel */}
      <AnimatePresence>
        {open && editingWorkspaceId && editingWorkspace && (
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
          <div style={{
            padding: '10px 14px 8px', borderBottom: '1px solid rgba(255,255,255,0.05)',
            display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            <div
              onClick={() => setEditingWorkspaceId(null)}
              style={{ cursor: 'pointer', opacity: 0.5, fontSize: '12px', transition: 'opacity 0.15s', color: '#8a8f98' }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}
            >
              &larr;
            </div>
            <span style={{ fontSize: '11px', color: '#8a8f98', fontWeight: 510, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Agents — {editingWorkspace.name}
            </span>
          </div>
          <div style={{ padding: '4px' }}>
            {allAgents.map(agent => {
              const isEnabled = (editingWorkspace.agents ?? []).includes(agent.type);
              return (
                <div
                  key={agent.type}
                  onClick={() => handleToggleAgent(agent.type)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                    borderRadius: '6px', transition: 'background 0.12s',
                    color: isEnabled ? '#d0d6e0' : '#62666d',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '6px',
                    background: isEnabled ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.02)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    opacity: isEnabled ? 1 : 0.4,
                  }}>
                    <AgentIcon agent={agent} size={14} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 510 }}>{agent.name}</div>
                    <div style={{ fontSize: '11px', color: '#62666d', marginTop: '1px', fontWeight: 400 }}>{agent.description}</div>
                  </div>
                  <div style={{
                    width: '32px', height: '18px', borderRadius: '9px',
                    background: isEnabled ? 'var(--accent)' : 'rgba(255,255,255,0.08)',
                    padding: '2px', transition: 'background 0.2s',
                    display: 'flex', alignItems: 'center',
                    justifyContent: isEnabled ? 'flex-end' : 'flex-start',
                  }}>
                    <div style={{
                      width: '14px', height: '14px', borderRadius: '50%',
                      background: '#fff', transition: 'all 0.2s',
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
          </motion.div>
        )}
      </AnimatePresence>

      {showCreate && <WorkspaceCreate onClose={() => setShowCreate(false)} />}
    </div>
  );
}
