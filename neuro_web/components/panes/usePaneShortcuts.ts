'use client';
import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { splitPane, setFocusedPaneId, closePane } from '@/store/uiSlice';

/**
 * Global keyboard shortcuts for split panes:
 *   Ctrl + \            → split the focused pane (up to 3)
 *   Ctrl + 1 / 2 / 3    → focus pane N by position
 *   Ctrl + W            → close the focused pane (only when >1 pane)
 *
 * Shortcuts are gated so they never fire while the user is typing in an
 * input, textarea, select, or contentEditable element.
 */
export function usePaneShortcuts() {
  const dispatch = useAppDispatch();
  const panes = useAppSelector(s => s.ui.panes);
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(input|textarea|select)$/i.test(target.tagName)) return;
      if (target?.isContentEditable) return;

      if (!e.ctrlKey && !e.metaKey) return;

      if (!e.shiftKey && e.key === '\\') {
        e.preventDefault();
        if (panes.length < 3) dispatch(splitPane());
        return;
      }

      if (['1', '2', '3'].includes(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        if (panes[idx]) {
          e.preventDefault();
          dispatch(setFocusedPaneId(panes[idx].id));
        }
        return;
      }

      if (e.key.toLowerCase() === 'w' && panes.length > 1) {
        e.preventDefault();
        dispatch(closePane(focusedPaneId));
        return;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [panes, focusedPaneId, dispatch]);
}
