'use client';
import { useRef, useCallback, useEffect, useState } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useAppSelector } from '@/store/hooks';
import { useLocalCursor } from './LocalCursorContext';

const BASE_SENSITIVITY = 1.0;
const ACCEL_FACTOR = 0.18;
const ACCEL_POWER = 0.65;
const MAX_SENSITIVITY = 12.0;
const PC_SENS = 2.5;
// Local cursor moves faster than what we send to the server so the user gets
// instant visual feedback even though the server actuates the real mouse a
// few frames later. Tune to match Kotlin's CursorArrowOverlay feel.
const LOCAL_CURSOR_GAIN = 1.6;
const LONG_PRESS_MS = 500;
const DOUBLE_TAP_MS = 350;
const TAP_CONFIRM_MS = 180;
const MOVE_THRESHOLD_PX = 3;

function applyAccel(delta: number): number {
  const abs = Math.abs(delta);
  const accel = 1 + ACCEL_FACTOR * Math.pow(abs, ACCEL_POWER);
  return Math.sign(delta) * Math.min(abs * accel, abs * MAX_SENSITIVITY) * PC_SENS * BASE_SENSITIVITY;
}

type GestureState = 'idle' | 'potential-tap' | 'dragging' | 'scrolling' | 'dt-drag';

export default function TouchpadOverlay() {
  const { sendControl } = useDesktopRoom();
  const { scrollMode } = useAppSelector(s => s.mobileDesktop);
  const cursor = useLocalCursor();

  const stateRef = useRef<GestureState>('idle');
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const pointerDownPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const lastTapTimeRef = useRef(0);
  const tapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerIdRef = useRef<number | null>(null);
  const elRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });

  // Track our own size so cursor clamping stays inside the visible area when
  // the window resizes (rotation, fullscreen toggles).
  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const update = () => setContainerSize({ w: el.clientWidth, h: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Center the local cursor on first mount so the user can see where it is
  // before they touch anything. Kotlin behaves the same way.
  useEffect(() => {
    if (containerSize.w > 0 && containerSize.h > 0) {
      cursor.setPos(containerSize.w / 2, containerSize.h / 2);
    }
    // Only on first non-zero size — re-centering on every resize would feel
    // jarring during fullscreen transitions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerSize.w > 0]);

  const clearTimers = () => {
    if (tapTimerRef.current) { clearTimeout(tapTimerRef.current); tapTimerRef.current = null; }
    if (longPressTimerRef.current) { clearTimeout(longPressTimerRef.current); longPressTimerRef.current = null; }
  };

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (pointerIdRef.current !== null) return;
    pointerIdRef.current = e.pointerId;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    clearTimers();
    pointerDownPosRef.current = { x: e.clientX, y: e.clientY };
    lastPosRef.current = { x: e.clientX, y: e.clientY };

    const isDoubleTap = Date.now() - lastTapTimeRef.current < DOUBLE_TAP_MS;

    if (isDoubleTap) {
      stateRef.current = 'dt-drag';
      sendControl({ type: 'mousedown', button: 'left' });
    } else {
      stateRef.current = 'potential-tap';
      longPressTimerRef.current = setTimeout(() => {
        if (stateRef.current === 'potential-tap') {
          stateRef.current = 'idle';
          sendControl({ type: 'click', button: 'right', count: 1 });
        }
      }, LONG_PRESS_MS);
    }
  }, [sendControl]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    if (!lastPosRef.current) return;

    const dx = e.clientX - lastPosRef.current.x;
    const dy = e.clientY - lastPosRef.current.y;
    const startDist = Math.hypot(
      e.clientX - pointerDownPosRef.current.x,
      e.clientY - pointerDownPosRef.current.y
    );
    lastPosRef.current = { x: e.clientX, y: e.clientY };

    if (stateRef.current === 'potential-tap' && startDist > MOVE_THRESHOLD_PX) {
      clearTimers();
      stateRef.current = scrollMode ? 'scrolling' : 'dragging';
    }

    if (stateRef.current === 'dragging' || stateRef.current === 'dt-drag') {
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
      const accelDx = applyAccel(dx);
      const accelDy = applyAccel(dy);
      sendControl({ type: 'mouse_move', dx: accelDx, dy: accelDy });
      // Move local cursor with extra gain — it leads the server-driven cursor
      // by a few px so the user gets sub-RTT visual response. The server's
      // cursor_position broadcast (via ServerCursorOverlay) will catch up.
      cursor.movePos(accelDx * LOCAL_CURSOR_GAIN, accelDy * LOCAL_CURSOR_GAIN, containerSize);
    }

    if (stateRef.current === 'scrolling') {
      sendControl({ type: 'scroll', dy: -dy * 0.08 });
    }
  }, [sendControl, scrollMode, cursor, containerSize]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    clearTimers();

    if (stateRef.current === 'dt-drag') {
      sendControl({ type: 'mouseup', button: 'left' });
      stateRef.current = 'idle';
      lastTapTimeRef.current = 0;
      return;
    }

    if (stateRef.current === 'potential-tap') {
      const now = Date.now();
      lastTapTimeRef.current = now;
      tapTimerRef.current = setTimeout(() => {
        sendControl({ type: 'click', button: 'left', count: 1 });
      }, TAP_CONFIRM_MS);
    }

    stateRef.current = 'idle';
    lastPosRef.current = null;
  }, [sendControl]);

  return (
    <div
      ref={elRef}
      style={{
        position: 'absolute', inset: 0,
        zIndex: 10,
        touchAction: 'none',
        WebkitUserSelect: 'none',
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    />
  );
}
