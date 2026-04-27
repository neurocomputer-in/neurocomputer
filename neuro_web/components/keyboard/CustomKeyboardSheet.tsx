'use client';
import { motion, AnimatePresence } from 'framer-motion';
import CustomKeyboard, { ModifierState } from './CustomKeyboard';

interface Props {
  open: boolean;
  onKey: (combo: string) => void;
  modifiers: ModifierState;
  onToggleModifier: (m: 'ctrl' | 'alt' | 'shift') => void;
  onClearModifiers: () => void;
}

export default function CustomKeyboardSheet({
  open, onKey, modifiers, onToggleModifier, onClearModifiers,
}: Props) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
          style={{
            position: 'absolute',
            left: 0, right: 0, bottom: 0,
            zIndex: 30,
            touchAction: 'none',
          }}
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
