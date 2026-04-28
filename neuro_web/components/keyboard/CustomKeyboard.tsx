'use client';
import { useState } from 'react';

type Layer = 'letters' | 'symbols';

const LETTER_ROWS: string[][] = [
  ['1','2','3','4','5','6','7','8','9','0'],
  ['q','w','e','r','t','y','u','i','o','p'],
  ['a','s','d','f','g','h','j','k','l'],
  ['z','x','c','v','b','n','m'],
];

const SYMBOL_ROWS: string[][] = [
  ['1','2','3','4','5','6','7','8','9','0'],
  ['-','/',':',';','(',')','$','&','@','"'],
  ['#','=','*','+','!','?','{','}','|','~'],
  ['<','>','[',']','`','\\','^','_'],
];

const DISPLAY: Record<string, string> = {
  Return: '↵', BackSpace: '⌫', space: 'space',
  shift: '⇧', SHIFT_LOCKED: '⇧',
  bracketleft: '[', bracketright: ']',
  semicolon: ';', apostrophe: "'", comma: ',', period: '.', slash: '/',
};

export interface ModifierState {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
}

interface Props {
  modifiers: ModifierState;
  onKey: (combo: string) => void;
  onToggleModifier: (m: 'ctrl' | 'alt' | 'shift') => void;
  onClearModifiers: () => void;
}

/**
 * Samsung / iOS-style soft keyboard. Four rows: numbers, two letter rows,
 * one mixed (shift + letters + backspace), then a bottom strip with layer
 * toggle, comma, space, period, return.
 *
 * Modifier flow: tapping Shift on the letters layer just uppercases the
 * next typed letter (consumed automatically). The hotkey toolbar above
 * (MobileKeyBar) handles Ctrl / Alt / Esc / Tab / Enter-to-PTY.
 *
 * `onKey(combo)` receives values like 'a', 'A', '1', 'Return', 'space',
 * 'BackSpace'. Combos with modifiers (e.g. 'ctrl+c') are *not* generated
 * here — Ctrl lives in the toolbar above and operates on raw PTY bytes.
 */
export default function CustomKeyboard({ modifiers, onKey, onToggleModifier, onClearModifiers }: Props) {
  const [layer, setLayer] = useState<Layer>('letters');
  const rows = layer === 'letters' ? LETTER_ROWS : SYMBOL_ROWS;

  function emit(key: string) {
    onKey(key);
    // Shift is one-shot — after typing one character, drop it.
    if (modifiers.shift) onClearModifiers();
  }

  function tapKey(key: string) {
    if (key.length === 1 && /[a-z]/.test(key) && modifiers.shift) {
      emit(key.toUpperCase());
    } else {
      emit(key);
    }
  }

  return (
    <div style={{
      background: 'rgba(18,18,22,0.96)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      padding: '6px 4px',
      paddingBottom: 'max(env(safe-area-inset-bottom), 6px)',
      userSelect: 'none',
      WebkitUserSelect: 'none',
    }}>
      {rows.map((row, ri) => (
        <div key={ri} style={{
          display: 'flex', gap: 4, marginBottom: 4,
          padding: '0 4px', justifyContent: 'center',
        }}>
          {/* Last row of letters: shift on left, backspace on right */}
          {layer === 'letters' && ri === 3 && (
            <Key wide active={modifiers.shift} onTap={() => onToggleModifier('shift')}>
              {DISPLAY.shift}
            </Key>
          )}

          {row.map((k) => (
            <Key key={k} onTap={() => tapKey(k)}>
              {modifiers.shift && /[a-z]/.test(k) ? k.toUpperCase() : k}
            </Key>
          ))}

          {layer === 'letters' && ri === 3 && (
            <Key wide onTap={() => emit('BackSpace')}>{DISPLAY.BackSpace}</Key>
          )}
          {layer === 'symbols' && ri === 3 && (
            <Key wide onTap={() => emit('BackSpace')}>{DISPLAY.BackSpace}</Key>
          )}
        </div>
      ))}

      {/* Bottom strip: layer toggle, comma, space, period, return */}
      <div style={{ display: 'flex', gap: 4, padding: '0 4px' }}>
        <Key wide onTap={() => setLayer(l => l === 'letters' ? 'symbols' : 'letters')}>
          {layer === 'letters' ? '?123' : 'ABC'}
        </Key>
        <Key onTap={() => emit(',')}>,</Key>
        <Key flex={5} onTap={() => emit('space')}>space</Key>
        <Key onTap={() => emit('.')}>.</Key>
        <Key wide accent onTap={() => emit('Return')}>{DISPLAY.Return}</Key>
      </div>
    </div>
  );
}

function Key({
  children, onTap, wide, flex, active, accent,
}: {
  children: React.ReactNode;
  onTap: () => void;
  wide?: boolean;
  flex?: number;
  active?: boolean;
  accent?: boolean;
}) {
  const f = flex ?? (wide ? 1.6 : 1);
  return (
    <button
      onPointerDown={(e) => { e.preventDefault(); onTap(); }}
      style={{
        flex: f, minWidth: 0,
        height: 38, borderRadius: 6,
        background: active ? '#6366f1'
          : accent ? 'rgba(94,106,210,0.28)'
          : 'rgba(255,255,255,0.10)',
        color: 'rgba(255,255,255,0.95)',
        border: '1px solid ' + (accent ? 'rgba(94,106,210,0.5)' : 'rgba(255,255,255,0.06)'),
        fontSize: 14,
        fontWeight: 500,
        cursor: 'pointer',
        padding: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      {children}
    </button>
  );
}
