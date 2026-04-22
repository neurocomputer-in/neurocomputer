'use client';
import { Brain } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openTab, setActiveTab } from '@/store/conversationSlice';
import { setPaneActiveCid } from '@/store/uiSlice';

/**
 * "NeuroIDE" button for the TopBar. Clicking opens (or focuses) a
 * neuroide tab in the currently focused pane — mirrors TerminalButton's
 * "new terminal" flow, minus the listing/selection (there's only one
 * logical IDE — no per-project IDE sessions to pick from).
 */
export default function NeuroIDEButton() {
  const dispatch = useAppDispatch();
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);

  const openIDE = () => {
    // Reuse an existing neuroIDE tab if one is open, else create one.
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
        display: 'flex', alignItems: 'center', gap: '6px',
        background: 'rgba(255,255,255,0.02)', padding: '5px 10px',
        borderRadius: '6px', cursor: 'pointer', userSelect: 'none',
        transition: 'background 0.15s',
        border: '1px solid rgba(255,255,255,0.05)',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
    >
      <Brain size={13} color="#c4b5fd" />
      <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>NeuroIDE</span>
    </div>
  );
}
