'use client';
import { useState } from 'react';
import { Menu } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setActiveTabInWindow, reorderWindowTabs, closeTabFromWindow } from '@/store/osSlice';
import { closeTab } from '@/store/conversationSlice';
import WindowTabStrip from './WindowTabStrip';
import TabOverviewPopover from './TabOverviewPopover';

interface Props {
  activeWindowId: string | null;
  onMenuOpen: () => void;
  onNewTab: (windowId: string) => void;
  onSwitcherOpen: () => void;
}

export default function MobileTabStrip({ activeWindowId, onMenuOpen, onNewTab, onSwitcherOpen }: Props) {
  const dispatch = useAppDispatch();
  const win = useAppSelector(s => s.os.windows.find(w => w.id === activeWindowId));
  const [overviewOpen, setOverviewOpen] = useState(false);

  if (!win) {
    return (
      <div style={{
        height: 36, flexShrink: 0, display: 'flex', alignItems: 'center',
        padding: '0 12px', background: 'rgba(14,14,16,0.98)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <button onClick={onMenuOpen} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'rgba(255,255,255,0.5)' }}>
          <Menu size={16} />
        </button>
      </div>
    );
  }

  return (
    <div style={{
      height: 36, flexShrink: 0, display: 'flex', alignItems: 'stretch',
      background: 'rgba(14,14,16,0.98)',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
      position: 'relative', zIndex: 100,
    }}>
      <button
        onClick={onMenuOpen}
        style={{
          flexShrink: 0, width: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'rgba(255,255,255,0.5)', borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <Menu size={15} />
      </button>

      <WindowTabStrip
        tabs={win.tabs}
        activeTabId={win.activeTabId}
        isWindowActive={true}
        onActivate={(tabId) => dispatch(setActiveTabInWindow({ windowId: win.id, tabId }))}
        onClose={(tabId) => {
          const tab = win.tabs.find(t => t.id === tabId);
          if (tab) dispatch(closeTab(tab.cid));
          dispatch(closeTabFromWindow({ windowId: win.id, tabId }));
        }}
        onReorder={(from, to) => dispatch(reorderWindowTabs({ windowId: win.id, fromIndex: from, toIndex: to }))}
        onOverflowPill={() => setOverviewOpen(true)}
        onNewTab={() => onNewTab(win.id)}
      />

      {overviewOpen && (
        <TabOverviewPopover
          tabs={win.tabs}
          activeTabId={win.activeTabId}
          onActivate={(tabId) => { dispatch(setActiveTabInWindow({ windowId: win.id, tabId })); setOverviewOpen(false); }}
          onClose={() => setOverviewOpen(false)}
        />
      )}
    </div>
  );
}
