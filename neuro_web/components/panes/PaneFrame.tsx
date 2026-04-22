'use client';
import { useMemo } from 'react';
import dynamic from 'next/dynamic';
import { X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setFocusedPaneId, closePane } from '@/store/uiSlice';
import { PaneContext, PaneBinding } from './PaneContext';
import PanePickerBar from './PanePickerBar';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';

const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });
const NeuroIDEPanel = dynamic(() => import('@/components/neuroide/NeuroIDEPanel'), { ssr: false });

interface Props { paneId: string; activeCid: string | null }

export default function PaneFrame({ paneId, activeCid }: Props) {
  const dispatch = useAppDispatch();
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);
  const paneCount = useAppSelector(s => s.ui.panes.length);
  const focused = focusedPaneId === paneId;
  const binding: PaneBinding = useMemo(
    () => ({ paneId, activeCid }),
    [paneId, activeCid],
  );
  const tab = useAppSelector(s =>
    s.conversations.openTabs.find(t => t.cid === activeCid) || null
  );
  const kind =
    tab?.type === 'terminal' ? 'terminal' :
    tab?.type === 'neuroide' ? 'neuroide' : 'chat';
  const multi = paneCount > 1;

  return (
    <PaneContext.Provider value={binding}>
      <div
        onMouseDown={() => { if (multi && !focused) dispatch(setFocusedPaneId(paneId)); }}
        style={{
          flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
          position: 'relative',
          borderLeft: multi ? '1px solid rgba(255,255,255,0.05)' : undefined,
          boxShadow: multi && focused ? 'inset 0 0 0 1px rgba(94,106,210,0.35)' : undefined,
          transition: 'box-shadow 0.15s',
        }}
      >
        {multi && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            background: 'rgba(15,16,17,0.6)', flexShrink: 0,
          }}>
            <PanePickerBar paneId={paneId} activeCid={activeCid} />
            <div style={{ flex: 1 }} />
            <button
              onClick={(e) => { e.stopPropagation(); dispatch(closePane(paneId)); }}
              title="Close pane"
              style={{
                width: 20, height: 20, borderRadius: 4, border: 'none',
                background: 'transparent', color: '#62666d', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            ><X size={12} /></button>
          </div>
        )}
        {activeCid ? (
          kind === 'terminal' ? <TerminalPanel /> :
          kind === 'neuroide' ? <NeuroIDEPanel /> :
          (<><ChatPanel /><VoiceCallPanel /><ChatInput /></>)
        ) : (
          <EmptyPane />
        )}
      </div>
    </PaneContext.Provider>
  );
}

function EmptyPane() {
  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#62666d', fontSize: 13, padding: 24, textAlign: 'center',
    }}>
      <div>
        <div style={{ marginBottom: 8 }}>Empty pane</div>
        <div style={{ fontSize: 11, color: '#50565d' }}>
          Use the picker above to drop a session in here.
        </div>
      </div>
    </div>
  );
}
