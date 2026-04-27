'use client';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { useIsMobile } from '@/hooks/useIsMobile';
import WindowComponent from './Window';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';
import DesktopApp from '@/components/mobile-desktop/DesktopApp';

const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });
const NeuroIDEPanel = dynamic(() => import('@/components/neuroide/NeuroIDEPanel'), { ssr: false });

function ChatWindowContent() {
  const [inputHidden, setInputHidden] = useState(false);
  const isMobile = useIsMobile();
  return (
    <>
      <ChatPanel />
      <VoiceCallPanel />
      {/* Hide the collapse handle entirely on mobile — it reads as a stray
          floating "tab" above the input. Mobile doesn't need an input toggle. */}
      {!isMobile && (
        <div
          onClick={() => setInputHidden(h => !h)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: 14, flexShrink: 0, cursor: 'pointer', background: 'transparent',
          }}
        >
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '2px 12px', borderRadius: 6,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.05)',
          }}>
            <div style={{ width: 20, height: 2, borderRadius: 1, background: 'rgba(255,255,255,0.15)' }} />
            {inputHidden ? <ChevronUp size={9} color="rgba(255,255,255,0.3)" /> : <ChevronDown size={9} color="rgba(255,255,255,0.3)" />}
          </div>
        </div>
      )}
      <AnimatePresence initial={false}>
        {!inputHidden && (
          <motion.div
            key="chat-input"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.8 }}
            style={{ overflow: 'hidden', flexShrink: 0 }}
          >
            <ChatInput />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function WindowContent({ tabKind }: { tabKind: string }) {
  switch (tabKind) {
    case 'terminal': return <TerminalPanel />;
    case 'neuroide': return <NeuroIDEPanel />;
    case 'desktop': return <DesktopApp />;
    default: return <ChatWindowContent />;
  }
}

export default function WindowManager({ onNewTab }: {
  onNewTab?: (windowId: string, appId: string, tabKind: string) => void;
}) {
  const windows = useAppSelector(s => s.os.windows);

  return (
    <div
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: 'transparent', pointerEvents: 'none' }}
    >
      {windows.map(w => {
        const activeTab = w.tabs.find(t => t.id === w.activeTabId);
        const tabKind = activeTab?.type ?? 'chat';
        return (
          <WindowComponent key={w.id} windowId={w.id} onNewTab={onNewTab}>
            <WindowContent tabKind={tabKind} />
          </WindowComponent>
        );
      })}
    </div>
  );
}
