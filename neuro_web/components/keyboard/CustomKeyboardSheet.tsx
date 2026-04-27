'use client';
import { motion, AnimatePresence } from 'framer-motion';
import CustomKeyboard, { ModifierState } from './CustomKeyboard';

interface Props {
  open: boolean;
  onKey: (combo: string) => void;
  modifiers: ModifierState;
  onToggleModifier: (m: 'ctrl' | 'alt' | 'shift') => void;
  onClearModifiers: () => void;
  /**
   * - 'overlay' (default): position absolute, slides up over content. Used by
   *   the mobile-desktop streaming view where the keyboard floats over video.
   * - 'inline': lives in the flex flow, pushes adjacent content up. Used by
   *   the terminal so the input bar stays visible above the keyboard.
   */
  variant?: 'overlay' | 'inline';
}

export default function CustomKeyboardSheet({
  open, onKey, modifiers, onToggleModifier, onClearModifiers, variant = 'overlay',
}: Props) {
  const sheetStyle = variant === 'inline'
    ? { flexShrink: 0, overflow: 'hidden' as const, touchAction: 'none' as const }
    : { position: 'absolute' as const, left: 0, right: 0, bottom: 0, zIndex: 30, touchAction: 'none' as const };

  // Inline variant slides height (so the input bar above it stays visible).
  // Overlay variant slides Y (no need to push content; it floats above).
  const motionAnim = variant === 'inline'
    ? { initial: { height: 0 }, animate: { height: 'auto' }, exit: { height: 0 } }
    : { initial: { y: '100%' }, animate: { y: 0 }, exit: { y: '100%' } };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          {...motionAnim}
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
          style={sheetStyle}
        >
          <CustomKeyboard
            modifiers={modifiers}
            onKey={onKey}
            onToggleModifier={onToggleModifier}
            onClearModifiers={onClearModifiers}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
