'use client';
import { useEffect, useLayoutEffect, useRef, useCallback, useState } from 'react';
import { Plus, Sparkles, ArrowRight, Search, FileText, Code, ChevronDown, Folder } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { usePaneCid } from '@/components/panes/PaneContext';
import { AGENT_LIST, AgentType } from '@/types';
import { createConversation, openTab, setActiveTab, updateTabAgent } from '@/store/conversationSlice';
import { setInputText } from '@/store/chatSlice';
import { useLiveKitContext } from '@/providers/LiveKitProvider';
import { useChat } from '@/hooks/useChat';
import { apiUpdateConversationAgent } from '@/services/api';
import AgentIcon from '@/components/agent/AgentIcon';
import MessageBubble from './MessageBubble';
import ThinkingIndicator from './ThinkingIndicator';
// NOTE: VoiceCallPanel is rendered at page-level now (app/page.tsx) so it
// persists across chat/terminal/3D views. Don't reintroduce it here.
import LoadingIndicator from '@/components/common/LoadingIndicator';

const SUGGESTIONS = [
  { icon: ArrowRight, text: 'What can you help me with?' },
  { icon: Search, text: 'Search the web for latest news' },
  { icon: Code, text: 'Write a Python script for me' },
  { icon: FileText, text: 'Summarize a document' },
];

