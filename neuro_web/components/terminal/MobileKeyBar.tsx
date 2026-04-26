'use client';
import { useState } from 'react';

interface Props { onKey: (seq: string) => void }

const KEYS: { label: string; seq: string }[] = [
  { label: 'Esc', seq: '\x1b' },
  { label: 'Tab', seq: '\t' },
  { label: '↑',   seq: '\x1b[A' },
  { label: '↓',   seq: '\x1b[B' },
  { label: '←',   seq: '\x1b[D' },
  { label: '→',   seq: '\x1b[C' },
];

export default function MobileKeyBar({ onKey }: Props) {
  const [ctrl, setCtrl] = useState(false);

  const press = (seq: string) => {
    // Sticky Ctrl: if active, combine with the next alpha key.
    if (ctrl && seq.length === 1 && /[a-zA-Z]/.test(seq)) {
      onKey(String.fromCharCode(seq.charCodeAt(0) & 0x1f));
      setCtrl(false);
      return;
    }
    onKey(seq);
    if (ctrl) setCtrl(false);
  };

  return (
    <div style={{
      display: 'flex', gap: 4, padding: 4,
      borderTop: '1px solid rgba(255,255,255,0.05)',
      overflowX: 'auto', background: '#0f1011',
    }}>
      {/* onMouseDown preventDefault keeps the textarea focused on iOS —
          tapping a button without this causes iOS to blur the input and
          dismiss the keyboard before onClick fires. */}
      <button onMouseDown={e => e.preventDefault()} onClick={() => setCtrl(c => !c)} style={btn(ctrl)}>Ctrl</button>
      {KEYS.map(k => (
        <button key={k.label} onMouseDown={e => e.preventDefault()} onClick={() => press(k.seq)} style={btn(false)}>
          {k.label}
        </button>
      ))}
      <button onMouseDown={e => e.preventDefault()} onClick={() => { onKey('\x03'); setCtrl(false); }} style={btn(false)}>Ctrl+C</button>
      <button onMouseDown={e => e.preventDefault()} onClick={() => { onKey('\x04'); setCtrl(false); }} style={btn(false)}>Ctrl+D</button>
    </div>
  );
}

function btn(active: boolean): React.CSSProperties {
  return {
    padding: '6px 10px', borderRadius: 4,
    background: active ? 'rgba(94,106,210,0.25)' : 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: active ? '#c4b5fd' : '#d0d6e0',
    fontSize: 12, minWidth: 38, flexShrink: 0, fontFamily: 'inherit',
    cursor: 'pointer',
  };
}
