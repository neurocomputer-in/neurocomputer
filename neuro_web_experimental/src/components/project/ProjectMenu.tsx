'use client';
import { useEffect, useRef, useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { Project } from '@/types';
import { useAppDispatch } from '@/store/hooks';
import { deleteProject, updateProject } from '@/store/projectSlice';

interface Props {
  project: Project;
  position: { x: number; y: number };
  onClose: () => void;
}

export default function ProjectMenu({ project, position, onClose }: Props) {
  const dispatch = useAppDispatch();
  const ref = useRef<HTMLDivElement>(null);
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState(project.name);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  const handleRename = () => {
    if (newName.trim() && newName !== project.name && project.id) {
      dispatch(updateProject({ id: project.id, data: { name: newName.trim() } }));
    }
    onClose();
  };

  const isMainProject = typeof project.id === 'string' && project.id.startsWith('main-');

  const handleDelete = () => {
    if (project.id && !isMainProject && confirm(`Delete project "${project.name}"?`)) {
      dispatch(deleteProject(project.id));
    }
    onClose();
  };

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        background: '#191a1b',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        zIndex: 200,
        minWidth: '160px',
        overflow: 'hidden',
        boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
      }}
    >
      {renaming ? (
        <div style={{ padding: '10px 12px' }}>
          <input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleRename();
              if (e.key === 'Escape') onClose();
            }}
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(113,112,255,0.3)',
              borderRadius: '4px',
              padding: '4px 8px',
              color: '#f7f8f8',
              fontSize: '13px',
              outline: 'none',
              fontWeight: 400,
            }}
          />
        </div>
      ) : (
        <div style={{ padding: '4px' }}>
          <div
            onClick={() => setRenaming(true)}
            style={{
              padding: '8px 12px', fontSize: '13px', color: '#d0d6e0', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '8px',
              borderRadius: '4px', transition: 'background 0.12s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <Pencil size={13} color="#8a8f98" />
            Rename
          </div>
          {!isMainProject && (
            <div
              onClick={handleDelete}
              style={{
                padding: '8px 12px', fontSize: '13px', color: '#ef4444', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '8px',
                borderRadius: '4px', transition: 'background 0.12s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.06)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <Trash2 size={13} color="#ef4444" />
              Delete
            </div>
          )}
        </div>
      )}
    </div>
  );
}
