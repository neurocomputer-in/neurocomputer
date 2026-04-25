'use client';
import { Brain } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openTab, setActiveTab } from '@/store/conversationSlice';
import { setPaneActiveCid } from '@/store/uiSlice';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function NeuroIDEButton() {
  const dispatch = useAppDispatch();
  const isMobile = useIsMobile();
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);

  const openIDE = () => {
    const existing = openTabs.find(t => t.type === 'neuroide');
    if (existing) {
      dispatch(setActiveTab(existing.cid));
      dispatch(setPaneActiveCid({ id: focusedPaneId, cid: existing.cid }));
      return;
    }
    const cid = `neuroide-${Date.now().toString(36)}`;
    dispatch(openTab({
      cid,
      title: 'NeuroIDE',
      agentId: 'neuroide',
      isActive: true,
      type: 'neuroide',
    }));
    dispatch(setPaneActiveCid({ id: focusedPaneId, cid }));
  };

  return (
    <div
      onClick={openIDE}
      title="Open NeuroIDE — 3D neuro library + editor"
      style={{
        display: 'flex', alignItems: 'center', gap: isMobile ? '4px' : '6px',
        background: 'rgba(255,255,255,0.02)',
        padding: isMobile ? '6px' : '5px 10px',
        borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
        transition: 'background 0.15s',
        border: '1px solid rgba(255,255,255,0.05)',
        touchAction: isMobile ? 'manipulation' : undefined,
        WebkitTapHighlightColor: isMobile ? 'transparent' : undefined,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
    >
      <Brain size={isMobile ? 14 : 13} color="#c4b5fd" />
      {!isMobile && <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>NeuroIDE</span>}
    </div>
  );
}
