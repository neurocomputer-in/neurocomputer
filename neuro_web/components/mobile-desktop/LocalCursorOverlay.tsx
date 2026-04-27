'use client';
import { useEffect, useRef } from 'react';
import { useLocalCursor } from './LocalCursorContext';
import { useLetterbox } from './LetterboxContext';

/**
 * Renders the classic arrow at the local cursor position, top-left hot-spot
 * mode. Uses imperative DOM updates (transform) inside the subscribe callback
 * so position updates don't trigger React re-renders — keeps the cursor smooth
 * at 60fps with no GC churn.
 *
 * Pixel mapping (mirrors Kotlin's `CursorArrowOverlay`):
 *   px = letterbox.offsetX + cursor.nx * letterbox.drawW
 *   py = letterbox.offsetY + cursor.ny * letterbox.drawH
 * The SVG's path is drawn so the arrow tip is at (0,0) of the SVG, so we
 * translate the host element directly to (px, py) — no offset adjustment.
 */
export default function LocalCursorOverlay() {
  const { posRef, visibleRef, subscribe } = useLocalCursor();
  const lb = useLetterbox();
  const lbRef = useRef(lb);
  lbRef.current = lb;
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const apply = () => {
      const { nx, ny } = posRef.current;
      const { offsetX, offsetY, drawW, drawH } = lbRef.current;
      const px = offsetX + nx * drawW;
      const py = offsetY + ny * drawH;
      el.style.transform = `translate3d(${px}px, ${py}px, 0)`;
      el.style.opacity = visibleRef.current ? '1' : '0';
    };
    apply();
    return subscribe(apply);
  }, [posRef, visibleRef, subscribe]);

  // Re-apply when the letterbox changes (orientation / fullscreen toggle) so
  // the cursor doesn't jump off-target on resize.
  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const { nx, ny } = posRef.current;
    const px = lb.offsetX + nx * lb.drawW;
    const py = lb.offsetY + ny * lb.drawH;
    el.style.transform = `translate3d(${px}px, ${py}px, 0)`;
  }, [lb, posRef]);

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
      {/* Arrow shape from Kotlin's path — tip at (0,0), 20px nominal size.
          White fill + 2.5px black stroke so it stands out on any wallpaper. */}
      <svg width="20" height="20" viewBox="0 0 20 20" style={{ display: 'block', overflow: 'visible' }}>
        <path
          d="M 0 0 L 0 20 L 6 12.4 L 10.8 19.6 L 14 17.6 L 9.2 11.2 L 15.6 8.8 Z"
          fill="#ffffff"
          stroke="#000000"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
