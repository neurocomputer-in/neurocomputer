import { useEffect, useRef, useCallback } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setWsStatus } from '@/store/terminalSlice';
import { terminalWsUrl } from '@/services/api';

export interface TerminalWsHandle {
  /** Returns true if the data was actually sent over an OPEN socket. */
  send: (data: ArrayBuffer | Uint8Array | string) => boolean;
  sendControl: (payload: Record<string, unknown>) => void;
  resize: (cols: number, rows: number) => void;
  close: () => void;
}

export function useTerminalWs(
  cid: string | null,
  onBinary: (b: ArrayBuffer) => void,
  onExit?: (code: number) => void,
): TerminalWsHandle {
  const dispatch = useAppDispatch();
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const shouldReconnectRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onBinaryRef = useRef(onBinary);
  const onExitRef = useRef(onExit);

  useEffect(() => { onBinaryRef.current = onBinary; }, [onBinary]);
  useEffect(() => { onExitRef.current = onExit; }, [onExit]);

  const connect = useCallback(() => {
    if (!cid) return;
    // Close any prior socket before opening a new one. Without this, a
    // half-open socket whose onclose hasn't fired yet would be silently
    // abandoned and stay alive on the server, leaking a PtyBridge per
    // reconnect cycle. After enough reconnects, the server holds N parallel
    // tmux attaches against the same session and stdin routing gets racey.
    const prior = wsRef.current;
    if (prior) {
      try {
        prior.onopen = null; prior.onmessage = null;
        prior.onerror = null; prior.onclose = null;
        prior.close();
      } catch { /* no-op */ }
    }

    const ws = new WebSocket(terminalWsUrl(cid));
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;
    dispatch(setWsStatus({ cid, status: 'connecting' }));

    ws.onopen = () => {
      backoffRef.current = 1000;
      // wait for server-sent {"type":"ready"} before marking ready
    };
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'ready') {
            dispatch(setWsStatus({ cid, status: 'ready' }));
          } else if (msg.type === 'exit') {
            onExitRef.current?.(msg.code ?? 0);
          } else if (msg.type === 'error') {
            console.warn('[terminal] server error:', msg.msg);
            dispatch(setWsStatus({ cid, status: 'error' }));
          }
        } catch {
          /* ignore malformed JSON */
        }
        return;
      }
      if (ev.data instanceof ArrayBuffer) {
        onBinaryRef.current(ev.data);
      } else if (ev.data instanceof Blob) {
        ev.data.arrayBuffer().then((b) => onBinaryRef.current(b));
      }
    };
    ws.onclose = () => {
      // Crucial: if a *previous* (orphaned) socket fires onclose, ignore it.
      // Reconnecting from a stale close handler would replace the healthy
      // current socket with a brand-new one and avalanche the server with
      // duplicate attaches.
      if (wsRef.current !== ws) return;
      wsRef.current = null;
      if (!shouldReconnectRef.current) return;
      dispatch(setWsStatus({ cid, status: 'reconnecting' }));
      reconnectTimerRef.current = setTimeout(() => {
        backoffRef.current = Math.min(backoffRef.current * 2, 10000);
        connect();
      }, backoffRef.current);
    };
    ws.onerror = () => {
      try { ws.close(); } catch { /* no-op */ }
    };
  }, [cid, dispatch]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      try { wsRef.current?.close(); } catch { /* no-op */ }
      wsRef.current = null;
    };
  }, [connect]);

  const send = useCallback((data: ArrayBuffer | Uint8Array | string): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('[terminal-ws] send dropped — wsState=', ws?.readyState);
      // Do NOT trigger a reconnect here. The natural onclose-driven reconnect
      // is enough; piling on extra connect() calls from send() was creating
      // a thundering herd of orphan WS connections on the server (each one
      // holding a tmux attach against the same session).
      return false;
    }
    try {
      if (typeof data === 'string') {
        ws.send(new TextEncoder().encode(data));
      } else {
        ws.send(data);
      }
      return true;
    } catch (e) {
      console.warn('[terminal-ws] send threw', e);
      return false;
    }
  }, []);

  const resize = useCallback((cols: number, rows: number) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'resize', cols, rows }));
  }, []);

  const sendControl = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    const state = ws?.readyState;
    console.log('[terminal-ws] sendControl', payload, 'wsState=', state);
    if (!ws || state !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(payload));
  }, []);

  const close = useCallback(() => {
    shouldReconnectRef.current = false;
    try { wsRef.current?.close(); } catch { /* no-op */ }
  }, []);

  return { send, sendControl, resize, close };
}
