'use client';
import { useRef, useCallback, useState } from 'react';
import {
  DndContext, closestCenter, PointerSensor,
  useSensor, useSensors, DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { WindowTab } from '@/types';
import { APP_MAP } from '@/lib/appRegistry';
import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass, Mic, Languages,
} from 'lucide-react';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
  search: Search, pen: Pen, barchart: BarChart2, folder: Folder,
  mail: Mail, calendar: Calendar, note: StickyNote, compass: Compass,
  mic: Mic, languages: Languages,
};

const OVERFLOW_THRESHOLD = 3;
const LONG_PRESS_MS = 500;

interface ContextMenuState { tabId: string; x: number; y: number; }

function TabContextMenu({ x, y, onClose, onRenameStart, onDismiss }: {
  x: number; y: number;
  onClose: () => void;
  onRenameStart: () => void;
  onDismiss: () => void;
}) {
  return (
    <>
      <div
        style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
        onClick={onDismiss}
        onContextMenu={(e) => { e.preventDefault(); onDismiss(); }}
      />
      <div style={{
        position: 'fixed', left: x, top: y, zIndex: 9999,
        background: 'rgba(30,30,34,0.97)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 8,
        boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        padding: '4px 0',
        minWidth: 140,
      }}>
        {([
          { label: 'Rename', action: onRenameStart },
          { label: 'Close Tab', action: onClose, danger: true },
        ] as const).map(item => (
          <button
            key={item.label}
            onClick={(e) => { e.stopPropagation(); item.action(); }}
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              padding: '7px 14px', background: 'none', border: 'none',
              cursor: 'pointer', fontSize: 13,
              color: (item as any).danger ? '#ff5f57' : 'rgba(255,255,255,0.85)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
          >
            {item.label}
          </button>
        ))}
      </div>
    </>
  );
}

function SortableTab({ tab, isActive, onActivate, onClose, isWindowActive, onContextMenu, onLongPress, renamingTabId, onRenameCommit }: {
  tab: WindowTab;
  isActive: boolean;
  onActivate: () => void;
  onClose: () => void;
  isWindowActive: boolean;
  onContextMenu: (e: React.MouseEvent) => void;
  onLongPress: (x: number, y: number) => void;
  renamingTabId: string | null;
  onRenameCommit: (value: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tab.id });
  const app = APP_MAP[tab.appId as keyof typeof APP_MAP];
  const LucideIcon = app ? (ICON_MAP[app.icon] || Globe) : Globe;
  const color = app?.color ?? '#888';
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isRenaming = renamingTabId === tab.id;

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    const { clientX, clientY } = e;
    longPressTimer.current = setTimeout(() => {
      longPressTimer.current = null;
      onLongPress(clientX, clientY);
    }, LONG_PRESS_MS);
  }, [onLongPress]);

  const cancelLongPress = useCallback(() => {
    if (longPressTimer.current) { clearTimeout(longPressTimer.current); longPressTimer.current = null; }
  }, []);

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        minWidth: 80, maxWidth: 180, flex: '1 1 0',
        height: '100%',
        userSelect: 'none',
        background: isActive ? 'rgba(60,60,66,0.95)' : 'transparent',
        borderRight: '1px solid rgba(255,255,255,0.05)',
        position: 'relative',
        borderBottom: isActive ? '2px solid ' + color : '2px solid transparent',
        boxSizing: 'border-box',
      }}
      {...attributes}
      {...listeners}
    >
      {/* Inner wrapper owns click/long-press/context so it doesn't clobber dnd listeners */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0 10px', height: '100%', cursor: 'pointer' }}
        onClick={!isRenaming ? onActivate : undefined}
        onContextMenu={onContextMenu}
        onPointerDown={handlePointerDown}
        onPointerMove={cancelLongPress}
        onPointerUp={cancelLongPress}
        onPointerLeave={cancelLongPress}
      >
        <LucideIcon size={11} color={color} strokeWidth={1.8} style={{ flexShrink: 0 }} />
        {isRenaming ? (
          <input
            autoFocus
            defaultValue={tab.title}
            style={{
              flex: 1, minWidth: 0, fontSize: '11px', fontWeight: 500,
              color: '#e0e0e0', background: 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: 3, padding: '1px 4px', outline: 'none',
            }}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            onBlur={(e) => onRenameCommit(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onRenameCommit((e.target as HTMLInputElement).value);
              if (e.key === 'Escape') onRenameCommit(tab.title);
            }}
          />
        ) : (
          <span style={{
            fontSize: '11px',
            fontWeight: isActive ? 500 : 400,
            color: isActive ? (isWindowActive ? '#e0e0e0' : '#aaa') : '#666',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            flex: 1, minWidth: 0,
          }}>
            {tab.title}
          </span>
        )}
      </div>
    </div>
  );
}

