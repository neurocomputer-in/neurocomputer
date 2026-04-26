'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, FolderOpen, Plus, Pencil, Trash2, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedProject, fetchProjects, createProject, updateProject, deleteProject } from '@/store/projectSlice';
import { fetchConversations, switchProjectTabs } from '@/store/conversationSlice';
import { Project } from '@/types';

const COLORS = ['#8B5CF6','#3b82f6','#14b8a6','#f97316','#ec4899','#f59e0b','#27a644','#6366f1'];

// Shared project form used in both desktop panel and mobile sheet
export function ProjectForm({ project, onSave, onDelete, onCancel, autoFocus = true }: {
  project?: Pick<Project, 'id' | 'name' | 'description' | 'color'> | null;
  onSave: (data: { name: string; description: string; color: string }) => Promise<void>;
  onDelete?: () => Promise<void>;
  onCancel: () => void;
  autoFocus?: boolean;
}) {
  const [name, setName] = useState(project?.name ?? '');
  const [description, setDescription] = useState(project?.description ?? '');
  const [color, setColor] = useState(project?.color ?? COLORS[0]);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (autoFocus) inputRef.current?.focus(); }, [autoFocus]);

  const handleSave = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try { await onSave({ name: name.trim(), description, color }); }
    finally { setSaving(false); }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14 }}>
        <button onClick={onCancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.4)', padding: '2px 0', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
          onMouseEnter={e => (e.currentTarget.style.color = '#fff')} onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.4)')}>
          ← Back
        </button>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#f7f8f8' }}>{project ? 'Edit Project' : 'New Project'}</span>
      </div>

      <input
        ref={inputRef}
        value={name}
        onChange={e => setName(e.target.value)}
        placeholder="Project name"
        onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') onCancel(); }}
        style={{
          width: '100%', boxSizing: 'border-box', marginBottom: 10,
          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 8, padding: '8px 12px', color: '#f7f8f8', fontSize: 13, outline: 'none',
        }}
        onFocus={e => (e.currentTarget.style.borderColor = 'rgba(94,106,210,0.55)')}
        onBlur={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
      />

      <textarea
        value={description}
        onChange={e => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        style={{
          width: '100%', boxSizing: 'border-box', resize: 'none', marginBottom: 12,
          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 8, padding: '8px 12px', color: '#f7f8f8', fontSize: 12,
          outline: 'none', fontFamily: 'inherit', lineHeight: 1.45,
        }}
        onFocus={e => (e.currentTarget.style.borderColor = 'rgba(94,106,210,0.55)')}
        onBlur={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
      />

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: '#62666d', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Color</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {COLORS.map(c => (
            <div key={c} onClick={() => setColor(c)} style={{
              width: 20, height: 20, borderRadius: '50%', background: c, cursor: 'pointer',
              border: color === c ? '2px solid #fff' : '2px solid transparent',
              outline: color === c ? `2px solid ${c}` : 'none', outlineOffset: 2,
              transition: 'outline 0.1s, border 0.1s',
            }} />
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {onDelete && !confirmDelete && (
          <button onClick={() => setConfirmDelete(true)}
            style={{ background: 'rgba(255,80,60,0.1)', border: 'none', borderRadius: 7, padding: '6px 8px', cursor: 'pointer', color: '#ff5f57', display: 'flex', alignItems: 'center' }}>
            <Trash2 size={13} />
          </button>
        )}
        {confirmDelete && (
          <>
            <span style={{ fontSize: 12, color: '#ff5f57', marginRight: 2 }}>Delete?</span>
            <button onClick={async () => { if (onDelete) await onDelete(); setConfirmDelete(false); }}
              style={{ padding: '5px 12px', borderRadius: 7, border: 'none', background: '#ff5f57', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}>Yes</button>
            <button onClick={() => setConfirmDelete(false)}
              style={{ padding: '5px 10px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 12 }}>No</button>
          </>
        )}
        <div style={{ flex: 1 }} />
        <button onClick={onCancel}
          style={{ padding: '6px 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 12 }}>
          Cancel
        </button>
        <button onClick={handleSave} disabled={!name.trim() || saving}
          style={{ padding: '6px 14px', borderRadius: 7, border: 'none', background: name.trim() ? '#5e6ad2' : 'rgba(94,106,210,0.25)', color: '#fff', cursor: name.trim() ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: 500 }}>
          {saving ? '…' : 'Save'}
        </button>
      </div>
    </div>
  );
}

// Reusable list + form — used by desktop panel AND mobile sheet
export function ProjectListPanel({ onClose }: { onClose?: () => void }) {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const [view, setView] = useState<'list' | 'create' | 'edit'>('list');
  const [editingProject, setEditingProject] = useState<Project | null>(null);

  const handleSelect = (id: string | null) => {
    dispatch(switchProjectTabs({ fromProjectId: selectedProjectId, toProjectId: id, fromAgencyId: selectedWorkspaceId, toAgencyId: selectedWorkspaceId }));
    dispatch(setSelectedProject(id));
    dispatch(fetchConversations({ projectId: id, agencyId: selectedWorkspaceId }));
    onClose?.();
  };

  const handleCreate = async (data: { name: string; description: string; color: string }) => {
    await dispatch(createProject({ ...data, workspaceId: selectedWorkspaceId }));
    dispatch(fetchProjects(selectedWorkspaceId));
    setView('list');
  };

  const handleEdit = async (data: { name: string; description: string; color: string }) => {
    if (!editingProject?.id) return;
    await dispatch(updateProject({ id: editingProject.id, data }));
    setView('list'); setEditingProject(null);
  };

  const handleDelete = async () => {
    if (!editingProject?.id) return;
    await dispatch(deleteProject(editingProject.id));
    setView('list'); setEditingProject(null);
    onClose?.();
  };

  if (view === 'create') {
    return <ProjectForm onSave={handleCreate} onCancel={() => setView('list')} />;
  }
  if (view === 'edit' && editingProject) {
    return (
      <ProjectForm
        project={editingProject}
        onSave={handleEdit}
        onDelete={handleDelete}
        onCancel={() => { setView('list'); setEditingProject(null); }}
      />
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#62666d', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Projects</span>
        <button onClick={() => setView('create')}
          style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(94,106,210,0.12)', border: 'none', borderRadius: 6, padding: '4px 9px', cursor: 'pointer', color: '#8a8aff', fontSize: 12, fontWeight: 500 }}>
          <Plus size={11} /> New
        </button>
      </div>

      {/* All Projects */}
      <div onClick={() => handleSelect(null)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 6px', borderRadius: 8, cursor: 'pointer', background: !selectedProjectId ? 'rgba(255,255,255,0.06)' : 'transparent', transition: 'background 0.12s' }}
        onMouseEnter={e => { if (selectedProjectId) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; }}
        onMouseLeave={e => { if (selectedProjectId) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
        <FolderOpen size={13} color="#62666d" />
        <span style={{ flex: 1, fontSize: 13, color: !selectedProjectId ? '#f7f8f8' : '#b0b4bc', fontWeight: !selectedProjectId ? 500 : 400 }}>All Projects</span>
        {!selectedProjectId && <Check size={12} color="#7170ff" />}
      </div>

      {projects.filter(p => p.id).map(p => {
        const isSelected = selectedProjectId === p.id;
        return (
          <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 6px', borderRadius: 8, background: isSelected ? 'rgba(255,255,255,0.06)' : 'transparent', transition: 'background 0.12s' }}
            onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; }}
            onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
            <div onClick={() => handleSelect(p.id)} style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0, cursor: 'pointer' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: isSelected ? '#f7f8f8' : '#b0b4bc', fontWeight: isSelected ? 500 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</div>
                {p.description && (
                  <div style={{ fontSize: 11, color: '#5a5e66', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 1 }}>{p.description}</div>
                )}
              </div>
            </div>
            {isSelected && <Check size={12} color="#7170ff" style={{ flexShrink: 0 }} />}
            <button onClick={(e) => { e.stopPropagation(); setEditingProject(p); setView('edit'); }}
              style={{ flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer', opacity: 0, padding: 4, borderRadius: 4, color: '#aaa', display: 'flex', transition: 'opacity 0.12s' }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0')}>
              <Pencil size={11} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// Desktop-only dropdown panel (mobile uses MobileControlSheet)
export default function ProjectPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: -6, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -6, scale: 0.97 }}
          transition={{ duration: 0.14, ease: 'easeOut' }}
          style={{
            position: 'absolute', top: '100%', left: 0, marginTop: 4,
            minWidth: 280, maxWidth: 320,
            background: 'rgba(16,16,20,0.99)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10,
            boxShadow: '0 14px 48px rgba(0,0,0,0.7)',
            zIndex: 500,
            maxHeight: 480, overflowY: 'auto',
            padding: 12,
          }}
        >
          <ProjectListPanel onClose={onClose} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
