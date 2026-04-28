'use client';
import { KeyboardEvent, useRef, useState, useEffect } from 'react';
import { ArrowUp, Mic, Square, Loader2, Phone, PhoneOff, Keyboard, KeyboardOff } from 'lucide-react';
import { startVoiceRecording, stopVoiceRecording, transcribeAudio } from '@/services/voice';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import { useIsMobile } from '@/hooks/useIsMobile';
import { useIsIOS } from '@/hooks/useIsIOS';
import CustomKeyboardSheet from '@/components/keyboard/CustomKeyboardSheet';

// Persisted globally across all terminal tabs (and across reloads). Default ON
// since the custom keyboard is the only input source on mobile.
const KB_PREF_KEY = 'neuro.terminal.customKeyboardOpen';
const readKbPref = (): boolean => {
  if (typeof window === 'undefined') return true;
  const v = window.localStorage.getItem(KB_PREF_KEY);
  return v === null ? true : v === '1';
};
const writeKbPref = (open: boolean) => {
  try { window.localStorage.setItem(KB_PREF_KEY, open ? '1' : '0'); } catch {}
};

interface Props {
  /**
   * Called with raw text (no trailing newline). Parent appends `\n`.
   * Should return true if the data was actually sent (WS open). Returning
   * false (or void) tells the input bar to keep `value` intact so the user
   * can retry once the WS recovers.
   */
  onSubmit: (text: string) => boolean | void;
  disabled?: boolean;
  placeholder?: string;
  /** If true, pressing Enter after a voice transcript is auto-submitted. */
  autoSubmitVoice?: boolean;
}

