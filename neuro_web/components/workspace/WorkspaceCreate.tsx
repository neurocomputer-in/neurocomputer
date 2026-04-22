'use client';
import { useState } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { createWorkspace } from '@/store/workspaceSlice';
import { THEME_LIST, ThemeId, DEFAULT_THEME } from '@/theme/presets';

const EMOJI_CHOICES = ['🧠', '💼', '🦀', '🧪', '🎨', '📚', '⚙️', '🚀', '🌿', '🔮', '🛠️', '🤖'];
// Concrete hex values — users pick a literal colour, not a var.
const COLOR_CHOICES = ['#8B5CF6', '#14B8A6', '#F97316', '#22C55E', '#F59E0B', '#5e6ad2', '#EC4899', '#06B6D4'];

interface Props {
  onClose: () => void;
}

export default function WorkspaceCreate({ onClose }: Props) {
  const dispatch = useAppDispatch();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [emoji, setEmoji] = useState(EMOJI_CHOICES[0]);
  const [color, setColor] = useState(COLOR_CHOICES[0]);
  const [themeId, setThemeId] = useState<ThemeId>(DEFAULT_THEME);
  const [saving, setSaving] = useState(false);

  const canSave = name.trim().length > 0 && !saving;

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      await dispatch(createWorkspace({
        name: name.trim(),
        description: description.trim(),
        emoji,
        color,
        theme: themeId,
        agents: ['neuro'],
        defaultAgent: 'neuro',
      })).unwrap();
      onClose();
    } catch (e) {
      console.error('Failed to create workspace', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 500,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '520px', maxHeight: '85vh', overflow: 'auto',
          background: '#0f1011', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px', padding: '22px',
          boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
        }}
      >
        <h2 style={{
          fontSize: '18px', fontWeight: 590, color: '#f7f8f8',
          margin: 0, marginBottom: '4px', letterSpacing: '-0.2px',
        }}>New Workspace</h2>
        <p style={{ fontSize: '12px', color: '#8a8f98', margin: 0, marginBottom: '18px' }}>
          Groups projects + agents with a shared theme.
        </p>

        <Field label="Name">
          <input
            autoFocus
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Research"
            style={input}
            onKeyDown={e => { if (e.key === 'Enter' && canSave) handleSave(); }}
          />
        </Field>

        <Field label="Description (optional)">
          <input
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Short description"
            style={input}
          />
        </Field>

        <Field label="Emoji">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {EMOJI_CHOICES.map(e => (
              <button
                key={e}
                onClick={() => setEmoji(e)}
                style={{
                  width: '32px', height: '32px', borderRadius: '6px',
                  background: emoji === e ? 'rgba(94,106,210,0.18)' : 'rgba(255,255,255,0.03)',
                  border: '1px solid ' + (emoji === e ? 'rgba(94,106,210,0.4)' : 'rgba(255,255,255,0.08)'),
                  fontSize: '16px', cursor: 'pointer',
                }}
              >{e}</button>
            ))}
          </div>
        </Field>

        <Field label="Accent color">
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {COLOR_CHOICES.map(c => (
              <button
                key={c}
                onClick={() => setColor(c)}
                aria-label={c}
                style={{
                  width: '28px', height: '28px', borderRadius: '50%',
                  background: c, cursor: 'pointer',
                  border: color === c ? '2px solid #fff' : '2px solid transparent',
                  outline: color === c ? '1px solid rgba(255,255,255,0.2)' : 'none',
                }}
              />
            ))}
          </div>
        </Field>

        <Field label="Theme">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            {THEME_LIST.map(t => {
              const active = t.id === themeId;
              return (
                <button
                  key={t.id}
                  onClick={() => setThemeId(t.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '10px 12px', borderRadius: '8px',
                    background: active ? 'rgba(94,106,210,0.12)' : 'rgba(255,255,255,0.02)',
                    border: '1px solid ' + (active ? 'rgba(94,106,210,0.3)' : 'rgba(255,255,255,0.06)'),
                    cursor: 'pointer', textAlign: 'left', color: '#d0d6e0',
                  }}
                >
                  <span style={{
                    width: '14px', height: '14px', borderRadius: '50%',
                    background: t.swatch, flexShrink: 0,
                    border: '1px solid rgba(255,255,255,0.15)',
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '12px', fontWeight: 510 }}>{t.label}</div>
                    <div style={{ fontSize: '10px', color: '#62666d', marginTop: '2px',
                                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </Field>

        <div style={{ display: 'flex', gap: '8px', marginTop: '18px', justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={btn}>Cancel</button>
          <button
            onClick={handleSave}
            disabled={!canSave}
            style={{
              ...btn,
              background: canSave ? 'var(--accent)' : 'rgba(94,106,210,0.3)',
              color: '#fff', fontWeight: 510,
              cursor: canSave ? 'pointer' : 'not-allowed',
            }}
          >{saving ? 'Creating...' : 'Create'}</button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{
        fontSize: '11px', color: '#8a8f98', textTransform: 'uppercase',
        letterSpacing: '0.5px', fontWeight: 510, marginBottom: '6px',
      }}>{label}</div>
      {children}
    </div>
  );
}

const input: React.CSSProperties = {
  width: '100%',
  background: 'rgba(255,255,255,0.02)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '6px', padding: '8px 10px',
  color: '#f7f8f8', fontSize: '13px', outline: 'none',
};

const btn: React.CSSProperties = {
  padding: '7px 14px', borderRadius: '6px',
  background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
  color: '#d0d6e0', fontSize: '13px', cursor: 'pointer',
  fontFamily: 'inherit',
};
