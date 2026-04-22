'use client';
import { KeyboardEvent, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Paperclip, ArrowUp, Mic, Square, CircleStop, Phone, PhoneOff } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setInputText, setLoading } from '@/store/chatSlice';
import { AgentType } from '@/types';
import { apiCancelChat } from '@/services/api';
import { useChat } from '@/hooks/useChat';
import { useVoice } from '@/hooks/useVoice';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import LlmSelector from './LlmSelector';

export default function ChatInput() {
  const dispatch = useAppDispatch();
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
      // When no conversation exists, sendMessage will auto-create one
      // inside useChat — no separate "New Session" click required.
      if (!isLoading && inputText.trim()) {
        sendMessage(inputText);
        setTimeout(() => textareaRef.current?.focus(), 0);
      }
    }
  };

  useEffect(() => {
    if (!recording && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [activeTabCid, recording]);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

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
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  // With auto-create on first send, the input is usable even when there's
  // no active conversation. Only gate send on loading and non-empty text.
  const canSend = !isLoading && inputText.trim().length > 0 && !recording;

  return (
    <div style={{ padding: '12px 24px 16px', flexShrink: 0, display: 'flex', justifyContent: 'center' }}>
      <motion.div
        layout
        className="glass-bubble"
        style={{
          width: '100%',
          maxWidth: '1024px',
          border: `1px solid ${recording ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.08)'}`,
          borderRadius: '8px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'flex-end',
          gap: '10px',
          transition: 'border-color 0.2s',
        }}
      >
        <div
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: '28px', height: '28px', borderRadius: '6px',
            cursor: 'not-allowed', opacity: 0.3, flexShrink: 0, marginBottom: '1px',
          }}
        >
          <Paperclip size={15} color="#8a8f98" />
        </div>

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
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#f7f8f8',
              fontSize: '14px',
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingBottom: '1px', flexShrink: 0 }}>
          {/* Provider + model selector (inline, Gemini-style) */}
          <LlmSelector />

          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)', marginRight: '2px' }} />

          {/* Voice call button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={voiceCallActive ? endCall : startCall}
            disabled={voiceConnecting}
            style={{
              width: '30px', height: '30px', borderRadius: '6px',
              background: voiceCallActive ? 'rgba(39, 166, 68, 0.12)' : 'rgba(255,255,255,0.03)',
              border: voiceCallActive ? '1px solid rgba(39, 166, 68, 0.2)' : '1px solid transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
            }}
            title={voiceCallActive ? 'End voice call' : 'Start voice call'}
          >
            {voiceCallActive ? (
              <PhoneOff size={14} color="#27a644" />
            ) : voiceConnecting ? (
              <Phone size={14} color="#8a8f98" style={{ animation: 'pulse 1s infinite' }} />
            ) : (
              <Phone size={14} color="#8a8f98" />
            )}
          </motion.button>

          {/* Mic button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleMicClick}
            disabled={(isLoading && !recording) || voiceCallActive}
            style={{
              width: '30px', height: '30px', borderRadius: '6px',
              background: recording ? '#ef4444' : 'rgba(255,255,255,0.03)',
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: voiceCallActive ? 'not-allowed' : 'pointer',
              opacity: voiceCallActive ? 0.3 : 1,
            }}
            title={recording ? 'Stop & send voice' : 'Record voice message'}
          >
            {recording ? <Square size={13} color="#fff" /> : <Mic size={15} color="#8a8f98" />}
          </motion.button>

          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)' }} />

          {/* Send or Stop button */}
          {isLoading ? (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              data-testid="stop-button"
              onClick={handleStop}
              style={{
                width: '30px', height: '30px', borderRadius: '6px',
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
              title="Stop generating"
            >
              <CircleStop size={15} color="#ef4444" strokeWidth={1.8} />
            </motion.button>
          ) : (
            <motion.button
              whileHover={canSend ? { scale: 1.05 } : {}}
              whileTap={canSend ? { scale: 0.95 } : {}}
              data-testid="send-button"
              onClick={handleSend}
              disabled={!canSend}
              style={{
                width: '30px', height: '30px', borderRadius: '6px',
                background: canSend ? 'var(--accent)' : 'rgba(255,255,255,0.03)',
                border: 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: canSend ? 'pointer' : 'default',
                transition: 'background 0.2s',
              }}
            >
              <ArrowUp size={15} color={canSend ? '#fff' : '#62666d'} strokeWidth={2.5} />
            </motion.button>
          )}
        </div>
      </motion.div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}</style>
    </div>
  );
}
