'use client';
import { useRef, useCallback } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useAppSelector } from '@/store/hooks';
import { useLocalCursor } from './LocalCursorContext';
import { useLetterbox } from './LetterboxContext';

// Constants — exactly mirror Kotlin's TouchpadOverlay.kt so the cursor
// behaves identically across devices.
const MOVE_THRESHOLD = 3;             // px
const DOUBLE_TAP_INTERVAL = 350;      // ms
const TAP_CONFIRM_DELAY = 180;        // ms
const BASE_SENSITIVITY = 1.0;
const ACCEL_FACTOR = 0.18;
const ACCEL_POWER = 0.65;
const MAX_SENSITIVITY = 12.0;
const PC_SENS = 2.5;

/**
 * Touchpad mode — relative pointer with acceleration. Ports the Kotlin
 * algorithm 1:1 so the local cursor and the remote-actuated cursor stay
 * in sync within network latency.
 *
 * Wire format (matches Kotlin's `direct_*` family — backend's
 * mouse_controller dispatches these to absolute positions, no delta math
 * server-side):
 *   direct_move          {x, y}                         — absolute cursor
 *   direct_click         {x, y, button:'left',  count:1}
 *   direct_double_click  {x, y, button:'left',  count:2}
 *   direct_right_click   {x, y, button:'right', count:1}
 *   mousedown / mouseup  {button:'left'}                — for double-tap-and-drag
 *   scroll               {dy}                           — when scroll mode is on
 */
