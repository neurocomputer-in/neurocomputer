'use client';
import { useEffect, useRef, useState } from 'react';
import { Palette } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setTheme } from '@/store/uiSlice';

const THEMES = [
  { id: 'neural-network', label: 'Neural Network', color: '#5e6ad2' },
  { id: 'deep-space', label: 'Deep Space', color: '#4a6aaa' },
  { id: 'digital-rain', label: 'Digital Rain', color: '#27a644' },
  { id: 'minimal-dark', label: 'Minimal Dark', color: '#62666d' },
] as const;

export default function ThemeSelector() {
  const dispatch = useAppDispatch();
  const currentTheme = useAppSelector(s => s.ui.theme);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem('neuro_theme');
    if (saved && saved !== currentTheme) {
      dispatch(setTheme(saved as any));
    }
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const current = THEMES.find(t => t.id === currentTheme) ?? THEMES[0];

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '6px', padding: '5px 10px', cursor: 'pointer',
          fontSize: '12px', color: '#8a8f98', transition: 'all 0.15s',
          fontFamily: 'inherit', fontFeatureSettings: '"cv01", "ss03"',
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)')}
        title="Change 3D theme"
      >
        <Palette size={13} color={current.color} />
        <span style={{ fontWeight: 510 }}>{current.label}</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: '6px',
          background: '#191a1b', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '8px', minWidth: '200px', zIndex: 1000,
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)', padding: '4px',
          overflow: 'hidden',
        }}>
          {THEMES.map(theme => {
            const isSelected = currentTheme === theme.id;
            return (
              <div
                key={theme.id}
                onClick={() => { dispatch(setTheme(theme.id as any)); setOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '8px 12px', cursor: 'pointer', fontSize: '13px',
                  color: isSelected ? '#f7f8f8' : '#d0d6e0',
                  background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                  borderRadius: '6px', transition: 'background 0.12s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? 'rgba(255,255,255,0.05)' : 'transparent'; }}
              >
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: theme.color }} />
                <span style={{ fontWeight: isSelected ? 510 : 400 }}>{theme.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
