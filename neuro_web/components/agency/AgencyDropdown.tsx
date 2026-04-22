// @ts-nocheck — deprecated, replaced by WorkspaceDropdown
'use client';
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Building2, Settings } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedAgency, fetchAgencies } from '@/store/agencySlice';
import { setAgentFilter } from '@/store/agentSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';
import { fetchProjects, setSelectedProject } from '@/store/projectSlice';
import { AGENT_LIST, AgentType } from '@/types';
import AgentIcon from '@/components/agent/AgentIcon';
import { apiUpdateAgency } from '@/services/api';

export default function AgencyDropdown() {
  const dispatch = useAppDispatch();
  const agencies = useAppSelector(s => s.agency.agencies);
  const selectedAgencyId = useAppSelector(s => s.agency.selectedAgencyId);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const [open, setOpen] = useState(false);
  const [editingAgencyId, setEditingAgencyId] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setEditingAgencyId(null);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selected = agencies.find(a => a.id === selectedAgencyId);
  const label = selected?.name ?? 'All';
  const color = selected?.color ?? '#888';

  const handleSelect = (agencyId: string | null) => {
    if (agencyId === selectedAgencyId) { setOpen(false); return; }
    dispatch(switchProjectTabs({
      fromProjectId: selectedProjectId, toProjectId: null,
      fromAgencyId: selectedAgencyId, toAgencyId: agencyId,
    }));
    dispatch(setSelectedAgency(agencyId));

    const agency = agencies.find(a => a.id === agencyId);
    if (agency) {
      // Reset agent filter to "All" when switching agencies
      dispatch(setAgentFilter(AgentType.ALL));
    }

    dispatch(setSelectedProject(null));
    dispatch(fetchProjects(agencyId));
    dispatch(fetchConversations({ projectId: null, agencyId }));
    setOpen(false);
  };

  const editingAgency = editingAgencyId ? agencies.find(a => a.id === editingAgencyId) : null;
  const allAgents = AGENT_LIST.filter(a => a.type !== AgentType.ALL);

  const handleToggleAgent = async (agentType: string) => {
    if (!editingAgency) return;
    const current = editingAgency.agents ?? [];
    const updated = current.includes(agentType)
      ? current.filter(a => a !== agentType)
      : [...current, agentType];
    // Don't allow empty — keep at least one agent
    if (updated.length === 0) return;
    try {
      await apiUpdateAgency(editingAgency.id, { agents: updated });
      dispatch(fetchAgencies());
    } catch {}
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => { setOpen(!open); setEditingAgencyId(null); }}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          background: 'rgba(255,255,255,0.05)', padding: '6px 12px',
          borderRadius: '8px', cursor: 'pointer', userSelect: 'none',
          borderLeft: `3px solid ${color}`,
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
      >
        <Building2 size={14} color={color} />
        <span style={{ fontSize: '12px', color: '#e0e0e0', fontWeight: 500 }}>{label}</span>
        <ChevronDown size={13} color="#666" style={{
          transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }} />
      </div>

      {open && !editingAgencyId && (
        <div
          style={{
            position: 'absolute', top: '100%', left: 0, marginTop: '6px',
            background: '#16162a', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px', minWidth: '280px', zIndex: 100, overflow: 'hidden',
            boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
          }}
        >
          <div style={{ padding: '6px' }}>
            {agencies.map(agency => {
              const isSelected = selectedAgencyId === agency.id;
              return (
                <div
                  key={agency.id}
                  style={{
                    padding: '9px 12px', cursor: 'pointer', fontSize: '13px',
                    color: isSelected ? agency.color : '#ddd',
                    background: isSelected ? `${agency.color}12` : 'transparent',
                    display: 'flex', alignItems: 'center', gap: '10px',
                    borderRadius: '7px', transition: 'background 0.12s',
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? `${agency.color}12` : 'transparent'; }}
                >
                  <div
                    onClick={() => handleSelect(agency.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px', flex: 1,
                    }}
                  >
                    <div style={{
                      width: '32px', height: '32px', borderRadius: '8px',
                      background: `${agency.color}15`, borderLeft: `3px solid ${agency.color}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <Building2 size={14} color={agency.color} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, fontSize: '13px' }}>{agency.name}</div>
                      <div style={{ fontSize: '10px', color: '#555', marginTop: '1px' }}>{agency.description}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isSelected && <Check size={14} color={agency.color} strokeWidth={2.5} />}
                    <div
                      onClick={(e) => { e.stopPropagation(); setEditingAgencyId(agency.id); }}
                      style={{
                        width: '24px', height: '24px', borderRadius: '6px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        opacity: 0.3, transition: 'all 0.15s', cursor: 'pointer',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
                      onMouseLeave={e => { e.currentTarget.style.opacity = '0.3'; e.currentTarget.style.background = 'transparent'; }}
                      title="Manage agents"
                    >
                      <Settings size={12} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Agent management panel */}
      {open && editingAgencyId && editingAgency && (
        <div
          style={{
            position: 'absolute', top: '100%', left: 0, marginTop: '6px',
            background: '#16162a', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px', minWidth: '260px', zIndex: 100, overflow: 'hidden',
            boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
          }}
        >
          <div style={{
            padding: '10px 14px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', gap: '8px',
          }}>
            <div
              onClick={() => setEditingAgencyId(null)}
              style={{ cursor: 'pointer', opacity: 0.5, fontSize: '12px', transition: 'opacity 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}
            >
              &larr;
            </div>
            <span style={{ fontSize: '11px', color: '#888', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Agents — {editingAgency.name}
            </span>
          </div>
          <div style={{ padding: '6px' }}>
            {allAgents.map(agent => {
              const isEnabled = (editingAgency.agents ?? []).includes(agent.type);
              return (
                <div
                  key={agent.type}
                  onClick={() => handleToggleAgent(agent.type)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '8px 10px', cursor: 'pointer', fontSize: '12px',
                    borderRadius: '7px', transition: 'background 0.12s',
                    color: isEnabled ? '#ddd' : '#555',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '7px',
                    background: isEnabled ? `${agent.color}15` : 'rgba(255,255,255,0.03)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    opacity: isEnabled ? 1 : 0.4,
                  }}>
                    <AgentIcon agent={agent} size={14} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{agent.name}</div>
                    <div style={{ fontSize: '10px', color: '#555', marginTop: '1px' }}>{agent.description}</div>
                  </div>
                  <div style={{
                    width: '32px', height: '18px', borderRadius: '9px',
                    background: isEnabled ? '#8B5CF6' : 'rgba(255,255,255,0.1)',
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
        </div>
      )}
    </div>
  );
}