export interface WindowTabStripProps {
  tabs: WindowTab[];
  activeTabId: string;
  isWindowActive: boolean;
  onActivate: (tabId: string) => void;
  onClose: (tabId: string) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
  onRename?: (tabId: string, newTitle: string) => void;
  onOverflowPill?: () => void;
  onNewTab: () => void;
  trailingSlot?: React.ReactNode;
}

export default function WindowTabStrip({
  tabs, activeTabId, isWindowActive,
  onActivate, onClose, onReorder, onRename, onOverflowPill, onNewTab, trailingSlot,
}: WindowTabStripProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const showPill = tabs.length > OVERFLOW_THRESHOLD;
  const visibleTabs = showPill ? tabs.slice(0, OVERFLOW_THRESHOLD) : tabs;
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [renamingTabId, setRenamingTabId] = useState<string | null>(null);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const fromIndex = tabs.findIndex(t => t.id === active.id);
    const toIndex = tabs.findIndex(t => t.id === over.id);
    if (fromIndex !== -1 && toIndex !== -1) onReorder(fromIndex, toIndex);
  }, [tabs, onReorder]);

  const openMenu = useCallback((tabId: string, x: number, y: number) => {
    setContextMenu({ tabId, x, y });
  }, []);

  const closeMenu = useCallback(() => setContextMenu(null), []);

  const handleRenameCommit = useCallback((value: string) => {
    if (renamingTabId && value.trim()) onRename?.(renamingTabId, value.trim());
    setRenamingTabId(null);
  }, [renamingTabId, onRename]);

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'stretch', height: '100%', minWidth: 0, flex: 1, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'stretch', flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={visibleTabs.map(t => t.id)} strategy={horizontalListSortingStrategy}>
              {visibleTabs.map(tab => (
                <SortableTab
                  key={tab.id}
                  tab={tab}
                  isActive={tab.id === activeTabId}
                  isWindowActive={isWindowActive}
                  onActivate={() => onActivate(tab.id)}
                  onClose={() => { onClose(tab.id); closeMenu(); }}
                  onContextMenu={(e) => { e.preventDefault(); openMenu(tab.id, e.clientX, e.clientY); }}
                  onLongPress={(x, y) => openMenu(tab.id, x, y)}
                  renamingTabId={renamingTabId}
                  onRenameCommit={handleRenameCommit}
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>

        {showPill && (
          <button
            onClick={onOverflowPill}
            style={{
              flexShrink: 0, padding: '0 8px',
              background: 'rgba(255,255,255,0.06)', border: 'none',
              borderRight: '1px solid rgba(255,255,255,0.05)',
              cursor: 'pointer', fontSize: '10px', fontWeight: 600,
              color: 'rgba(255,255,255,0.6)', display: 'flex', alignItems: 'center',
            }}
          >
            +{tabs.length - OVERFLOW_THRESHOLD}
          </button>
        )}

        <button
          onClick={onNewTab}
          style={{
            flexShrink: 0, width: 28,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: 'rgba(255,255,255,0.4)', fontSize: 16, lineHeight: 1,
          }}
          title="New tab"
        >
          +
        </button>

        {trailingSlot}
      </div>

      {contextMenu && (
        <TabContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => { onClose(contextMenu.tabId); closeMenu(); }}
          onRenameStart={() => { setRenamingTabId(contextMenu.tabId); closeMenu(); }}
          onDismiss={closeMenu}
        />
      )}
    </>
  );
}
