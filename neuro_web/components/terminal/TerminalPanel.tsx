'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { useAppSelector } from '@/store/hooks';
import { useTerminalWs } from '@/hooks/useTerminalWs';
import { usePaneCid } from '@/components/panes/PaneContext';
import MobileKeyBar from './MobileKeyBar';
import TerminalInputBar from './TerminalInputBar';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';

export default function TerminalPanel() {
  // Prefer the pane-scoped cid when rendered inside a PaneFrame; fall
  // back to the global activeTabCid so legacy mount sites (tests, etc.)
  // still work.
  const paneCid = usePaneCid();
  const globalCid = useAppSelector(s => s.conversations.activeTabCid);
  const activeCid = paneCid ?? globalCid;
  const tab = useAppSelector(s =>
    s.conversations.openTabs.find(t => t.cid === activeCid) || null);
  const wsStatus = useAppSelector(s =>
    activeCid ? (s.terminal.wsStatus[activeCid] || 'idle') : 'idle');

  const containerRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const [mobile, setMobile] = useState(false);

  // Stable refs for the WS send/resize functions so the mount-effect
  // below can depend only on `activeCid`.
  const sendRef = useRef<((d: ArrayBuffer | Uint8Array | string) => void) | null>(null);
  const resizeRef = useRef<((c: number, r: number) => void) | null>(null);

  // 1. Mount xterm (per cid)
  useEffect(() => {
    if (!containerRef.current || !activeCid) return;
    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "'Berkeley Mono', ui-monospace, Menlo, monospace",
      fontSize: 13,
      theme: { background: '#0a0a0b', foreground: '#d0d6e0' },
      scrollback: 10000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new WebLinksAddon());
    // Canvas renderer only (default). xterm-addon-webgl causes
    // "onRequestRedraw on undefined" races during React unmount; the
    // extra perf isn't worth the lifecycle fragility here.
    term.open(containerRef.current);
    try { fit.fit(); } catch { /* container may be 0×0 briefly */ }
    termRef.current = term;
    fitRef.current = fit;

    term.onData(d => {
      sendRef.current?.(new TextEncoder().encode(d).buffer);
    });

    const onResize = () => {
      try {
        fit.fit();
        resizeRef.current?.(term.cols, term.rows);
      } catch { /* no-op */ }
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(containerRef.current);
    window.addEventListener('resize', onResize);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', onResize);
      termRef.current = null;
      fitRef.current = null;
      // Defer dispose to next tick so any in-flight xterm rAF callbacks
      // can finish against the still-live DOM instead of crashing on a
      // half-torn-down renderer.
      const t = term;
      setTimeout(() => { try { t.dispose(); } catch { /* no-op */ } }, 0);
    };
  }, [activeCid]);

  // 2. Viewport breakpoint
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)');
    const on = () => setMobile(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  // 3. WS wiring — stable callbacks via refs
  const onBinary = useCallback((buf: ArrayBuffer) => {
    termRef.current?.write(new Uint8Array(buf));
  }, []);
  const onExit = useCallback((code: number) => {
    termRef.current?.writeln(`\r\n\x1b[33m[session ended, code=${code}]\x1b[0m`);
  }, []);

  const { send, resize } = useTerminalWs(activeCid, onBinary, onExit);
  sendRef.current = send;
  resizeRef.current = resize;

  // 4. Push initial size once ready
  useEffect(() => {
    if (wsStatus === 'ready' && termRef.current) {
      resize(termRef.current.cols, termRef.current.rows);
    }
  }, [wsStatus, resize]);

  const sendKey = (seq: string) => {
    send(new TextEncoder().encode(seq).buffer);
  };

  const sendLine = (line: string) => {
    // Append \n so the line actually executes. Callers pass raw text.
    send(new TextEncoder().encode(line + '\n').buffer);
  };

  if (!tab || tab.type !== 'terminal') return null;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', flex: 1,
      background: '#0a0a0b', overflow: 'hidden', minHeight: 0,
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        color: '#62666d', fontSize: '11px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <span style={{ fontFamily: 'monospace', overflow: 'hidden',
                       textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tab.tmuxSession || '—'}
        </span>
        <span>{statusLabel(wsStatus)}</span>
      </div>
      <div ref={containerRef}
           style={{ flex: 1, minHeight: 0, padding: '4px 6px' }} />
      {mobile && <MobileKeyBar onKey={sendKey} />}
      <VoiceCallPanel />
      <TerminalInputBar
        onSubmit={sendLine}
        disabled={wsStatus !== 'ready'}
        placeholder={wsStatus === 'ready'
          ? 'Type a command, Enter to send'
          : `waiting for ${wsStatus}…`}
      />
    </div>
  );
}

function statusLabel(s: string | undefined) {
  switch (s) {
    case 'ready':        return 'connected';
    case 'connecting':   return 'connecting…';
    case 'reconnecting': return 'reconnecting…';
    case 'error':        return 'error';
    default:             return '';
  }
}
