'use client';
import { KeyboardEvent, useRef, useState } from 'react';
import { ArrowUp, Mic, Square, Loader2, Phone, PhoneOff } from 'lucide-react';
import { startVoiceRecording, stopVoiceRecording, transcribeAudio } from '@/services/voice';
import { useVoiceCall } from '@/hooks/useVoiceCall';

interface Props {
  /** Called with raw text (no trailing newline). Parent appends `\n`. */
  onSubmit: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** If true, pressing Enter after a voice transcript is auto-submitted.
   *  Default false — user sees the transcript and can edit first. */
  autoSubmitVoice?: boolean;
}

/**
 * Minimal text input for sending into a terminal's stdin. Same visual
 * language as ChatInput but routes through whatever onSubmit the parent
 * supplies — phase 2 will extract a shared MessageInput and collapse these.
 */
export default function TerminalInputBar({ onSubmit, disabled, placeholder, autoSubmitVoice }: Props) {
  const [value, setValue] = useState('');
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const { startCall, endCall, isActive: callActive, connecting: callConnecting } = useVoiceCall();

  const submit = (text?: string) => {
    const t = (text ?? value).trim();
    if (!t) return;
    onSubmit(t);
    setValue('');
    setTimeout(() => ref.current?.focus(), 0);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onMicClick = async () => {
    if (disabled || transcribing) return;
    if (!recording) {
      try {
        await startVoiceRecording();
        setRecording(true);
      } catch (err: any) {
        console.error('[terminal] mic denied:', err?.message || err);
      }
      return;
    }
    // Stop + transcribe + prefill (or auto-submit).
    setRecording(false);
    setTranscribing(true);
    try {
      const blob = await stopVoiceRecording();
      if (!blob || blob.size === 0) {
        setTranscribing(false);
        return;
      }
      const text = (await transcribeAudio(blob)).trim();
      setTranscribing(false);
      if (!text) return;
      if (autoSubmitVoice) {
        submit(text);
      } else {
        // Append to whatever the user already has in the field.
        const next = value ? `${value} ${text}` : text;
        setValue(next);
        ref.current?.focus();
      }
    } catch (err: any) {
      console.error('[terminal] transcribe failed:', err?.message || err);
      setTranscribing(false);
    }
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: 8,
      padding: '8px 12px',
      borderTop: '1px solid rgba(255,255,255,0.05)',
      background: 'rgba(15, 16, 17, 0.8)',
      flexShrink: 0,
    }}>
      <div style={{
        flex: 1, minWidth: 0,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 8, padding: '6px 10px',
        display: 'flex', alignItems: 'flex-end', gap: 6,
      }}>
        <span style={{
          color: '#7170ff', fontFamily: "'Berkeley Mono', ui-monospace, monospace",
          fontSize: 13, lineHeight: '20px', flexShrink: 0, userSelect: 'none',
        }}>$</span>
        <textarea
          ref={ref}
          value={value}
          placeholder={placeholder || 'Type a command, Enter to send'}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={1}
          style={{
            flex: 1, minWidth: 0,
            background: 'transparent', border: 'none', outline: 'none',
            color: '#f7f8f8',
            fontSize: 13, lineHeight: '20px',
            fontFamily: "'Berkeley Mono', ui-monospace, monospace",
            resize: 'none', padding: 0,
            maxHeight: 160,
          }}
        />
      </div>
      <button
        onClick={callActive ? endCall : startCall}
        disabled={disabled || callConnecting}
        title={callActive ? 'End voice call' : 'Live voice → terminal stdin'}
        style={{
          width: 32, height: 32, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: callActive ? 'rgba(239,68,68,0.25)'
            : callConnecting ? 'rgba(94,106,210,0.15)'
            : 'rgba(255,255,255,0.04)',
          border: '1px solid ' + (callActive ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.08)'),
          color: callActive ? '#f87171' : callConnecting ? '#c4b5fd' : '#8a8f98',
          cursor: disabled || callConnecting ? 'default' : 'pointer',
          flexShrink: 0,
        }}
      >
        {callConnecting
          ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
          : callActive ? <PhoneOff size={14} /> : <Phone size={14} />}
      </button>
      <button
        onClick={onMicClick}
        disabled={disabled || transcribing}
        title={recording ? 'Stop & transcribe' : 'Voice input (dictation)'}
        style={{
          width: 32, height: 32, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: recording
            ? 'rgba(239,68,68,0.25)'
            : transcribing
              ? 'rgba(94,106,210,0.15)'
              : 'rgba(255,255,255,0.04)',
          border: '1px solid ' + (recording
            ? 'rgba(239,68,68,0.5)'
            : 'rgba(255,255,255,0.08)'),
          color: recording ? '#f87171' : transcribing ? '#c4b5fd' : '#8a8f98',
          cursor: disabled || transcribing ? 'default' : 'pointer',
          flexShrink: 0,
        }}
      >
        {transcribing ? (
          <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
        ) : recording ? (
          <Square size={14} />
        ) : (
          <Mic size={14} />
        )}
      </button>
      <button
        onClick={() => submit()}
        disabled={disabled || !value.trim()}
        title="Send to terminal stdin (Enter)"
        style={{
          width: 32, height: 32, borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: value.trim() ? 'rgba(94,106,210,0.2)' : 'rgba(255,255,255,0.04)',
          border: '1px solid ' + (value.trim() ? 'rgba(94,106,210,0.4)' : 'rgba(255,255,255,0.08)'),
          color: value.trim() ? '#c4b5fd' : '#62666d',
          cursor: value.trim() && !disabled ? 'pointer' : 'default',
          flexShrink: 0,
        }}
      >
        <ArrowUp size={14} />
      </button>
    </div>
  );
}
