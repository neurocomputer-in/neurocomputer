'use client';
import { useEffect, useRef } from 'react';
import { ChevronUp, ChevronDown, ChevronsUp, ChevronsDown } from 'lucide-react';

interface Props {
  sendControl: (payload: Record<string, unknown>) => void;
}

type ScrollAction =
  | 'up' | 'down'
  | 'page-up' | 'page-down'
  | 'halfpage-up' | 'halfpage-down'
  | 'top'
  | 'cancel';

// Mobile terminal scroll bar — drives tmux copy-mode directly through the
// backend via a WS control message. No xterm-internals, no mouse-mode
// detection, no escape-sequence guessing: the server runs
// `tmux send-keys -X <action>` on the real session. Works regardless of
// whether tmux mouse mode is on.
export default function TerminalScrollbar({ sendControl }: Props) {
  const repeatRef = useRef<number | null>(null);

  const fire = (action: ScrollAction, count = 1) => {
    sendControl({ type: 'tmux-scroll', action, count });
  };

  // For repeat-on-hold: start conservative, then accelerate — 3 taps, then
  // ramp to faster. Line actions (up/down) fire 1 at a time; page actions
  // batch bigger chunks.
  const startRepeat = (action: ScrollAction) => {
    fire(action, action.startsWith('page') ? 1 : 1);
    if (repeatRef.current) clearTimeout(repeatRef.current);
    let ticks = 0;
    const tick = () => {
      ticks += 1;
      // Ramp speed: after a few ticks, batch bigger counts in one request.
      const count = action.startsWith('page')
        ? 1
        : Math.min(5, 1 + Math.floor(ticks / 4)); // 1,1,1,1,2,2,2,2,3,...
      fire(action, count);
      const delay = ticks < 3 ? 180 : 60;
      repeatRef.current = window.setTimeout(tick, delay) as unknown as number;
    };
    repeatRef.current = window.setTimeout(tick, 220) as unknown as number;
  };

  const stopRepeat = () => {
    if (repeatRef.current != null) {
      clearTimeout(repeatRef.current);
      repeatRef.current = null;
    }
  };
  useEffect(() => () => stopRepeat(), []);

  const BTN_H = 34;
  const BAR_W = 30;

  return (
    <div
      style={{
        width: BAR_W,
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(255,255,255,0.03)',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        userSelect: 'none',
        flexShrink: 0,
      }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      {/* Jump to top */}
      <Btn height={BTN_H} onClick={() => fire('top')} title="Jump to top">
        <ChevronsUp size={14} color="#a0a6b0" />
      </Btn>

      {/* Page up */}
      <Btn
        height={BTN_H}
        hold={() => startRepeat('page-up')}
        release={stopRepeat}
        title="Page up (hold to repeat)"
      >
        <span style={{ color: '#a0a6b0', fontSize: 9, fontFamily: 'monospace' }}>⇞</span>
      </Btn>

      {/* Line up */}
      <Btn
        height={BTN_H}
        hold={() => startRepeat('up')}
        release={stopRepeat}
        title="Scroll up (hold to repeat)"
      >
        <ChevronUp size={15} color="#d0d6e0" />
      </Btn>

      {/* Filler bar — visual only */}
      <div style={{
        flex: 1, minHeight: 40,
        borderTop: '1px solid rgba(255,255,255,0.04)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: 2, background: 'rgba(140,145,155,0.2)',
          alignSelf: 'stretch', margin: '6px 0', borderRadius: 1,
        }} />
      </div>

      {/* Line down */}
      <Btn
        height={BTN_H}
        hold={() => startRepeat('down')}
        release={stopRepeat}
        title="Scroll down (hold to repeat)"
      >
        <ChevronDown size={15} color="#d0d6e0" />
      </Btn>

      {/* Page down */}
      <Btn
        height={BTN_H}
        hold={() => startRepeat('page-down')}
        release={stopRepeat}
        title="Page down (hold to repeat)"
      >
        <span style={{ color: '#a0a6b0', fontSize: 9, fontFamily: 'monospace' }}>⇟</span>
      </Btn>

      {/* Exit copy-mode → back to live */}
      <Btn height={BTN_H} onClick={() => fire('cancel')} title="Back to live">
        <ChevronsDown size={14} color="#a0a6b0" />
      </Btn>
    </div>
  );
}

function Btn({
  height, onClick, hold, release, title, children,
}: {
  height: number;
  onClick?: () => void;
  hold?: () => void;
  release?: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      onPointerDown={hold}
      onPointerUp={release}
      onPointerCancel={release}
      onPointerLeave={release}
      title={title}
      style={{
        height,
        minHeight: height,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'transparent',
        border: 'none',
        borderTop: '1px solid rgba(255,255,255,0.04)',
        cursor: 'pointer',
        padding: 0,
        touchAction: 'manipulation',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      {children}
    </button>
  );
}
