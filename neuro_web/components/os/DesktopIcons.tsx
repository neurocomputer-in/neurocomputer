'use client';
import { useRef, useCallback, useState } from 'react';
import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass, Mic, Languages,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { moveDesktopIcon } from '@/store/iconsSlice';
import { APP_LIST, AppDef } from '@/lib/appRegistry';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
  search: Search, pen: Pen, barchart: BarChart2, folder: Folder,
  mail: Mail, calendar: Calendar, note: StickyNote, compass: Compass,
  mic: Mic, languages: Languages,
};

const ICON_SIZE = 52;

function DesktopIconItem({ app, storedX, storedY, selected, onSelect, onLaunch, onDrop }: {
  app: AppDef;
  storedX: number; storedY: number;
  selected: boolean;
  onSelect: () => void;
  onLaunch: () => void;
  onDrop: (x: number, y: number) => void;
}) {
  const elRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    startX: number; startY: number;
    originX: number; originY: number;
    moved: boolean;
  } | null>(null);
  const [dragOffset, setDragOffset] = useState<{ dx: number; dy: number } | null>(null);
  const LucideIcon = ICON_MAP[app.icon] || Globe;

  const displayX = storedX + (dragOffset?.dx ?? 0);
  const displayY = storedY + (dragOffset?.dy ?? 0);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { startX: e.clientX, startY: e.clientY, originX: storedX, originY: storedY, moved: false };
    onSelect();
  }, [storedX, storedY, onSelect]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (!dragRef.current.moved && (Math.abs(dx) > 6 || Math.abs(dy) > 6)) {
      dragRef.current.moved = true;
    }
    if (dragRef.current.moved) setDragOffset({ dx, dy });
  }, []);

  const handlePointerUp = useCallback(() => {
    if (!dragRef.current) return;
    if (dragRef.current.moved && dragOffset) {
      onDrop(storedX + dragOffset.dx, storedY + dragOffset.dy);
    }
    setDragOffset(null);
    dragRef.current = null;
  }, [dragOffset, storedX, storedY, onDrop]);

  return (
    <div
      ref={elRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onDoubleClick={(e) => { e.stopPropagation(); onLaunch(); }}
      onClick={(e) => e.stopPropagation()}
      style={{
        position: 'absolute',
        left: displayX, top: displayY,
        width: 72, zIndex: dragOffset ? 50 : 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
        cursor: 'default', userSelect: 'none', touchAction: 'none',
        transform: dragOffset ? 'scale(1.05)' : 'scale(1)',
        transition: dragOffset ? 'none' : 'transform 0.12s',
      }}
    >
      <div style={{
        width: ICON_SIZE, height: ICON_SIZE, borderRadius: 13,
        background: `linear-gradient(145deg, ${app.color}44 0%, ${app.color}22 100%)`,
        border: selected
          ? `1.5px solid ${app.color}99`
          : '1px solid rgba(255,255,255,0.09)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: selected
          ? `0 0 0 2.5px ${app.color}55, 0 6px 18px rgba(0,0,0,0.5)`
          : '0 3px 10px rgba(0,0,0,0.4)',
        backdropFilter: 'blur(6px)',
        transition: 'border 0.12s, box-shadow 0.12s',
      }}>
        <LucideIcon size={24} color={app.color} strokeWidth={1.7} />
      </div>
      <span style={{
        fontSize: 10.5, fontWeight: 500,
        color: '#fff',
        textAlign: 'center',
        textShadow: '0 1px 4px rgba(0,0,0,0.95), 0 0 10px rgba(0,0,0,0.7)',
        maxWidth: 72,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        background: selected ? 'rgba(80,60,180,0.65)' : 'transparent',
        borderRadius: selected ? 3 : 0,
        padding: selected ? '1px 4px' : '0',
      }}>
        {app.name}
      </span>
    </div>
  );
}

export default function DesktopIcons({ onLaunch }: { onLaunch: (app: AppDef) => void }) {
  const dispatch = useAppDispatch();
  const desktopLayout = useAppSelector(s => s.icons.desktopLayout);
  const [selected, setSelected] = useState<string | null>(null);

  const handleDrop = useCallback((appId: string, x: number, y: number) => {
    dispatch(moveDesktopIcon({ appId, x: Math.max(0, x), y: Math.max(0, y) }));
  }, [dispatch]);

  return (
    <div
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 0 }}
      onClick={() => setSelected(null)}
    >
      {APP_LIST.map(app => {
        const pos = desktopLayout[app.id] ?? { x: 20, y: 20 };
        return (
          <DesktopIconItem
            key={app.id}
            app={app}
            storedX={pos.x}
            storedY={pos.y}
            selected={selected === app.id}
            onSelect={() => setSelected(app.id)}
            onLaunch={() => { setSelected(null); onLaunch(app); }}
            onDrop={(x, y) => handleDrop(app.id, x, y)}
          />
        );
      })}
    </div>
  );
}
