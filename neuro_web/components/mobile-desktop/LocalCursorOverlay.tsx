'use client';
import { useEffect, useRef } from 'react';
import { useLocalCursor } from './LocalCursorContext';

/**
 * Renders an arrow at the local cursor position. Uses imperative DOM updates
 * (transform) inside the subscribe callback so position updates don't trigger
 * React re-renders — keeps the cursor smooth at 60fps with no GC churn.
 */
export default function LocalCursorOverlay() {
  const { posRef, visibleRef, subscribe } = useLocalCursor();
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const apply = () => {
      const { x, y } = posRef.current;
      el.style.transform = `translate3d(${x - 4}px, ${y - 2}px, 0)`;
      el.style.opacity = visibleRef.current ? '1' : '0';
    };
    apply();
    return subscribe(apply);
  }, [posRef, visibleRef, subscribe]);

  return (
    <div
      ref={elRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: 0,
        height: 0,
        zIndex: 21,
        pointerEvents: 'none',
        opacity: 0,
        transition: 'opacity 0.15s',
        willChange: 'transform',
      }}
    >
      {/* Classic arrow cursor — 18×18 SVG, white fill + black outline so it
          stands out on any wallpaper. */}
      <svg width="18" height="18" viewBox="0 0 18 18" style={{ display: 'block' }}>
        <path
          d="M2 1 L2 14 L5.5 11 L7.5 16 L10 15 L8 10 L13 10 Z"
          fill="#fff"
          stroke="#000"
          strokeWidth="1"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
