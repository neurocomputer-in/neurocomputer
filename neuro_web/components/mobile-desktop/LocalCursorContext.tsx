'use client';
import { createContext, useContext, useRef, useCallback, ReactNode, MutableRefObject } from 'react';

/**
 * Local cursor — normalized PC coordinates (0..1, 0..1), exactly matching the
 * Kotlin app's CursorArrowOverlay so the arrow tip lines up pixel-for-pixel
 * with where the server is moving the actual mouse.
 *
 * Positions are stored in refs (not React state) because touch updates fire
 * 60+ times/sec; re-rendering on every move would tank performance. Subscribers
 * are notified via a tiny pub-sub and pull the value imperatively.
 */
interface CursorPos {
  /** Normalized PC x in [0,1]. */
  nx: number;
  /** Normalized PC y in [0,1]. */
  ny: number;
}

interface LocalCursorAPI {
  posRef: MutableRefObject<CursorPos>;
  visibleRef: MutableRefObject<boolean>;
  /** Set absolute normalized position. Clamped to [0,1]. */
  setNorm: (nx: number, ny: number) => void;
  /** Subscribe to position updates — returns unsubscribe. */
  subscribe: (cb: () => void) => () => void;
}

const noopRef = { current: { nx: 0.5, ny: 0.5 } } as MutableRefObject<CursorPos>;
const noopVis = { current: false } as MutableRefObject<boolean>;

const LocalCursorContext = createContext<LocalCursorAPI>({
  posRef: noopRef,
  visibleRef: noopVis,
  setNorm: () => {},
  subscribe: () => () => {},
});

const clamp01 = (v: number) => v < 0 ? 0 : v > 1 ? 1 : v;

export function LocalCursorProvider({ children }: { children: ReactNode }) {
  // Center of screen on first mount, matching Kotlin's `Offset(0.5f, 0.5f)`.
  const posRef = useRef<CursorPos>({ nx: 0.5, ny: 0.5 });
  const visibleRef = useRef<boolean>(false);
  const subsRef = useRef<Set<() => void>>(new Set());

  const notify = useCallback(() => {
    for (const cb of subsRef.current) cb();
  }, []);

  const setNorm = useCallback((nx: number, ny: number) => {
    posRef.current = { nx: clamp01(nx), ny: clamp01(ny) };
    visibleRef.current = true;
    notify();
  }, [notify]);

  const subscribe = useCallback((cb: () => void) => {
    subsRef.current.add(cb);
    return () => { subsRef.current.delete(cb); };
  }, []);

  return (
    <LocalCursorContext.Provider value={{ posRef, visibleRef, setNorm, subscribe }}>
      {children}
    </LocalCursorContext.Provider>
  );
}

export function useLocalCursor() {
  return useContext(LocalCursorContext);
}
