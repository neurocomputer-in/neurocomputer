'use client';

interface Props {
  open: boolean;
  onKey: (combo: string) => void;
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean };
  onToggleModifier: (m: 'ctrl' | 'alt' | 'shift') => void;
  onClearModifiers: () => void;
}

export default function CustomKeyboardSheet(_props: Props) {
  return null;
}