export default function TouchpadOverlay() {
  const { sendControl } = useDesktopRoom();
  const { scrollMode } = useAppSelector(s => s.mobileDesktop);
  const cursor = useLocalCursor();
  const lb = useLetterbox();
  const lbRef = useRef(lb);
  lbRef.current = lb;

  // Pointer/gesture state — refs because we read them inside async timers.
  const pointerIdRef = useRef<number | null>(null);
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const downPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Tap disambiguation:
  //   pointerDownCount + lastDownTime → tracks raw DOWNs to enable
  //     double-tap-and-drag (drag-mode kicks in if pointer goes down 2x in a row).
  //   tapCount + lastTapTime + pendingTapTimerRef → debounced single/double click.
  const pointerDownCountRef = useRef(0);
  const lastDownTimeRef = useRef(0);
  const tapCountRef = useRef(0);
  const lastTapTimeRef = useRef(0);
  const pendingTapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Drag state
  const isDraggingRef = useRef(false);     // true once movement crossed MOVE_THRESHOLD
  const isDragModeRef = useRef(false);     // true if double-tap initiated a drag (mousedown sent)
  const totalMovementRef = useRef(0);
  const longPressFiredRef = useRef(false); // skip tap-on-up if long-press already sent right-click

  const clearTapTimers = () => {
    if (pendingTapTimerRef.current) { clearTimeout(pendingTapTimerRef.current); pendingTapTimerRef.current = null; }
    if (longPressTimerRef.current) { clearTimeout(longPressTimerRef.current); longPressTimerRef.current = null; }
  };

  // Fire the pending tap (single or double) after the confirmation window.
  const flushPendingTap = useCallback(() => {
    pendingTapTimerRef.current = null;
    const count = Math.min(2, Math.max(1, tapCountRef.current));
    const { nx, ny } = cursor.posRef.current;
    if (count === 2) {
      sendControl({ type: 'direct_double_click', x: nx, y: ny, button: 'left', count: 2 });
    } else {
      sendControl({ type: 'direct_click', x: nx, y: ny, button: 'left', count: 1 });
    }
    tapCountRef.current = 0;
  }, [sendControl, cursor]);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (pointerIdRef.current !== null) return;
    pointerIdRef.current = e.pointerId;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    const now = Date.now();
    // Update raw DOWN counter — used to enable drag-mode on double-tap-and-hold.
    if (now - lastDownTimeRef.current < DOUBLE_TAP_INTERVAL) {
      pointerDownCountRef.current += 1;
    } else {
      pointerDownCountRef.current = 1;
    }
    lastDownTimeRef.current = now;

    downPosRef.current = { x: e.clientX, y: e.clientY };
    lastPosRef.current = { x: e.clientX, y: e.clientY };
    totalMovementRef.current = 0;
    isDraggingRef.current = false;
    longPressFiredRef.current = false;

    // Cancel any in-flight tap-confirm — if user is starting a new gesture
    // we don't want a stale single-click to fire underneath.
    if (pendingTapTimerRef.current) {
      // Don't fire it; let the new gesture decide.
      clearTimeout(pendingTapTimerRef.current);
      pendingTapTimerRef.current = null;
    }

    // Long-press → right-click. Fires only if the user hasn't moved by then.
    longPressTimerRef.current = setTimeout(() => {
      longPressTimerRef.current = null;
      if (isDraggingRef.current) return;
      longPressFiredRef.current = true;
      const { nx, ny } = cursor.posRef.current;
      sendControl({ type: 'direct_right_click', x: nx, y: ny, button: 'right', count: 1 });
    }, 500);
  }, [sendControl, cursor]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    if (!lastPosRef.current) return;

    const dx = e.clientX - lastPosRef.current.x;
    const dy = e.clientY - lastPosRef.current.y;
    lastPosRef.current = { x: e.clientX, y: e.clientY };

    totalMovementRef.current += Math.abs(dx) + Math.abs(dy);
    if (!isDraggingRef.current && totalMovementRef.current > MOVE_THRESHOLD) {
      isDraggingRef.current = true;
      // Crossed the move threshold — cancel long-press (we're dragging now).
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current);
        longPressTimerRef.current = null;
      }
      // Decide drag-mode: did the user just complete a tap before this hold?
      const now = Date.now();
      const recentDown = now - lastDownTimeRef.current < DOUBLE_TAP_INTERVAL;
      if (recentDown && pointerDownCountRef.current >= 2) {
        isDragModeRef.current = true;
        sendControl({ type: 'mousedown', button: 'left' });
      }
      pointerDownCountRef.current = 0;
    }

    if (!isDraggingRef.current) return;

    if (scrollMode && !isDragModeRef.current) {
      // Scroll mode — vertical drag becomes scroll. Inverse Y so finger-down
      // = scroll up (page reveals older content), matching every native UI.
      sendControl({ type: 'scroll', dy: -dy * 0.08 });
      return;
    }

    // Cursor move with Kotlin's acceleration.
    const speed = Math.hypot(dx, dy);
    const sens = Math.min(BASE_SENSITIVITY + ACCEL_FACTOR * Math.pow(speed, ACCEL_POWER), MAX_SENSITIVITY);
    const drawW = Math.max(lbRef.current.drawW, 1);
    const drawH = Math.max(lbRef.current.drawH, 1);
    const ndx = (dx * sens * PC_SENS) / drawW;
    const ndy = (dy * sens * PC_SENS) / drawH;
    const c = cursor.posRef.current;
    const nx = Math.max(0, Math.min(1, c.nx + ndx));
    const ny = Math.max(0, Math.min(1, c.ny + ndy));
    cursor.setNorm(nx, ny);
    sendControl({ type: 'direct_move', x: nx, y: ny });
  }, [sendControl, scrollMode, cursor]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }

    // Drag-mode end → emit mouseup, no tap.
    if (isDragModeRef.current) {
      sendControl({ type: 'mouseup', button: 'left' });
      isDragModeRef.current = false;
      isDraggingRef.current = false;
      tapCountRef.current = 0;
      lastTapTimeRef.current = 0;
      return;
    }

    // Plain drag (no double-tap precursor) → no click on release.
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      return;
    }

    // Long-press already sent the right-click → don't also send a left.
    if (longPressFiredRef.current) {
      longPressFiredRef.current = false;
      return;
    }

    // Tap → bump tapCount, schedule debounced fire after TAP_CONFIRM_DELAY.
    const now = Date.now();
    if (now - lastTapTimeRef.current < DOUBLE_TAP_INTERVAL) {
      tapCountRef.current += 1;
    } else {
      tapCountRef.current = 1;
    }
    lastTapTimeRef.current = now;

    if (pendingTapTimerRef.current) {
      clearTimeout(pendingTapTimerRef.current);
    }
    pendingTapTimerRef.current = setTimeout(flushPendingTap, TAP_CONFIRM_DELAY);
  }, [sendControl, flushPendingTap]);

  const onPointerCancel = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    clearTapTimers();
    if (isDragModeRef.current) {
      sendControl({ type: 'mouseup', button: 'left' });
      isDragModeRef.current = false;
    }
    isDraggingRef.current = false;
    tapCountRef.current = 0;
    longPressFiredRef.current = false;
  }, [sendControl]);

  return (
    <div
      style={{
        position: 'absolute', inset: 0,
        zIndex: 10,
        touchAction: 'none',
        WebkitUserSelect: 'none',
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
    />
  );
}
