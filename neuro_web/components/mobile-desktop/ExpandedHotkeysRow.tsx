'use client';
import { useDesktopRoom } from './DesktopRoomContext';

interface Key {
  label: string;
  key: string;     // matches LiveKit `{type:"key",key:"..."}` payload
}

const KEYS: Key[] = [
  { label: 'Esc',   key: 'Escape' },
  { label: 'Tab',   key: 'Tab' },
  { label: '↵',     key: 'Return' },
  { label: '⌫',     key: 'BackSpace' },
  { label: '⌦',     key: 'Delete' },
  { label: 'Undo',  key: 'ctrl+z' },
  { label: 'Redo',  key: 'ctrl+shift+z' },
  { label: 'Copy',  key: 'ctrl+c' },
  { label: 'Paste', key: 'ctrl+v' },
  { label: 'PgUp',  key: 'Page_Up' },
  { label: 'PgDn',  key: 'Page_Down' },
  { label: 'Home',  key: 'Home' },
  { label: 'End',   key: 'End' },
  { label: '⎙',     key: 'Print' }, // Screenshot
];

/**
 * Second-tier hotkeys row — toggleable from the FloatingToolbar's expand
 * button. Mirrors the Kotlin app's expanded shortcut tier (DraggableToolbar
 * row 2). Keys are sent over the LiveKit data channel as `{type:'key',key:'…'}`.
 */
export default function ExpandedHotkeysRow() {
  const { sendControl } = useDesktopRoom();

  return (
    <div
      onPointerDown={(e) => e.stopPropagation()}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 4,
        background: 'rgba(14,14,18,0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 10,
        padding: 6,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        maxWidth: 240,
      }}
    >
      {KEYS.map((k) => (
        <button
          key={k.key}
          onPointerDown={(e) => { e.stopPropagation(); sendControl({ type: 'key', key: k.key }); }}
          style={{
            minWidth: 36,
            height: 26,
            padding: '0 8px',
            borderRadius: 6,
            background: 'rgba(255,255,255,0.08)',
            border: '1px solid rgba(255,255,255,0.06)',
            color: 'rgba(255,255,255,0.85)',
            fontSize: 11,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          {k.label}
        </button>
      ))}
    </div>
  );
}
