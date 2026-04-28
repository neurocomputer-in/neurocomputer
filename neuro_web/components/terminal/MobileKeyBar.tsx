'use client';
import { useState } from 'react';
import { CornerDownLeft, ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Delete } from 'lucide-react';

interface Props { onKey: (seq: string) => void }

/**
 * Hotkey toolbar that sits between the xterm canvas and the input bar on
 * mobile. Every key here writes its raw escape sequence directly to the
 * PTY (bypasses the textarea/submit buffer), so it works inside any TUI —
 * Claude CLI, opencode, vim, less, etc. — even though the input bar
 * normally buffers typing.
 *
 * Enter sends CR (\r) because that's what real keyboards send and what
 * raw-mode TUIs read as "submit". \n looks identical in the shell but is
 * just a newline-in-input for raw-mode apps.
 */
const KEYS: { label: React.ReactNode; seq: string; title: string; minW?: number }[] = [
  { label: 'Esc',                 seq: '\x1b',     title: 'Escape' },
  { label: 'Tab',                 seq: '\t',       title: 'Tab' },
  { label: <CornerDownLeft size={14} />, seq: '\r', title: 'Enter (submit to TUI)', minW: 44 },
  { label: <Delete size={14} />,  seq: '\x7f',     title: 'Backspace' },
  { label: <ArrowUp size={13} />,    seq: '\x1b[A', title: 'Up' },
  { label: <ArrowDown size={13} />,  seq: '\x1b[B', title: 'Down' },
  { label: <ArrowLeft size={13} />,  seq: '\x1b[D', title: 'Left' },
  { label: <ArrowRight size={13} />, seq: '\x1b[C', title: 'Right' },
];

export default function MobileKeyBar({ onKey }: Props) {
  const [ctrl, setCtrl] = useState(false);

  const press = (seq: string) => {
    // Sticky Ctrl: combine with the next alpha key.
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
      scrollbarWidth: 'none',
    }}>
      <button onPointerDown={e => e.preventDefault()} onClick={() => setCtrl(c => !c)}
              style={btn(ctrl)} title="Ctrl modifier (next key)">Ctrl</button>
      {KEYS.map((k, i) => (
        <button key={i}
                onPointerDown={e => e.preventDefault()}
                onClick={() => press(k.seq)}
                style={{ ...btn(false), minWidth: k.minW ?? 38 }}
                title={k.title}>
          {k.label}
        </button>
      ))}
      <button onPointerDown={e => e.preventDefault()}
              onClick={() => { onKey('\x03'); setCtrl(false); }}
              style={btn(false)} title="Send Ctrl+C (interrupt)">^C</button>
      <button onPointerDown={e => e.preventDefault()}
              onClick={() => { onKey('\x04'); setCtrl(false); }}
              style={btn(false)} title="Send Ctrl+D (EOF / exit)">^D</button>
    </div>
  );
}

function btn(active: boolean): React.CSSProperties {
  return {
    padding: '6px 10px', borderRadius: 6,
    background: active ? 'rgba(94,106,210,0.25)' : 'rgba(255,255,255,0.04)',
    border: '1px solid ' + (active ? 'rgba(94,106,210,0.5)' : 'rgba(255,255,255,0.08)'),
    color: active ? '#c4b5fd' : '#d0d6e0',
    fontSize: 12, minWidth: 38, flexShrink: 0, fontFamily: 'inherit',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer',
  };
}
