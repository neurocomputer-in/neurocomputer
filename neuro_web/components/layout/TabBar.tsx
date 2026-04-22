'use client';
import { useEffect, useRef, useState } from 'react';
import { Plus, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeTab, loadMessages, setActiveTab } from '@/store/conversationSlice';
import { useLiveKitContext } from '@/providers/LiveKitProvider';
import { AGENT_LIST, AgentType } from '@/types';
import AgentIcon from '@/components/agent/AgentIcon';

interface Props {
  onNewTab: () => void;
}

export default function TabBar({ onNewTab }: Props) {
  const dispatch = useAppDispatch();
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const { connectToConversation } = useLiveKitContext();

  const visibleTabs = agentFilter === AgentType.ALL
    ? openTabs
    : openTabs.filter(t => t.agentId === agentFilter);

  const handleSwitchTab = async (cid: string) => {
    if (cid === activeTabCid) return;
    dispatch(setActiveTab(cid));
    await connectToConversation(cid);
    if (!tabMessages[cid] || tabMessages[cid].length === 0) {
      dispatch(loadMessages(cid));
    }
  };

  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Tabs are restored from localStorage on the client after mount, so
  // server-rendered HTML (0 tabs) diverges from client-rendered HTML
  // (N tabs). Gate the tab list on mount to avoid hydration mismatch.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  // Convert vertical wheel scrolls into horizontal scrolls inside the tab
  // strip, so laptops without a trackpad can still traverse many tabs.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
      el.scrollLeft += e.deltaY;
      e.preventDefault();
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  return (
    <div
      style={{
        height: '36px',
        minHeight: '36px',
        display: 'flex',
        alignItems: 'stretch',
        background: 'rgba(15, 16, 17, 0.8)',
        backdropFilter: 'blur(10px)',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      <div
        ref={scrollRef}
        className="tabbar-scroll"
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          alignItems: 'stretch',
          overflowX: 'auto',
          overflowY: 'hidden',
          scrollbarWidth: 'none',
        }}
      >
      {mounted && visibleTabs.map((tab) => {
        const isActive = tab.cid === activeTabCid;
        const agent = AGENT_LIST.find(a => a.type === tab.agentId) ?? AGENT_LIST[1];
        return (
          <motion.div
            key={tab.cid}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            whileHover={!isActive ? { backgroundColor: 'rgba(255,255,255,0.02)' } : {}}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '0 14px',
              fontSize: '12px',
              color: isActive ? '#f7f8f8' : '#62666d',
              borderTop: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              background: isActive ? 'rgba(255,255,255,0.03)' : 'transparent',
              gap: '6px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              userSelect: 'none',
              flexShrink: 0,
            }}
            onClick={() => handleSwitchTab(tab.cid)}
          >
            <AgentIcon agent={agent} size={13} />
            <span
              title={tab.workdir ? `${tab.title} — ${tab.workdir}` : tab.title}
              style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: isActive ? 510 : 400 }}
            >
              {tab.title}
            </span>
            {tab.workdir && (
              <span style={{
                fontSize: '10px', color: isActive ? 'var(--accent)' : 'rgba(113,112,255,0.5)',
                fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                maxWidth: '80px',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {tab.workdir.split('/').pop() || tab.workdir}
              </span>
            )}
            <motion.span
              whileHover={{ opacity: 1, backgroundColor: 'rgba(255,255,255,0.08)' }}
              whileTap={{ scale: 0.9 }}
              onClick={(e) => { e.stopPropagation(); dispatch(closeTab(tab.cid)); }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: '16px', height: '16px', borderRadius: '4px',
                opacity: 0.3,
              }}
            >
              <X size={11} color="#8a8f98" />
            </motion.span>
          </motion.div>
        );
      })}
      </div>
      <div style={{
        flexShrink: 0,
        borderLeft: '1px solid rgba(255,255,255,0.05)',
        background: 'rgba(15, 16, 17, 0.92)',
        boxShadow: '-8px 0 12px -8px rgba(0,0,0,0.5)',
      }}>
        <motion.div
          whileHover={{ opacity: 1, backgroundColor: 'rgba(255,255,255,0.04)' }}
          whileTap={{ scale: 0.9 }}
          onClick={onNewTab}
          title="New chat"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 14px', cursor: 'pointer',
            opacity: 0.7, height: '100%',
          }}
        >
          <Plus size={14} color="#d0d6e0" />
        </motion.div>
      </div>
    </div>
  );
}
