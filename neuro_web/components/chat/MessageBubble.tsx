'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Volume2, VolumeX, Loader2, Mic } from 'lucide-react';
import { Message, AGENT_LIST } from '@/types';
import { useAppSelector } from '@/store/hooks';
import AgentIcon from '@/components/agent/AgentIcon';
import MarkdownRenderer from '@/components/common/MarkdownRenderer';
import OpenCodeMessage from './OpenCodeMessage';
import { requestTTS, playAudio, stopAudio, isPlaying } from '@/services/voice';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7001';

function resolveAudioUrl(url?: string): string | undefined {
  if (!url) return undefined;
  if (url.startsWith('http') || url.startsWith('blob:')) return url;
  return `${API_BASE}${url}`;
}

interface Props {
  message: Message;
  agentEmoji?: string;
  agentName?: string;
  conversationId?: string;
}

function formatTime(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function AudioBar({ src }: { src: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
      <Volume2 size={13} color="#8a8f98" />
      <audio controls src={src} style={{ height: '32px', flex: 1 }} />
    </div>
  );
}

export default function MessageBubble({ message, agentEmoji, agentName = 'Neuro', conversationId }: Props) {
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const agentInfo = AGENT_LIST.find(a => a.name === agentName) ?? AGENT_LIST[1];
  const [speaking, setSpeaking] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);

  const handleSpeak = async () => {
    if (speaking || isPlaying()) {
      stopAudio();
      setSpeaking(false);
      return;
    }
    if (!message.text || !conversationId) return;

    const existingUrl = ttsAudioUrl || (message.audioUrl ? resolveAudioUrl(message.audioUrl) : null);
    if (existingUrl) {
      setSpeaking(true);
      playAudio(existingUrl, () => setSpeaking(false));
      return;
    }

    setTtsLoading(true);
    try {
      const { audio_url } = await requestTTS(message.text, conversationId);
      const resolved = resolveAudioUrl(audio_url)!;
      setTtsAudioUrl(resolved);
      setSpeaking(true);
      setTtsLoading(false);
      playAudio(resolved, () => setSpeaking(false));
    } catch (e) {
      console.error('TTS error:', e);
      setTtsLoading(false);
    }
  };

  // User message
  if (message.isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        data-testid="user-message" 
        style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}
      >
        <div style={{ maxWidth: '72%' }}>
          <div style={{
            fontSize: '11px', color: '#62666d', marginBottom: '5px', textAlign: 'right',
            display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '5px',
            fontWeight: 400,
          }}>
            <span>You</span>
            {message.isVoice && <Mic size={9} color="#62666d" />}
            {message.timestamp && <span style={{ color: '#3e3e44' }}>{formatTime(message.timestamp)}</span>}
          </div>
          <div
            className="glass-user-bubble"
            style={{
              borderRadius: '8px 2px 8px 8px',
              padding: '12px 18px',
              fontSize: '14px', color: '#d0d6e0', lineHeight: 1.6,
              fontWeight: 400,
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}
          >
            {message.isVoice && message.audioUrl && (
              <AudioBar src={resolveAudioUrl(message.audioUrl)!} />
            )}
            {message.text === 'Transcribing...' ? (
              <span style={{ color: '#8a8f98', fontStyle: 'italic' }}>Transcribing...</span>
            ) : (
              message.text && <span>{message.text}</span>
            )}
          </div>
        </div>
      </motion.div>
    );
  }

  // Step progress message
  if (message.messageType === 'step_progress' && message.stepInfo) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: '6px',
        padding: '4px 0', marginBottom: '4px',
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: message.stepInfo.status === 'running' ? 'var(--accent)' : '#27a644',
        }} />
        <span style={{ fontSize: '12px', color: '#62666d', fontWeight: 400 }}>
          {message.stepInfo.status === 'running' ? 'Running' : 'Done'}: {message.stepInfo.neuroName}
        </span>
      </div>
    );
  }

  // Agent message
  const audioSrc = ttsAudioUrl || (message.audioUrl ? resolveAudioUrl(message.audioUrl) : null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      data-testid="agent-message" style={{ display: 'flex', gap: '12px', marginBottom: '20px', maxWidth: '80%' }}
    >
      <div
        className="glass-bubble"
        style={{
          width: '28px', height: '28px', minWidth: '28px',
          borderRadius: '6px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: '2px', flexShrink: 0,
        }}
      >
        <AgentIcon agent={agentInfo} size={14} />
      </div>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{
          fontSize: '11px', color: '#62666d', marginBottom: '5px',
          display: 'flex', alignItems: 'center', gap: '5px',
        }}>
          <span style={{ fontWeight: 510, color: '#8a8f98' }}>{agentName}</span>
          {message.isVoice && <Mic size={9} color="#62666d" />}
          {message.timestamp && <span style={{ color: '#3e3e44' }}>{formatTime(message.timestamp)}</span>}
          {/* TTS speak button */}
          {!message.isStreaming && message.text && conversationId && (
            <button
              onClick={handleSpeak}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '0 2px', display: 'flex', alignItems: 'center',
                opacity: 0.4, transition: 'opacity 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0.4')}
              title={speaking ? 'Stop' : 'Speak'}
            >
              {ttsLoading ? (
                <Loader2 size={11} color="#8a8f98" style={{ animation: 'spin 1s linear infinite' }} />
              ) : speaking ? (
                <VolumeX size={11} color="#7170ff" />
              ) : (
                <Volume2 size={11} color="#8a8f98" />
              )}
            </button>
          )}
        </div>
        <div
          className="glass-bubble"
          style={{
            borderRadius: '2px 8px 8px 8px',
            padding: '13px 18px',
            fontSize: '14px', color: '#d0d6e0', lineHeight: 1.6,
            fontWeight: 400,
            wordBreak: 'break-word',
          }}
        >
          {audioSrc && <AudioBar src={audioSrc} />}
          {(message.toolCalls?.length || message.openCodeSteps?.length) ? (
            <OpenCodeMessage message={message} />
          ) : (
            <>
              <MarkdownRenderer content={message.text} />
              {message.isStreaming && (
                <span style={{
                  display: 'inline-block', width: '2px', height: '14px',
                  background: 'var(--accent)', marginLeft: '2px',
                  animation: 'blink 1s step-end infinite', verticalAlign: 'text-bottom',
                }} />
              )}
            </>
          )}
        </div>
      </div>
      <style>{`
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </motion.div>
  );
}
