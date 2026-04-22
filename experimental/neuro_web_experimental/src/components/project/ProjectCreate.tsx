'use client';
import { useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { createProject } from '@/store/projectSlice';
import { setShowProjectCreate } from '@/store/uiSlice';

const PRESET_COLORS = [
  'var(--accent)', '#f59e0b', '#27a644', '#ef4444',
  '#3b82f6', '#ec4899', '#14b8a6', '#f97316',
];

export default function ProjectCreate() {
  const dispatch = useAppDispatch();
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const [name, setName] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0]);

  const handleCreate = () => {
    if (!name.trim()) return;
    dispatch(createProject({ name: name.trim(), color, workspaceId: selectedWorkspaceId }));
    dispatch(setShowProjectCreate(false));
  };

  const close = () => dispatch(setShowProjectCreate(false));

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 300,
      }}
      onClick={close}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#191a1b',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px',
          padding: '24px',
          width: '320px',
          boxShadow: '0 8px 30px rgba(0,0,0,0.6)',
        }}
      >
        <h3 style={{ color: '#f7f8f8', fontSize: '16px', marginBottom: '16px', fontWeight: 510 }}>
          New Project
        </h3>
        <input
          autoFocus
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') handleCreate();
            if (e.key === 'Escape') close();
          }}
          placeholder="Project name"
          style={{
            width: '100%',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px',
            padding: '8px 12px',
            color: '#f7f8f8',
            fontSize: '14px',
            outline: 'none',
            marginBottom: '16px',
            boxSizing: 'border-box',
            fontWeight: 400,
          }}
        />
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '11px', color: '#62666d', marginBottom: '8px', fontWeight: 510, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Color</div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {PRESET_COLORS.map(c => (
              <div
                key={c}
                onClick={() => setColor(c)}
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: c,
                  cursor: 'pointer',
                  border: color === c ? '2px solid #fff' : '2px solid transparent',
                  outline: color === c ? `2px solid ${c}` : 'none',
                  outlineOffset: '2px',
                }}
              />
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            onClick={close}
            style={{
              padding: '7px 16px', fontSize: '13px', borderRadius: '6px',
              background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
              color: '#8a8f98', cursor: 'pointer', fontWeight: 510,
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim()}
            style={{
              padding: '7px 16px', fontSize: '13px', borderRadius: '6px',
              background: name.trim() ? 'var(--accent)' : 'rgba(94,106,210,0.3)',
              border: 'none', color: name.trim() ? '#fff' : '#62666d',
              cursor: name.trim() ? 'pointer' : 'not-allowed',
              fontWeight: 510,
            }}
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
