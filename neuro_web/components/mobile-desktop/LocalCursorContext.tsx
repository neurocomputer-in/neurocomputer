'use client';
import { createContext, useContext, useRef, useCallback, ReactNode, MutableRefObject } from 'react';

/**
 * Local cursor — rendered on the mobile side WITHOUT waiting for server feedback.
 * Touch overlays update this position (immediate visual response). The cursor
 * is rendered by LocalCursorOverlay and synced loosely with the server cursor
 * (the server cursor is authoritative but lags behind by network RTT).
 *
 * Stored in refs (not React state) because touch updates fire 60+ times/sec —
 * re-rendering on every move would tank performance. The overlay subscribes
 * via animation-frame loop instead.
 */
interface CursorPos { x: number; y: number; }

interface LocalCursorAPI {
  /** Current position ref — read-only for consumers. */
  posRef: MutableRefObject<CursorPos>;
  /** Visibility ref — false hides the overlay. */
  visibleRef: MutableRefObject<boolean>;
  /** Set absolute position. */
  setPos: (x: number, y: number) => void;
  /** Move by delta. Clamps to container bounds. */
  movePos: (dx: number, dy: number, container: { w: number; h: number }) => void;
  /** Subscribe to position updates — returns unsubscribe. */
  subscribe: (cb: () => void) => () => void;
}

const noopRef = { current: { x: 0, y: 0 } } as MutableRefObject<CursorPos>;
const noopVis = { current: false } as MutableRefObject<boolean>;

const LocalCursorContext = createContext<LocalCursorAPI>({
  posRef: noopRef,
  visibleRef: noopVis,
  setPos: () => {},
  movePos: () => {},
  subscribe: () => () => {},
});

export function LocalCursorProvider({ children }: { children: ReactNode }) {
  const posRef = useRef<CursorPos>({ x: 100, y: 100 });
  const visibleRef = useRef<boolean>(false);
  const subsRef = useRef<Set<() => void>>(new Set());

  const notify = useCallback(() => {
    for (const cb of subsRef.current) cb();
  }, []);

  const setPos = useCallback((x: number, y: number) => {
    posRef.current = { x, y };
    visibleRef.current = true;
    notify();
  }, [notify]);

  const movePos = useCallback((dx: number, dy: number, container: { w: number; h: number }) => {
    const next = {
      x: Math.max(0, Math.min(container.w, posRef.current.x + dx)),
      y: Math.max(0, Math.min(container.h, posRef.current.y + dy)),
    };
    posRef.current = next;
    visibleRef.current = true;
    notify();
  }, [notify]);

  const subscribe = useCallback((cb: () => void) => {
    subsRef.current.add(cb);
    return () => { subsRef.current.delete(cb); };
  }, []);

  return (
    <LocalCursorContext.Provider value={{ posRef, visibleRef, setPos, movePos, subscribe }}>
      {children}
    </LocalCursorContext.Provider>
  );
}

export function useLocalCursor() {
  return useContext(LocalCursorContext);
}
