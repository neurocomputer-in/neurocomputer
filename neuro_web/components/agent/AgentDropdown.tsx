'use client';
import { useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setAgentFilter } from '@/store/agentSlice';
import { setShowAgentDropdown } from '@/store/uiSlice';
import { AgentInfo, AGENT_LIST, AgentType } from '@/types';
import AgentIcon from './AgentIcon';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function AgentDropdown() {
  const dispatch = useAppDispatch();
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const showDropdown = useAppSelector(s => s.ui.showAgentDropdown);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const isMobile = useIsMobile();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        dispatch(setShowAgentDropdown(false));
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [dispatch]);

  const selectedWorkspace = workspaces.find(a => a.id === selectedWorkspaceId);
  const allowedAgentTypes = selectedWorkspace?.agents ?? [];

  const options = AGENT_LIST.filter(a => {
    if (a.type === AgentType.ALL) return true;
    if (allowedAgentTypes.length === 0) return true;
    return allowedAgentTypes.includes(a.type);
  });

  const currentAgent = AGENT_LIST.find(a => a.type === agentFilter) ?? AGENT_LIST[0];

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        data-testid="agent-dropdown-trigger"
        onClick={() => dispatch(setShowAgentDropdown(!showDropdown))}
        style={{
          display: 'flex', alignItems: 'center', gap: isMobile ? '4px' : '8px',
          background: 'rgba(255,255,255,0.02)',
          padding: isMobile ? '6px' : '5px 10px',
          borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
          transition: 'background 0.15s',
          border: '1px solid rgba(255,255,255,0.05)',
          touchAction: isMobile ? 'manipulation' : undefined,
          WebkitTapHighlightColor: isMobile ? 'transparent' : undefined,
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
      >
        <AgentIcon agent={currentAgent} size={isMobile ? 15 : 14} />
        {!isMobile && <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>{currentAgent.name}</span>}
        <ChevronDown size={isMobile ? 10 : 12} color="#62666d" style={{
          transition: 'transform 0.2s',
          transform: showDropdown ? 'rotate(180deg)' : 'rotate(0deg)',
        }} />
      </div>

      {typeof window !== 'undefined' && isMobile ? createPortal(
        <AnimatePresence>
          {showDropdown && (
            <>
              <motion.div
                key="agent-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => dispatch(setShowAgentDropdown(false))}
                style={{ position: 'fixed', inset: 0, zIndex: 9996 }}
              />
              <motion.div
                data-testid="agent-dropdown-menu"
                key="agent-menu"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                style={{
                  position: 'fixed', top: '48px', left: '8px',
                  borderRadius: '12px', minWidth: '220px',
                  maxWidth: 'calc(100vw - 16px)',
                  background: '#1a1b1d',
                  border: '1px solid rgba(255,255,255,0.12)',
                  boxShadow: '0 16px 48px rgba(0,0,0,0.8)',
                  overflow: 'hidden', zIndex: 9997,
                }}
              >
                <div style={{ padding: '4px' }}>
                  {options.map((agent: AgentInfo) => {
                    const isSelected = agentFilter === agent.type;
                    return (
                      <div
                        key={agent.type}
                        data-testid={`agent-option-${agent.type}`}
                        onClick={() => {
                          dispatch(setAgentFilter(agent.type));
                          dispatch(setShowAgentDropdown(false));
                        }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '10px',
                          padding: '12px 14px', cursor: 'pointer', fontSize: '15px',
                          color: isSelected ? '#f7f8f8' : '#d0d6e0',
                          background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                          borderRadius: '8px', transition: 'background 0.12s',
                          touchAction: 'manipulation',
                          WebkitTapHighlightColor: 'transparent',
                        }}
                      >
                        <div style={{
                          width: '30px', height: '30px', borderRadius: '6px',
                          background: 'rgba(255,255,255,0.04)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                          <AgentIcon agent={agent} size={15} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 510, fontSize: '14px' }}>{agent.name}</div>
                          {!isMobile && <div style={{ fontSize: '11px', color: '#62666d', marginTop: '1px', fontWeight: 400 }}>{agent.description}</div>}
                        </div>
                        {isSelected && <Check size={14} color="#7170ff" strokeWidth={2.5} />}
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>,
        document.body
      ) : (
        <AnimatePresence>
          {showDropdown && (
            <motion.div
              data-testid="agent-dropdown-menu"
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="glass-dropdown"
              style={{
                position: 'absolute', top: '100%', left: 0, marginTop: '6px',
                borderRadius: '8px', minWidth: '220px', zIndex: 100, overflow: 'hidden',
                boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
              }}
            >
            <div style={{ padding: '4px' }}>
              {options.map((agent: AgentInfo) => {
                const isSelected = agentFilter === agent.type;
                return (
                  <div
                    key={agent.type}
                    data-testid={`agent-option-${agent.type}`}
                    onClick={() => {
                      dispatch(setAgentFilter(agent.type));
                      dispatch(setShowAgentDropdown(false));
                    }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                      color: isSelected ? '#f7f8f8' : '#d0d6e0',
                      background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                      borderRadius: '6px', transition: 'background 0.12s',
                    }}
                    onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                    onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <div style={{
                      width: '30px', height: '30px', borderRadius: '6px',
                      background: 'rgba(255,255,255,0.04)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <AgentIcon agent={agent} size={15} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 510, fontSize: '13px' }}>{agent.name}</div>
                      <div style={{ fontSize: '11px', color: '#62666d', marginTop: '1px', fontWeight: 400 }}>{agent.description}</div>
                    </div>
                    {isSelected && <Check size={14} color="#7170ff" strokeWidth={2.5} />}
                  </div>
                );
              })}
            </div>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  );
}