export default function TerminalInputBar({ onSubmit, disabled, placeholder, autoSubmitVoice }: Props) {
  const [value, setValue] = useState('');
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const isMobile = useIsMobile();
  const isIOS = useIsIOS();
  // Custom keyboard visibility is persisted globally across all terminals
  // (localStorage). User can toggle via the keyboard button in the input bar;
  // preference survives reloads and applies to every terminal tab.
  const [kbOpen, setKbOpenState] = useState(() => isMobile && readKbPref());
  const setKbOpen = (v: boolean) => {
    setKbOpenState(v);
    if (isMobile) writeKbPref(v);
  };
  // Cross-tab sync: when another terminal toggles the keyboard, mirror it here.
  useEffect(() => {
    if (!isMobile) return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === KB_PREF_KEY && e.newValue !== null) {
        setKbOpenState(e.newValue === '1');
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [isMobile]);
  const [modifiers, setModifiers] = useState({ ctrl: false, alt: false, shift: false });
  const ref = useRef<HTMLTextAreaElement>(null);
  const { startCall, endCall, isActive: callActive, connecting: callConnecting } = useVoiceCall();

  const [sendError, setSendError] = useState(false);
  const submit = (text?: string) => {
    const t = (text ?? value).trim();
    if (!t) return;
    const ok = onSubmit(t);
    // If the parent returned `false`, the WebSocket wasn't open and the data
    // never left the browser. Keep `value` so the user can retry — clearing
    // it would silently lose their command.
    if (ok === false) {
      setSendError(true);
      setTimeout(() => setSendError(false), 1500);
      return;
    }
    setValue('');
    if (!isIOS && !isMobile) setTimeout(() => ref.current?.focus(), 0);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // Custom keyboard key handler — used on mobile in lieu of native keyboard.
  const handleCustomKey = (combo: string) => {
    if (combo === 'Return') { submit(); return; }
    if (combo === 'BackSpace') { setValue(v => v.slice(0, -1)); return; }
    if (combo === 'Tab') { setValue(v => v + '\t'); return; }
    if (combo === 'space') { setValue(v => v + ' '); return; }
    if (combo === 'Escape') { setValue(''); return; }
    if (combo.length === 1) {
      // Single character — apply shift if active for letters
      const ch = modifiers.shift && /[a-z]/.test(combo) ? combo.toUpperCase() : combo;
      setValue(v => v + ch);
      return;
    }
    // F-keys, arrows, combos like "ctrl+c" are out of scope for line-based input.
    // Silently ignore — could route to PTY raw-send in a future task.
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
        const next = value ? `${value} ${text}` : text;
        setValue(next);
        if (!isMobile) ref.current?.focus();
      }
    } catch (err: any) {
      console.error('[terminal] transcribe failed:', err?.message || err);
      setTranscribing(false);
    }
  };

  return (
    <>
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 8,
        padding: '8px 12px',
        paddingBottom: isMobile ? 'max(env(safe-area-inset-bottom), 8px)' : '8px',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        background: 'rgba(15, 16, 17, 0.8)',
        flexShrink: 0,
      }}>
        <div style={{
          flex: 1, minWidth: 0,
          background: sendError ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.03)',
          border: '1px solid ' + (sendError ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.08)'),
          borderRadius: 8, padding: '6px 10px',
          display: 'flex', alignItems: 'flex-end', gap: 6,
          transition: 'background 0.15s, border-color 0.15s',
        }}>
          <span style={{
            color: '#7170ff', fontFamily: "'Berkeley Mono', ui-monospace, monospace",
            fontSize: 13, lineHeight: '20px', flexShrink: 0, userSelect: 'none',
          }}>$</span>
          {isMobile ? (
            // Mobile: pure display div, never focusable. The custom keyboard
            // is the *only* input source. We deliberately avoid <textarea>
            // here because Android browsers will pop the native keyboard on
            // focus regardless of `readOnly` + `inputMode='none'`, and any
            // typing on that native keyboard never reaches React state
            // (readOnly suppresses onChange) — so a stray native ↵ would
            // call submit() with empty value and clear the visible text.
            <div
              data-terminal-input
              style={{
                flex: 1, minWidth: 0,
                color: '#f7f8f8',
                fontSize: 16, lineHeight: '20px',
                fontFamily: "'Berkeley Mono', ui-monospace, monospace",
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                maxHeight: 160,
                overflow: 'auto',
                userSelect: 'none',
                WebkitUserSelect: 'none',
                pointerEvents: 'none',
              }}
            >
              {value
                ? <>{value}<span style={{
                    display: 'inline-block', width: 1, height: 16,
                    background: '#7170ff', marginLeft: 1, verticalAlign: 'middle',
                    animation: 'termCaret 1s steps(1) infinite',
                  }} /></>
                : <span style={{ color: 'rgba(255,255,255,0.3)' }}>
                    {placeholder || 'Tap keys below to type a command'}
                  </span>}
            </div>
          ) : (
            <textarea
              ref={ref}
              data-terminal-input
              value={value}
              placeholder={placeholder || 'Type a command, Enter to send'}
              onChange={e => setValue(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={disabled}
              rows={1}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="none"
              spellCheck={false}
              enterKeyHint="send"
              style={{
                flex: 1, minWidth: 0,
                background: 'transparent', border: 'none', outline: 'none',
                color: '#f7f8f8',
                fontSize: 16, lineHeight: '20px',
                fontFamily: "'Berkeley Mono', ui-monospace, monospace",
                resize: 'none', padding: 0,
                maxHeight: 160,
                caretColor: '#7170ff',
              }}
            />
          )}
        </div>
        {isMobile && (
          <button
            onPointerDown={(e) => { e.preventDefault(); setKbOpen(!kbOpen); }}
            title={kbOpen ? 'Hide keyboard' : 'Show keyboard'}
            style={{
              width: 32, height: 32, borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: kbOpen ? 'rgba(94,106,210,0.2)' : 'rgba(255,255,255,0.04)',
              border: '1px solid ' + (kbOpen ? 'rgba(94,106,210,0.4)' : 'rgba(255,255,255,0.08)'),
              color: kbOpen ? '#c4b5fd' : '#8a8f98',
              cursor: 'pointer', flexShrink: 0,
            }}
          >
            {kbOpen ? <KeyboardOff size={14} /> : <Keyboard size={14} />}
          </button>
        )}
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

      {isMobile && (
        <CustomKeyboardSheet
          open={kbOpen}
          variant="inline"
          onKey={handleCustomKey}
          modifiers={modifiers}
          onToggleModifier={(m) => setModifiers(s => ({ ...s, [m]: !s[m] }))}
          onClearModifiers={() => setModifiers({ ctrl: false, alt: false, shift: false })}
        />
      )}
    </>
  );
}
