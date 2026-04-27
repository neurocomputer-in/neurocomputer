'use client';
import { useAppSelector } from '@/store/hooks';

/**
 * Pulsing border — visual cue that the desktop tab is "live" / receiving
 * input. Color reflects the active touch mode:
 *   touchpad → cyan
 *   tablet   → indigo (accent)
 *   none     → muted gray (display-only)
 * The glow is subtle (CSS box-shadow inset) and pulses 1.5s, matching the
 * Kotlin app's CursorArrowOverlay behavior.
 */
export default function GlowingBorder() {
  const { mode, connected } = useAppSelector(s => s.mobileDesktop);

  const colorMap: Record<string, string> = {
    touchpad: '6, 182, 212',   // cyan-500
    tablet:   '99, 102, 241',  // indigo-500
    none:     '113, 113, 122', // zinc-500
  };
  const rgb = colorMap[mode] ?? colorMap.touchpad;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 25,
        borderRadius: 0,
        boxShadow: connected
          ? `inset 0 0 0 2px rgba(${rgb}, 0.4), inset 0 0 18px rgba(${rgb}, 0.25)`
          : `inset 0 0 0 2px rgba(${rgb}, 0.15)`,
        animation: connected ? 'desktopGlow 1.5s ease-in-out infinite' : 'none',
      }}
    >
      <style>{`
        @keyframes desktopGlow {
          0%, 100% {
            box-shadow:
              inset 0 0 0 2px rgba(${rgb}, 0.35),
              inset 0 0 14px rgba(${rgb}, 0.18);
          }
          50% {
            box-shadow:
              inset 0 0 0 2px rgba(${rgb}, 0.7),
              inset 0 0 28px rgba(${rgb}, 0.4);
          }
        }
      `}</style>
    </div>
  );
}
