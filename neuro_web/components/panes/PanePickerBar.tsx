'use client';
import { useEffect, useRef, useState } from 'react';
import { ChevronDown, MessageSquare, Terminal as TerminalIcon } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setPaneActiveCid } from '@/store/uiSlice';

interface Props { paneId: string; activeCid: string | null }

function tabIcon(type?: string) {
  return type === 'terminal' ? <TerminalIcon size={11} /> : <MessageSquare size={11} />;
}

export default function PanePickerBar({ paneId, activeCid }: Props) {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const tabs = useAppSelector(s => s.conversations.openTabs);
  const active = tabs.find(t => t.cid === activeCid) || null;

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const pick = (cid: string) => {
    dispatch(setPaneActiveCid({ id: paneId, cid }));
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v); }}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '3px 8px', borderRadius: 5,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: '#d0d6e0', fontSize: 11, cursor: 'pointer',
          fontFamily: 'inherit',
        }}
        title="Pick a session for this pane"
      >
        {tabIcon(active?.type)}
        <span style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {active ? active.title : 'Pick a session'}
        </span>
        <ChevronDown size={10} />
      </button>
      {open && (
        <div className="glass-dropdown" style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          minWidth: 260, borderRadius: 8, zIndex: 50,
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)', overflow: 'hidden',
        }}>
          {tabs.length === 0 && (
            <div style={{ padding: '10px 12px', color: '#62666d', fontSize: 12 }}>
              No sessions open. Start one first.
            </div>
          )}
          {tabs.map(t => {
            const isActive = t.cid === activeCid;
            return (
              <button
                key={t.cid}
                onClick={(e) => { e.stopPropagation(); pick(t.cid); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  width: '100%', padding: '8px 10px',
                  background: isActive ? 'rgba(94,106,210,0.12)' : 'transparent',
                  border: 'none', color: isActive ? '#f7f8f8' : '#d0d6e0',
                  fontSize: 12, cursor: 'pointer', textAlign: 'left',
                  fontFamily: 'inherit',
                }}
                onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                {tabIcon(t.type)}
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.title}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
