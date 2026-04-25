'use client';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, FolderOpen } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedProject } from '@/store/projectSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function ProjectDropdown() {
  const dispatch = useAppDispatch();
  const isMobile = useIsMobile();
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selected = projects.find(p => p.id === selectedProjectId);
  const label = selected?.name ?? 'All Projects';
  const color = selected?.color ?? '#8a8f98';

  const handleSelect = (id: string | null) => {
    if (id !== selectedProjectId) {
      dispatch(switchProjectTabs({
        fromProjectId: selectedProjectId, toProjectId: id,
        fromAgencyId: selectedWorkspaceId, toAgencyId: selectedWorkspaceId,
      }));
    }
    dispatch(setSelectedProject(id));
    dispatch(fetchConversations({ projectId: id, agencyId: selectedWorkspaceId }));
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%' }}>
      <div
        data-testid="project-dropdown-trigger"
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          background: 'rgba(255,255,255,0.02)', padding: '5px 10px',
          borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
          transition: 'background 0.15s',
          border: '1px solid rgba(255,255,255,0.05)',
          width: '100%',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
      >
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: color }} />
        <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>{label}</span>
        <ChevronDown size={12} color="#62666d" style={{
          transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }} />
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            data-testid="project-dropdown-menu"
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="glass-dropdown"
            style={{
              position: 'absolute', top: '100%', left: 0, marginTop: '6px',
              borderRadius: '8px', minWidth: isMobile ? '100%' : '200px', width: isMobile ? '100%' : undefined,
              zIndex: 100, overflow: 'hidden',
              boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            }}
          >
          <div style={{ padding: '4px' }}>
            <div
              onClick={() => handleSelect(null)}
              style={{
                padding: '8px 12px', cursor: 'pointer', fontSize: '13px',
                color: !selectedProjectId ? '#f7f8f8' : '#d0d6e0',
                background: !selectedProjectId ? 'rgba(255,255,255,0.05)' : 'transparent',
                display: 'flex', alignItems: 'center', gap: '8px',
                borderRadius: '6px', transition: 'background 0.12s',
                fontWeight: !selectedProjectId ? 510 : 400,
              }}
              onMouseEnter={e => { if (selectedProjectId) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
              onMouseLeave={e => { if (selectedProjectId) e.currentTarget.style.background = 'transparent'; }}
            >
              <FolderOpen size={13} color="#8a8f98" />
              <span>All Projects</span>
              {!selectedProjectId && <Check size={13} color="#7170ff" strokeWidth={2.5} style={{ marginLeft: 'auto' }} />}
            </div>
            {projects.filter(p => p.id).map(p => {
              const isSelected = selectedProjectId === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => handleSelect(p.id)}
                  style={{
                    padding: '8px 12px', cursor: 'pointer', fontSize: '13px',
                    color: isSelected ? '#f7f8f8' : '#d0d6e0',
                    background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    borderRadius: '6px', transition: 'background 0.12s',
                    fontWeight: isSelected ? 510 : 400,
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: p.color, flexShrink: 0 }} />
                  <span>{p.name}</span>
                  {isSelected && <Check size={13} color="#7170ff" strokeWidth={2.5} style={{ marginLeft: 'auto' }} />}
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