function WelcomePage({ projectName }: { projectName: string }) {
  const dispatch = useAppDispatch();
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '40px 24px',
    }}>
      <div style={{ maxWidth: '600px', width: '100%', textAlign: 'center' }}>
        <div style={{
          width: '52px', height: '52px', borderRadius: '12px',
          background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 20px', fontSize: '22px', fontWeight: 590, color: '#fff',
        }}>
          N
        </div>
        <h1 style={{
          fontSize: '32px', fontWeight: 510, color: '#f7f8f8',
          marginBottom: '8px', letterSpacing: '-0.704px',
          lineHeight: 1.13,
        }}>
          Welcome to Neuro
        </h1>
        <p style={{ fontSize: '15px', color: '#8a8f98', marginBottom: '32px', lineHeight: 1.6, fontWeight: 400 }}>
          {projectName
            ? <>Working in <span style={{ color: 'var(--accent)', fontWeight: 510 }}>{projectName}</span> — type below to start a new session</>
            : <>Your AI assistant is ready. Type below to begin.</>
          }
        </p>

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '8px', textAlign: 'left',
        }}>
          {SUGGESTIONS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div
                key={i}
                onClick={() => dispatch(setInputText(s.text))}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '8px', padding: '14px 16px',
                  cursor: 'pointer', transition: 'all 0.15s',
                  display: 'flex', alignItems: 'flex-start', gap: '12px',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'; }}
              >
                <Icon size={15} color="#62666d" strokeWidth={1.8} style={{ marginTop: '1px', flexShrink: 0 }} />
                <div style={{ fontSize: '13px', color: '#8a8f98', fontWeight: 400 }}>{s.text}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function AgentSelector({ cid, currentAgentId, allowedAgents }: {
  cid: string;
  currentAgentId: string;
  allowedAgents: string[];
}) {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const options = AGENT_LIST.filter(a => {
    if (a.type === AgentType.ALL) return false;
    if (allowedAgents.length === 0) return true;
    return allowedAgents.includes(a.type);
  });
  const current = AGENT_LIST.find(a => a.type === currentAgentId) ?? AGENT_LIST[1];

  const handleChange = async (agentType: string) => {
    setOpen(false);
    dispatch(updateTabAgent({ cid, agentId: agentType }));
    try { await apiUpdateConversationAgent(cid, agentType); } catch {}
  };

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: 'rgba(255,255,255,0.03)', padding: '6px 12px',
          borderRadius: '6px', cursor: 'pointer', transition: 'background 0.15s',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
      >
        <AgentIcon agent={current} size={14} />
        <span style={{ fontSize: '13px', color: '#d0d6e0', fontWeight: 510 }}>{current.name}</span>
        <ChevronDown size={12} color="#62666d" style={{
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }} />
      </div>
      {open && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          marginBottom: '6px', background: '#191a1b',
          border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px',
          minWidth: '200px', zIndex: 100, overflow: 'hidden',
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)', padding: '4px',
        }}>
          {options.map(agent => {
            const isSelected = currentAgentId === agent.type;
            return (
              <div
                key={agent.type}
                onClick={() => handleChange(agent.type)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '8px 10px', cursor: 'pointer', fontSize: '13px',
                  color: isSelected ? '#f7f8f8' : '#d0d6e0',
                  background: isSelected ? 'rgba(255,255,255,0.05)' : 'transparent',
                  borderRadius: '6px', transition: 'background 0.12s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? 'rgba(255,255,255,0.05)' : 'transparent'; }}
              >
                <AgentIcon agent={agent} size={14} />
                <span style={{ fontWeight: 510 }}>{agent.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EmptyChat({ onSuggestionClick, cid, currentAgentId, allowedAgents }: {
  onSuggestionClick: (text: string) => void;
  cid: string;
  currentAgentId: string;
  allowedAgents: string[];
}) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '40px 24px',
    }}>
      <div style={{ maxWidth: '600px', width: '100%', textAlign: 'center' }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '8px',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.05)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          <Sparkles size={18} color="#7170ff" strokeWidth={1.5} />
        </div>
        <h2 style={{
          fontSize: '24px', fontWeight: 510, color: '#f7f8f8',
          marginBottom: '6px', letterSpacing: '-0.288px',
        }}>
          How can I help you?
        </h2>
        <p style={{ fontSize: '14px', color: '#62666d', marginBottom: '16px', fontWeight: 400 }}>
          Ask anything — code, research, automation, or just chat
        </p>

        <div style={{ marginBottom: '28px' }}>
          <AgentSelector cid={cid} currentAgentId={currentAgentId} allowedAgents={allowedAgents} />
        </div>

        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center',
        }}>
          {SUGGESTIONS.map((s, i) => {
            const Icon = s.icon;
            return (
              <button
                key={i}
                onClick={() => onSuggestionClick(s.text)}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '9999px', padding: '7px 14px',
                  fontSize: '13px', color: '#8a8f98', cursor: 'pointer',
                  transition: 'all 0.15s', fontFamily: 'inherit',
                  display: 'inline-flex', alignItems: 'center', gap: '6px',
                  fontWeight: 400,
                }}
                onMouseEnter={e => { e.currentTarget.style.color = '#f7f8f8'; e.currentTarget.style.borderColor = 'rgba(113,112,255,0.3)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = '#8a8f98'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}
              >
                <Icon size={12} strokeWidth={1.8} />
                {s.text}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function WorkdirModal({ onConfirm, onCancel }: {
  onConfirm: (path: string) => void;
  onCancel: () => void;
}) {
  const [path, setPath] = useState('/home/ubuntu');
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.85)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: '#191a1b', border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '12px', padding: '28px 32px', minWidth: '400px',
        boxShadow: '0 8px 30px rgba(0,0,0,0.6)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Folder size={18} color="#7170ff" />
          <span style={{ fontSize: '16px', fontWeight: 510, color: '#f7f8f8' }}>Choose Project Folder</span>
        </div>
        <p style={{ fontSize: '13px', color: '#62666d', marginBottom: '20px', fontWeight: 400 }}>
          OpenCode will work in this directory
        </p>
        <input
          autoFocus
          value={path}
          onChange={e => setPath(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && path.trim()) onConfirm(path.trim()); }}
          placeholder="/path/to/project"
          style={{
            width: '100%', background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px',
            padding: '10px 14px', fontSize: '14px', color: '#f7f8f8',
            outline: 'none', fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
            boxSizing: 'border-box',
          }}
          onFocus={e => (e.currentTarget.style.borderColor = 'rgba(113,112,255,0.4)')}
          onBlur={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
        />
        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px', padding: '8px 18px', fontSize: '13px',
              color: '#8a8f98', cursor: 'pointer', fontWeight: 510,
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => path.trim() && onConfirm(path.trim())}
            disabled={!path.trim()}
            style={{
              background: 'var(--accent)', border: 'none', borderRadius: '6px',
              padding: '8px 18px', fontSize: '13px', fontWeight: 510,
              color: '#fff', cursor: path.trim() ? 'pointer' : 'default',
              opacity: path.trim() ? 1 : 0.5,
            }}
          >
            Start Session
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPanel() {
  const dispatch = useAppDispatch();
  const paneCid = usePaneCid();
  const globalActiveCid = useAppSelector(s => s.conversations.activeTabCid);
  const activeTabCid = paneCid ?? globalActiveCid;
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const isLoading = useAppSelector(s => s.chat.isLoading);
  const thinkingContent = useAppSelector(s => s.chat.thinkingContent);
  const currentStep = useAppSelector(s => s.chat.currentStep);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const projects = useAppSelector(s => s.projects.projects);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const { connectToConversation } = useLiveKitContext();
  const { sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollPositionsRef = useRef<Record<string, number>>({});
  const userScrolledUpRef = useRef<Record<string, boolean>>({});
  const prevCidRef = useRef<string | null>(null);

  const activeTab = openTabs.find(t => t.cid === activeTabCid);
  const tabAgentId = activeTab?.agentId ?? AgentType.NEURO;
  const messages = activeTabCid ? (tabMessages[activeTabCid] ?? []) : [];
  const agentInfo = AGENT_LIST.find(a => a.type === tabAgentId) ?? AGENT_LIST[1];
  const currentProject = projects.find(p => p.id === selectedProjectId);
  const selectedWorkspace = workspaces.find(a => a.id === selectedWorkspaceId);
  const allowedAgents = selectedWorkspace?.agents ?? [];

  const [showWorkdirModal, setShowWorkdirModal] = useState(false);
  const pendingAgentRef = useRef<string | null>(null);

  // On tab switch: restore saved scroll position if the user had scrolled
  // up in that tab; otherwise stick to the bottom (latest message).
  useLayoutEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    if (prevCidRef.current === activeTabCid) return;
    prevCidRef.current = activeTabCid;
    if (activeTabCid != null) {
      if (userScrolledUpRef.current[activeTabCid]) {
        const saved = scrollPositionsRef.current[activeTabCid];
        if (saved !== undefined) el.scrollTop = saved;
      } else {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [activeTabCid]);

  // Auto-scroll to bottom when new content arrives (or when messages
  // finish loading async after a tab switch) — but only if the user
  // hasn't scrolled up in this tab.
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el || !activeTabCid) return;
    if (!userScrolledUpRef.current[activeTabCid]) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages.length, isLoading, thinkingContent, currentStep, activeTabCid]);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el || !activeTabCid) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    userScrolledUpRef.current[activeTabCid] = distanceFromBottom > 120;
    scrollPositionsRef.current[activeTabCid] = el.scrollTop;
  }, [activeTabCid]);

  const _createSessionWithWorkdir = useCallback(async (agentType: string, workdir?: string) => {
    const result = await dispatch(createConversation({
      agentId: agentType,
      projectId: selectedProjectId,
      workdir,
    }));
    if (createConversation.fulfilled.match(result)) {
      const conv = result.payload;
      dispatch(openTab({
        cid: conv.id,
        title: conv.title || 'New Chat',
        agentId: conv.agentId ?? agentType,
        isActive: true,
        workdir: conv.workdir,
      }));
      await connectToConversation(conv.id);
    }
  }, [dispatch, selectedProjectId, connectToConversation]);

  const handleWorkdirConfirm = useCallback(async (path: string) => {
    setShowWorkdirModal(false);
    const agent = pendingAgentRef.current ?? AgentType.OPENCODE;
    pendingAgentRef.current = null;
    await _createSessionWithWorkdir(agent, path);
  }, [_createSessionWithWorkdir]);

  const handleWorkdirCancel = useCallback(() => {
    setShowWorkdirModal(false);
    pendingAgentRef.current = null;
  }, []);

  useEffect(() => {
    if (agentFilter === AgentType.ALL) return;
    const matchingTab = openTabs.find(t => t.agentId === agentFilter);
    if (matchingTab) {
      dispatch(setActiveTab(matchingTab.cid));
      connectToConversation(matchingTab.cid);
      return;
    }
    if (agentFilter === AgentType.OPENCODE) {
      pendingAgentRef.current = agentFilter;
      setShowWorkdirModal(true);
      return;
    }
    (async () => {
      await _createSessionWithWorkdir(agentFilter);
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentFilter]);

  const handleNewSession = useCallback(async () => {
    const newAgentType = agentFilter === AgentType.ALL ? AgentType.NEURO : agentFilter;
    if (newAgentType === AgentType.OPENCODE) {
      pendingAgentRef.current = newAgentType;
      setShowWorkdirModal(true);
      return;
    }
    await _createSessionWithWorkdir(newAgentType);
  }, [agentFilter, _createSessionWithWorkdir]);

  const handleSuggestionClick = useCallback((text: string) => {
    if (activeTabCid) {
      sendMessage(text);
    }
  }, [activeTabCid, sendMessage]);

  const modal = showWorkdirModal && (
    <WorkdirModal onConfirm={handleWorkdirConfirm} onCancel={handleWorkdirCancel} />
  );

  const activeTabFilteredOut = activeTab && agentFilter !== AgentType.ALL && activeTab.agentId !== agentFilter;
  if (!activeTabCid || activeTabFilteredOut) {
    return (
      <>
        {modal}
        <WelcomePage projectName={currentProject?.name ?? ''} />
      </>
    );
  }

  if (messages.length === 0 && !isLoading) {
    return (
      <>
        {modal}
        <EmptyChat
          onSuggestionClick={handleSuggestionClick}
          cid={activeTabCid}
          currentAgentId={tabAgentId}
          allowedAgents={allowedAgents}
        />
      </>
    );
  }

  return (
    <>
      {modal}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        style={{
          flex: 1, overflowY: 'auto',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%', maxWidth: '1024px',
            padding: '24px 28px',
            display: 'flex', flexDirection: 'column',
          }}
        >
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              agentName={agentInfo.name}
              conversationId={activeTabCid ?? undefined}
            />
          ))}

          {isLoading && (thinkingContent || currentStep) && (
            <ThinkingIndicator
              thinkingContent={thinkingContent}
              currentStep={currentStep}
              agentInfo={agentInfo}
            />
          )}

          {isLoading && !thinkingContent && !currentStep && !messages.some(m => m.isStreaming) && (
            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '28px', height: '28px', minWidth: '28px',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: '6px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginTop: '2px', flexShrink: 0,
                }}
              >
                <AgentIcon agent={agentInfo} size={14} />
              </div>
              <div
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '4px 8px 8px 8px',
                  padding: '12px 16px',
                }}
              >
                <LoadingIndicator />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>
    </>
  );
}
