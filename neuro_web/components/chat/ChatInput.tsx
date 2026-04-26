'use client';
import { KeyboardEvent, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Paperclip, ArrowUp, Mic, Square, CircleStop, Phone, PhoneOff, Settings2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setInputText, setLoading } from '@/store/chatSlice';
import { AgentType } from '@/types';
import { apiCancelChat } from '@/services/api';
import { useChat } from '@/hooks/useChat';
import { useVoice } from '@/hooks/useVoice';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import { useIsMobile } from '@/hooks/useIsMobile';
import { useIsIOS } from '@/hooks/useIsIOS';
import LlmSelector from './LlmSelector';

export default function ChatInput() {
  const dispatch = useAppDispatch();
  const isMobile = useIsMobile();
  const isIOS = useIsIOS();
  const { sendMessage, inputText, isLoading } = useChat();
  const { recording, startRecording, stopAndSend } = useVoice();
  const { startCall, endCall, isActive: voiceCallActive, connecting: voiceConnecting } = useVoiceCall();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeTab = openTabs.find(t => t.cid === activeTabCid);
  const activeTabFilteredOut = activeTab && agentFilter !== AgentType.ALL && activeTab.agentId !== agentFilter;

  const noConversation = !activeTabCid || !!activeTabFilteredOut;

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && inputText.trim()) {
        sendMessage(inputText);
        // Skip on real iOS only. Programmatic focus from a setTimeout is
        // outside the user-gesture context on iOS Safari → keyboard dismisses.
        // Desktop mobile-emulation in DevTools is fine since there's no
        // virtual keyboard there.
        if (!isIOS) setTimeout(() => textareaRef.current?.focus(), 0);
      }
    }
  };

  useEffect(() => {
    if (isIOS) return;
    if (!recording && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [activeTabCid, recording, isIOS]);

  useEffect(() => {
    if (isIOS) return;
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading, isIOS]);

  const handleMicClick = () => {
    if (recording) {
      stopAndSend();
    } else {
      startRecording();
    }
  };

  const handleStop = () => {
    dispatch(setLoading(false));
    if (activeTabCid) {
      apiCancelChat(activeTabCid).catch(() => {});
    }
  };

  const handleSend = () => {
    sendMessage(inputText);
    if (!isIOS) setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const canSend = !isLoading && inputText.trim().length > 0 && !recording;

  const btnSize = isMobile ? '32px' : '30px';
  const iconSize = isMobile ? 14 : 14;
  const gap = isMobile ? '6px' : '10px';
  const innerGap = isMobile ? '6px' : '6px';
  const containerPad = isMobile ? '8px 10px' : '10px 14px';
  const outerPad = isMobile ? '8px 10px 10px' : '12px 24px 16px';

  return (
    <div style={{
      paddingTop: outerPad.split(' ')[0],
      paddingLeft: outerPad.split(' ')[1],
      paddingRight: outerPad.split(' ')[1] || outerPad.split(' ')[1],
      paddingBottom: isMobile ? 'calc(10px + var(--safe-bottom))' : outerPad.split(' ')[2] || outerPad.split(' ')[0],
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: '0px',
      justifyContent: 'center',
      alignItems: 'center',
    }}>
      <motion.div
        className="glass-bubble"
        style={{
          width: '100%',
          maxWidth: '1024px',
          border: `1px solid ${recording ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.08)'}`,
          borderRadius: '8px',
          padding: containerPad,
          display: 'flex',
          // Mobile: stack LlmSelector ABOVE input row inside the same bubble
          // so they read as one panel — not two separate floating tabs.
          flexDirection: isMobile ? 'column' : 'row',
          alignItems: isMobile ? 'stretch' : 'flex-end',
          gap: isMobile ? '6px' : gap,
          transition: 'border-color 0.2s',
          flexWrap: 'nowrap',
        }}
      >
        {isMobile && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            paddingBottom: '6px',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            overflowX: 'auto',
          }}>
            <LlmSelector />
          </div>
        )}
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap,
          width: '100%',
        }}>
        {!isMobile && (
          <div
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '28px', height: '28px', borderRadius: '6px',
              cursor: 'not-allowed', opacity: 0.3, flexShrink: 0, marginBottom: '1px',
            }}
          >
            <Paperclip size={15} color="#8a8f98" />
          </div>
        )}

        {recording ? (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', gap: '10px',
            padding: '4px 0', color: '#ef4444', fontSize: '13px', fontWeight: 400,
          }}>
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: '#ef4444', animation: 'pulse 1.2s infinite',
              flexShrink: 0,
            }} />
            Recording... tap mic to send
          </div>
        ) : (
          <textarea
            data-testid="chat-input"
            ref={textareaRef}
            value={inputText}
            onChange={(e) => dispatch(setInputText(e.target.value))}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? 'Type your next message...' : 'Ask anything...'}
            rows={1}
            style={{
              flex: 1,
              minWidth: 0,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#f7f8f8',
              fontSize: isMobile ? '16px' : '14px', // 16px prevents iOS zoom
              resize: 'none',
              fontFamily: 'inherit',
              lineHeight: 1.6,
              maxHeight: '140px',
              overflow: 'auto',
              paddingTop: '4px',
              fontWeight: 400,
            }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = 'auto';
              el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
            }}
          />
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: innerGap, paddingBottom: '1px', flexShrink: 0 }}>
          {/* Desktop: LLM selector inline */}
          {!isMobile && (
            <>
              <LlmSelector />
              <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)', marginRight: '2px' }} />
            </>
          )}

          {/* Voice call button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onMouseDown={e => e.preventDefault()}
            onClick={voiceCallActive ? endCall : startCall}
            disabled={voiceConnecting}
            style={{
              width: btnSize, height: btnSize, borderRadius: '6px',
              background: voiceCallActive ? 'rgba(39, 166, 68, 0.12)' : 'rgba(255,255,255,0.03)',
              border: voiceCallActive ? '1px solid rgba(39, 166, 68, 0.2)' : '1px solid transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', flexShrink: 0,
            }}
            title={voiceCallActive ? 'End voice call' : 'Start voice call'}
          >
            {voiceCallActive ? (
              <PhoneOff size={iconSize} color="#27a644" />
            ) : voiceConnecting ? (
              <Phone size={iconSize} color="#8a8f98" style={{ animation: 'pulse 1s infinite' }} />
            ) : (
              <Phone size={iconSize} color="#8a8f98" />
            )}
          </motion.button>

          {/* Mic button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onMouseDown={e => e.preventDefault()}
            onClick={handleMicClick}
            disabled={(isLoading && !recording) || voiceCallActive}
            style={{
              width: btnSize, height: btnSize, borderRadius: '6px',
              background: recording ? '#ef4444' : 'rgba(255,255,255,0.03)',
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: voiceCallActive ? 'not-allowed' : 'pointer',
              opacity: voiceCallActive ? 0.3 : 1,
              flexShrink: 0,
            }}
            title={recording ? 'Stop & send voice' : 'Record voice message'}
          >
            {recording ? <Square size={iconSize - 1} color="#fff" /> : <Mic size={iconSize + 1} color="#8a8f98" />}
          </motion.button>

          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />

          {/* Send or Stop button */}
          {isLoading ? (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onMouseDown={e => e.preventDefault()}
              data-testid="stop-button"
              onClick={handleStop}
              style={{
                width: btnSize, height: btnSize, borderRadius: '6px',
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', flexShrink: 0,
              }}
              title="Stop generating"
            >
              <CircleStop size={iconSize} color="#ef4444" strokeWidth={1.8} />
            </motion.button>
          ) : (
            <motion.button
              whileHover={canSend ? { scale: 1.05 } : {}}
              whileTap={canSend ? { scale: 0.95 } : {}}
              onMouseDown={e => e.preventDefault()}
              data-testid="send-button"
              onClick={handleSend}
              disabled={!canSend}
              style={{
                width: btnSize, height: btnSize, borderRadius: '6px',
                background: canSend ? 'var(--accent)' : 'rgba(255,255,255,0.03)',
                border: 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: canSend ? 'pointer' : 'default',
                transition: 'background 0.2s',
                flexShrink: 0,
              }}
            >
              <ArrowUp size={iconSize} color={canSend ? '#fff' : '#62666d'} strokeWidth={2.5} />
            </motion.button>
          )}
        </div>
        </div>
      </motion.div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}</style>
    </div>
  );
}
