'use client';
import { useEffect, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setActiveTabInWindow, closeTabFromWindow } from '@/store/osSlice';
import { closeTab } from '@/store/conversationSlice';

export function useKeyboardShortcuts(onNewTab: (windowId: string) => void) {
  const dispatch = useAppDispatch();
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const windows = useAppSelector(s => s.os.windows);

  const handleKey = useCallback((e: KeyboardEvent) => {
    const meta = e.metaKey || e.ctrlKey;
    if (!meta) return;
    const win = windows.find(w => w.id === activeWindowId);
    if (!win) return;

    if (e.key === 't') {
      e.preventDefault();
      onNewTab(win.id);
      return;
    }

    if (e.key === 'w') {
      e.preventDefault();
      const tab = win.tabs.find(t => t.id === win.activeTabId);
      if (tab) dispatch(closeTab(tab.cid));
      dispatch(closeTabFromWindow({ windowId: win.id, tabId: win.activeTabId }));
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      const idx = win.tabs.findIndex(t => t.id === win.activeTabId);
      const nextIdx = e.shiftKey
        ? (idx - 1 + win.tabs.length) % win.tabs.length
        : (idx + 1) % win.tabs.length;
      dispatch(setActiveTabInWindow({ windowId: win.id, tabId: win.tabs[nextIdx].id }));
      return;
    }

    const num = parseInt(e.key, 10);
    if (num >= 1 && num <= 9) {
      e.preventDefault();
      const target = win.tabs[num - 1];
      if (target) dispatch(setActiveTabInWindow({ windowId: win.id, tabId: target.id }));
    }
  }, [activeWindowId, windows, dispatch, onNewTab]);

  useEffect(() => {
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleKey]);
}
