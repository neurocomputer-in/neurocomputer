'use client';
import React, { useEffect, useRef, useCallback } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { useAppSelector } from '@/store/hooks';
import { useTerminalWs } from '@/hooks/useTerminalWs';
import { useActiveCid } from '@/components/os/WindowContext';
import MobileKeyBar from './MobileKeyBar';
import TerminalInputBar from './TerminalInputBar';
import TerminalScrollbar from './TerminalScrollbar';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';
import { useIsMobile } from '@/hooks/useIsMobile';

export default function TerminalPanel() {
  const paneCid   = useActiveCid();
  const globalCid = useAppSelector(s => s.conversations.activeTabCid);
  const activeCid = paneCid ?? globalCid;
  const tab       = useAppSelector(s =>
    s.conversations.openTabs.find(t => t.cid === activeCid) || null);
  const wsStatus  = useAppSelector(s =>
    activeCid ? (s.terminal.wsStatus[activeCid] || 'idle') : 'idle');

  const containerRef = useRef<HTMLDivElement | null>(null);
  const termRef      = useRef<Terminal | null>(null);
  const fitRef       = useRef<FitAddon | null>(null);
  const isMobile     = useIsMobile();

  const sendRef        = useRef<((d: ArrayBuffer | Uint8Array | string) => void) | null>(null);
  const sendControlRef = useRef<((p: Record<string, unknown>) => void) | null>(null);
  const resizeRef      = useRef<((c: number, r: number) => void) | null>(null);
  const pendingFitRef  = useRef(false);

  // ── xterm mount ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || !activeCid) return;

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "'Berkeley Mono', ui-monospace, Menlo, monospace",
      fontSize: isMobile ? 13 : 13,
      theme: { background: '#0a0a0b', foreground: '#d0d6e0' },
      scrollback: 10000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new WebLinksAddon());
    term.open(containerRef.current);
    try { fit.fit(); } catch { /**/ }
    termRef.current = term;
    fitRef.current  = fit;

    term.onData(d => sendRef.current?.(new TextEncoder().encode(d).buffer));

    const onResize = () => {
      // On mobile, skip fit() while the input textarea is focused. Otherwise the
      // canvas redraw can steal focus → keyboard snaps shut. We re-fit once the
      // user blurs the input (focusout listener below).
      if (isMobile) {
        const ae = document.activeElement as HTMLElement | null;
        if (ae && ae.tagName === 'TEXTAREA' && !ae.classList.contains('xterm-helper-textarea')) {
          pendingFitRef.current = true;
          return;
        }
      }
      try { fit.fit(); resizeRef.current?.(term.cols, term.rows); } catch { /**/ }
    };
    // ResizeObserver covers all real layout changes (orientation, window resize,
    // container resize). We intentionally omit window/visualViewport resize
    // listeners because on mobile those fire when the keyboard opens, causing
    // fit.fit() to redraw the xterm canvas which blurs the focused input.
    const ro = new ResizeObserver(onResize);
    ro.observe(containerRef.current);

    // When the input textarea blurs, run any deferred fit.
    const onFocusOut = (e: FocusEvent) => {
      const t = e.target as HTMLElement | null;
      if (t?.tagName === 'TEXTAREA' && !t.classList.contains('xterm-helper-textarea') && pendingFitRef.current) {
        pendingFitRef.current = false;
        try { fit.fit(); resizeRef.current?.(term.cols, term.rows); } catch {}
      }
    };
    document.addEventListener('focusout', onFocusOut);

    return () => {
      ro.disconnect();
      document.removeEventListener('focusout', onFocusOut);
      termRef.current = null;
      fitRef.current  = null;
      const t = term;
      setTimeout(() => { try { t.dispose(); } catch { /**/ } }, 0);
    };
  // intentionally exclude isMobile — no reason to remount xterm on breakpoint change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCid]);

  // Mobile touch overlay — gesture state stored in refs so React event
  // handlers close over stable refs, not stale closure values.
  const PX_PER_LINE = 22;
  const THRESHOLD   = 6;
  const TAP_MS      = 280;

  const gestureRef = useRef({
    active: false,
    startX: 0, startY: 0, lastY: 0, startT: 0,
    dragging: false,
    pxAccum: 0,
  });
  const flushTimerRef = useRef<number | null>(null);
  const pendingLinesRef = useRef(0);

  const flushScroll = useCallback(() => {
    const n = pendingLinesRef.current;
    if (n !== 0) {
      sendControlRef.current?.({
        type: 'tmux-scroll',
        action: n > 0 ? 'up' : 'down',
        count: Math.abs(n),
      });
      pendingLinesRef.current = 0;
    }
    flushTimerRef.current = null;
  }, []);

  const scheduleFlush = useCallback(() => {
    if (flushTimerRef.current == null) {
      flushTimerRef.current = window.setTimeout(flushScroll, 30) as unknown as number;
    }
  }, [flushScroll]);

  const onOverlayDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse') return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const g = gestureRef.current;
    g.active   = true;
    g.startX   = e.clientX;
    g.startY   = e.clientY;
    g.lastY    = e.clientY;
    g.startT   = performance.now();
    g.dragging = false;
    g.pxAccum  = 0;
    pendingLinesRef.current = 0;
  }, []);

  const onOverlayMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse') return;
    const g = gestureRef.current;
    if (!g.active) return;

    const dy = e.clientY - g.lastY;
    g.lastY = e.clientY;

    if (!g.dragging) {
      if (Math.hypot(e.clientX - g.startX, e.clientY - g.startY) < THRESHOLD) return;
      g.dragging = true;
    }

    e.preventDefault();
    // Finger DOWN (dy>0) → reveal older content → scroll UP
    g.pxAccum += dy;
    while (g.pxAccum >=  PX_PER_LINE) { pendingLinesRef.current += 1; g.pxAccum -= PX_PER_LINE; }
    while (g.pxAccum <= -PX_PER_LINE) { pendingLinesRef.current -= 1; g.pxAccum += PX_PER_LINE; }
    if (pendingLinesRef.current !== 0) scheduleFlush();
  }, [scheduleFlush]);

  const onOverlayUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse') return;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    const g = gestureRef.current;
    if (!g.active) return;
    g.active = false;

    if (!g.dragging && performance.now() - g.startT < TAP_MS) {
      if (!isMobile) {
        // Desktop: focus xterm so keyboard events reach it directly.
        termRef.current?.focus();
      }
      // Mobile: custom keyboard is always visible — do NOT focus the textarea.
      // Focusing it would bring up the native Android keyboard, causing native
      // keyboard ↵ to fire onKeyDown with empty React state (textarea is
      // readOnly so native typing never updates React state) and vanish input.
    } else if (g.dragging) {
      if (flushTimerRef.current != null) { clearTimeout(flushTimerRef.current); flushTimerRef.current = null; }
      flushScroll();
    }
    g.dragging = false;
    g.pxAccum  = 0;
  }, [flushScroll]);

  // ── WS wiring ────────────────────────────────────────────────────────────────
  const onBinary = useCallback((buf: ArrayBuffer) => {
    termRef.current?.write(new Uint8Array(buf));
  }, []);
  const onExit = useCallback((code: number) => {
    termRef.current?.writeln(`\r\n\x1b[33m[session ended, code=${code}]\x1b[0m`);
  }, []);

  const { send, sendControl, resize } = useTerminalWs(activeCid, onBinary, onExit);
  sendRef.current        = send;
  sendControlRef.current = sendControl;
  resizeRef.current      = resize;

  useEffect(() => {
    if (wsStatus === 'ready' && termRef.current) {
      resize(termRef.current.cols, termRef.current.rows);
    }
  }, [wsStatus, resize]);

  const sendKey  = (seq: string) => { send(new TextEncoder().encode(seq).buffer); };
  // Use CR (\r), not LF (\n). Real keyboards send \r when Enter is pressed.
  // Shells in cooked mode translate \r → run-command via ICRNL, so they
  // accept either. But TUIs running in raw mode (Claude Code CLI, opencode,
  // vim insert mode, etc.) read \r as Enter and treat \n as just-a-newline
  // — so submitting "hello\n" to Claude CLI inserts a newline into its
  // multi-line input box without ever submitting. \r fixes that.
  const sendLine = (line: string): boolean => send(new TextEncoder().encode(line + '\r').buffer);

  if (!tab || tab.type !== 'terminal') return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1,
                  background: '#0a0a0b', overflow: 'hidden', minHeight: 0 }}>

      {/* title bar */}
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

      {/* xterm + touch overlay + visible scrollbar (mobile).
          Row layout: [xterm area (flex:1)] [scrollbar (fixed width)].
          xterm area itself is position:relative so the touch overlay can
          sit on top via position:absolute. */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'row' }}>
        <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
          <div
            ref={containerRef}
            className="neuro-term-mount"
            style={{
              position: 'absolute', inset: 0,
              padding: isMobile ? '2px' : '4px 6px',
              overscrollBehavior: 'contain',
            }}
          />
          {isMobile && (
            <div
              onPointerDown={onOverlayDown}
              onPointerMove={onOverlayMove}
              onPointerUp={onOverlayUp}
              onPointerCancel={onOverlayUp}
              // Prevent synthesized mousedown/click events from reaching the
              // xterm canvas beneath. Without this, xterm's internal mousedown
              // listener calls its helper textarea's focus() which blurs our
              // visible textarea and dismisses the iOS keyboard.
              onMouseDown={e => e.stopPropagation()}
              onClick={e => e.stopPropagation()}
              style={{
                position: 'absolute', inset: 0, zIndex: 2,
                touchAction: 'none',
                background: 'transparent',
                WebkitTapHighlightColor: 'transparent',
              }}
            />
          )}
        </div>
        {isMobile && <TerminalScrollbar sendControl={sendControl} />}
      </div>

      {isMobile && <MobileKeyBar onKey={sendKey} />}
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
