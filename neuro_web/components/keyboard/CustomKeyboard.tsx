'use client';

const ROWS: string[][] = [
  ['F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12'],
  ['grave','1','2','3','4','5','6','7','8','9','0','minus','equal','BackSpace'],
  ['Tab','q','w','e','r','t','y','u','i','o','p','bracketleft','bracketright','backslash'],
  ['Caps_Lock','a','s','d','f','g','h','j','k','l','semicolon','apostrophe','Return'],
  ['shift','z','x','c','v','b','n','m','comma','period','slash','shift'],
  ['ctrl','alt','space','Left','Up','Down','Right','Escape'],
];

const DISPLAY: Record<string, string> = {
  BackSpace: '⌫', Tab: 'Tab', Caps_Lock: 'Caps', Return: '↵',
  shift: 'Shift', ctrl: 'Ctrl', alt: 'Alt', space: 'Space',
  Escape: 'Esc', Left: '←', Right: '→', Up: '↑', Down: '↓',
  grave: '`', minus: '-', equal: '=', bracketleft: '[', bracketright: ']',
  backslash: '\\', semicolon: ';', apostrophe: "'", comma: ',', period: '.', slash: '/',
};

const MODIFIERS = new Set(['ctrl', 'alt', 'shift']);
const WIDE_KEYS = new Set(['BackSpace','Tab','Caps_Lock','Return','space','shift','ctrl','alt','Escape']);

function keyLabel(k: string) { return DISPLAY[k] ?? k.toUpperCase(); }

export interface ModifierState {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
}

interface Props {
  modifiers: ModifierState;
  onKey: (combo: string) => void;       // called with full combo string like "ctrl+c" or "Return"
  onToggleModifier: (m: 'ctrl' | 'alt' | 'shift') => void;
  onClearModifiers: () => void;
}

export default function CustomKeyboard({ modifiers, onKey, onToggleModifier, onClearModifiers }: Props) {
  function handleKey(key: string) {
    if (MODIFIERS.has(key)) {
      onToggleModifier(key as 'ctrl' | 'alt' | 'shift');
      return;
    }
    const activeMods = (Object.entries(modifiers) as [string, boolean][])
      .filter(([, v]) => v)
      .map(([k]) => k);
    const combo = activeMods.length > 0 ? [...activeMods, key].join('+') : key;
    onKey(combo);
    onClearModifiers();
  }

  return (
    <div style={{
      background: 'rgba(18,18,22,0.96)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      padding: '6px 4px',
      paddingBottom: 'max(env(safe-area-inset-bottom), 6px)',
    }}>
      {/* Modifier pills row */}
      <div style={{ display: 'flex', gap: 6, padding: '0 4px 4px' }}>
        {(['ctrl', 'alt', 'shift'] as const).map(mod => (
          <button
            key={mod}
            onPointerDown={e => { e.preventDefault(); handleKey(mod); }}
            style={{
              padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
              background: modifiers[mod] ? '#6366f1' : 'rgba(255,255,255,0.08)',
              color: modifiers[mod] ? '#fff' : 'rgba(255,255,255,0.7)',
              border: 'none', cursor: 'pointer',
            }}
          >
            {mod.toUpperCase()}
          </button>
        ))}
      </div>

      {ROWS.map((row, ri) => (
        <div key={ri} style={{ display: 'flex', gap: 3, marginBottom: 3, justifyContent: 'center' }}>
          {row.map((key, ki) => {
            const isMod = MODIFIERS.has(key);
            const modActive = isMod && modifiers[key as keyof ModifierState];
            return (
              <button
                key={ki}
                onPointerDown={e => { e.preventDefault(); handleKey(key); }}
                style={{
                  flex: WIDE_KEYS.has(key) ? 2 : 1,
                  minWidth: 0,
                  height: 34,
                  borderRadius: 5,
                  background: modActive ? '#6366f1' : 'rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.92)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  fontSize: 11,
                  fontWeight: 500,
                  cursor: 'pointer',
                  padding: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                {keyLabel(key)}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
