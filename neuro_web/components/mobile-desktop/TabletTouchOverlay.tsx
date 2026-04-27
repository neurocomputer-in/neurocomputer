'use client';
import { useRef, useCallback } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useLetterbox } from './LetterboxContext';
import { useLocalCursor } from './LocalCursorContext';

const LONG_PRESS_MS = 500;
const DOUBLE_TAP_INTERVAL = 350;
const MOVE_THRESHOLD_NX = 0.01;

/**
 * Tablet mode — absolute pointer. Cursor jumps to wherever the finger is, just
 * like the Kotlin TabletTouchOverlay. Wire format mirrors LiveKitService:
 *   touch_tap         — single + double (count=1|2)
 *   touch_long_press  — long-press at finger position
 *   touch_drag_start  — drag begin
 *   touch_drag_move   — drag move
 *   touch_drag_end    — drag end
 */
export default function TabletTouchOverlay() {
  const { sendControl } = useDesktopRoom();
  const lb = useLetterbox();
  const lbRef = useRef(lb);
  lbRef.current = lb;
  const cursor = useLocalCursor();

  const lastTapTimeRef = useRef(0);
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isDraggingRef = useRef(false);
  const longPressFiredRef = useRef(false);
  const pointerDownPosRef = useRef({ nx: 0, ny: 0 });
  const pointerIdRef = useRef<number | null>(null);

  const toNorm = useCallback((clientX: number, clientY: number) => {
    const { offsetX, offsetY, drawW, drawH } = lbRef.current;
    const nx = Math.max(0, Math.min(1, (clientX - offsetX) / Math.max(drawW, 1)));
    const ny = Math.max(0, Math.min(1, (clientY - offsetY) / Math.max(drawH, 1)));
    return { nx, ny };
  }, []);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (pointerIdRef.current !== null) return;
    pointerIdRef.current = e.pointerId;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    const { nx, ny } = toNorm(e.clientX, e.clientY);
    pointerDownPosRef.current = { nx, ny };
    isDraggingRef.current = false;
    longPressFiredRef.current = false;
    cursor.setNorm(nx, ny);

    longPressTimerRef.current = setTimeout(() => {
      longPressFiredRef.current = true;
      sendControl({ type: 'touch_long_press', nx, ny, count: 1 });
    }, LONG_PRESS_MS);
  }, [sendControl, cursor, toNorm]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    const { nx, ny } = toNorm(e.clientX, e.clientY);
    const dist = Math.hypot(nx - pointerDownPosRef.current.nx, ny - pointerDownPosRef.current.ny);
    cursor.setNorm(nx, ny);

    if (!isDraggingRef.current && dist > MOVE_THRESHOLD_NX) {
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current);
        longPressTimerRef.current = null;
      }
      isDraggingRef.current = true;
      sendControl({
        type: 'touch_drag_start',
        nx: pointerDownPosRef.current.nx,
        ny: pointerDownPosRef.current.ny,
      });
    }

    if (isDraggingRef.current) {
      sendControl({ type: 'touch_drag_move', nx, ny });
    }
  }, [sendControl, cursor, toNorm]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }

    const { nx, ny } = toNorm(e.clientX, e.clientY);

    if (isDraggingRef.current) {
      sendControl({ type: 'touch_drag_end', nx, ny });
      isDraggingRef.current = false;
      return;
    }

    // Long-press already fired → don't also send a tap.
    if (longPressFiredRef.current) {
      longPressFiredRef.current = false;
      return;
    }

    const now = Date.now();
    const isDouble = now - lastTapTimeRef.current < DOUBLE_TAP_INTERVAL;
    lastTapTimeRef.current = now;
    sendControl({ type: 'touch_tap', nx, ny, count: isDouble ? 2 : 1 });
  }, [sendControl, cursor, toNorm]);

  return (
    <div
      style={{ position: 'absolute', inset: 0, zIndex: 10, touchAction: 'none', WebkitUserSelect: 'none' }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    />
  );
}
