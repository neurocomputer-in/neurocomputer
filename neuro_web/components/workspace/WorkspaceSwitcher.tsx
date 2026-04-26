'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Check, Plus, Pencil } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedWorkspace, createWorkspace, updateWorkspace, fetchWorkspaces } from '@/store/workspaceSlice';
import { setSelectedProject, fetchProjects } from '@/store/projectSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';

const WS_COLORS = ['#8B5CF6','#3b82f6','#14b8a6','#f97316','#ec4899','#f59e0b','#27a644','#6366f1'];

export default function WorkspaceSwitcher({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dispatch = useAppDispatch();
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  if (!open) return null;

  const handleSelect = (id: string) => {
    if (editingId) return;
    dispatch(switchProjectTabs({ fromProjectId: selectedProjectId, toProjectId: null, fromAgencyId: selectedWorkspaceId, toAgencyId: id }));
    dispatch(setSelectedWorkspace(id));
    dispatch(setSelectedProject(null));
    dispatch(fetchProjects(id));
    dispatch(fetchConversations({ projectId: null, agencyId: id }));
    onClose();
  };

  const handleCreate = async () => {
    if (!createName.trim()) return;
    const color = WS_COLORS[workspaces.length % WS_COLORS.length];
    await dispatch(createWorkspace({ name: createName.trim(), color }));
    dispatch(fetchWorkspaces());
    setCreateName(''); setShowCreate(false);
  };

  const handleSaveEdit = async () => {
    if (!editingId || !editName.trim()) { setEditingId(null); return; }
    await dispatch(updateWorkspace({ id: editingId, patch: { name: editName.trim() } }));
    dispatch(fetchWorkspaces());
    setEditingId(null);
  };

  return (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        onClick={e => e.stopPropagation()}
        style={{
          background: 'rgba(18,18,22,0.99)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 16, padding: '20px 20px 16px',
          width: '100%', maxWidth: 400,
          boxShadow: '0 24px 64px rgba(0,0,0,0.75)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#f7f8f8' }}>Switch Workspace</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.4)', padding: 4, borderRadius: 6, display: 'flex' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#fff')} onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.4)')}>
            <X size={16} />
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {workspaces.map(ws => {
            const isSelected = ws.id === selectedWorkspaceId;
            return (
              <div
                key={ws.id}
                onClick={() => handleSelect(ws.id)}
                style={{
                  position: 'relative', padding: '14px 8px 12px',
                  borderRadius: 12, cursor: 'pointer',
                  border: isSelected ? `2px solid ${ws.color}88` : '1px solid rgba(255,255,255,0.07)',
                  background: isSelected ? `${ws.color}14` : 'rgba(255,255,255,0.03)',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7,
                  transition: 'background 0.12s, border 0.12s',
                }}
                onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)'; }}
                onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
              >
                {isSelected && (
                  <div style={{ position: 'absolute', top: 6, right: 6, width: 16, height: 16, borderRadius: '50%', background: ws.color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Check size={9} color="#fff" strokeWidth={3} />
                  </div>
                )}
                <div style={{
                  width: 42, height: 42, borderRadius: 11,
                  background: `linear-gradient(135deg, ${ws.color}ee, ${ws.color}88)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 19, fontWeight: 700, color: '#fff', flexShrink: 0,
                }}>
                  {ws.name[0]?.toUpperCase() || '?'}
                </div>

                {editingId === ws.id ? (
                  <input
                    autoFocus
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleSaveEdit(); if (e.key === 'Escape') setEditingId(null); }}
                    onBlur={handleSaveEdit}
                    onClick={e => e.stopPropagation()}
                    style={{
                      width: '100%', textAlign: 'center', fontSize: 11,
                      background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.25)',
                      borderRadius: 5, padding: '2px 4px', color: '#fff', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                ) : (
                  <span style={{ fontSize: 11, fontWeight: 500, color: '#e0e0e0', textAlign: 'center', lineHeight: 1.25, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ws.name}
                  </span>
                )}

                <button
                  onClick={(e) => { e.stopPropagation(); setEditingId(ws.id); setEditName(ws.name); }}
                  style={{ position: 'absolute', bottom: 5, right: 5, background: 'none', border: 'none', cursor: 'pointer', opacity: 0, padding: 3, borderRadius: 4, color: '#aaa', display: 'flex', transition: 'opacity 0.12s' }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '0')}
                >
                  <Pencil size={9} />
                </button>
              </div>
            );
          })}

          {!showCreate && (
            <div
              onClick={() => setShowCreate(true)}
              style={{
                padding: '14px 8px 12px', borderRadius: 12, cursor: 'pointer',
                border: '1px dashed rgba(255,255,255,0.12)',
                background: 'rgba(255,255,255,0.02)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7,
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
            >
              <div style={{ width: 42, height: 42, borderRadius: 11, border: '1.5px dashed rgba(255,255,255,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Plus size={18} color="rgba(255,255,255,0.3)" />
              </div>
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>New</span>
            </div>
          )}
        </div>

        {showCreate && (
          <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
            <input
              autoFocus
              value={createName}
              onChange={e => setCreateName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') { setShowCreate(false); setCreateName(''); } }}
              placeholder="Workspace name"
              style={{
                flex: 1, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: 8, padding: '8px 12px', color: '#f7f8f8', fontSize: 13, outline: 'none',
              }}
              onFocus={e => (e.currentTarget.style.borderColor = 'rgba(94,106,210,0.6)')}
              onBlur={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)')}
            />
            <button onClick={handleCreate} disabled={!createName.trim()}
              style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: createName.trim() ? '#5e6ad2' : 'rgba(94,106,210,0.25)', color: '#fff', cursor: createName.trim() ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 500 }}>
              Create
            </button>
            <button onClick={() => { setShowCreate(false); setCreateName(''); }}
              style={{ padding: '8px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
              <X size={14} />
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
