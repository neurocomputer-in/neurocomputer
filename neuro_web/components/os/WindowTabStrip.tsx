'use client';
import { useRef, useCallback } from 'react';
import { X } from 'lucide-react';
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

function SortableTab({
  tab, isActive, onActivate, onClose, isWindowActive,
}: {
  tab: WindowTab;
  isActive: boolean;
  onActivate: () => void;
  onClose: () => void;
  isWindowActive: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tab.id });
  const app = APP_MAP[tab.appId as keyof typeof APP_MAP];
  const LucideIcon = app ? (ICON_MAP[app.icon] || Globe) : Globe;
  const color = app?.color ?? '#888';

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        minWidth: 80,
        maxWidth: 180,
        flex: '1 1 0',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '0 8px 0 10px',
        height: '100%',
        cursor: 'pointer',
        userSelect: 'none',
        background: isActive ? 'rgba(60,60,66,0.95)' : 'transparent',
        borderRight: '1px solid rgba(255,255,255,0.05)',
        position: 'relative',
        borderBottom: isActive ? '2px solid ' + color : '2px solid transparent',
        boxSizing: 'border-box',
      }}
      onClick={onActivate}
      {...attributes}
      {...listeners}
    >
      <LucideIcon size={11} color={color} strokeWidth={1.8} style={{ flexShrink: 0 }} />
      <span style={{
        fontSize: '11px',
        fontWeight: isActive ? 500 : 400,
        color: isActive ? (isWindowActive ? '#e0e0e0' : '#aaa') : '#666',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        flex: 1,
        minWidth: 0,
      }}>
        {tab.title}
      </span>
      <button
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 14, height: 14, borderRadius: '50%',
          background: 'transparent',
          border: 'none', cursor: 'pointer', padding: 0, flexShrink: 0,
          color: 'rgba(255,255,255,0.4)',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.12)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <X size={9} strokeWidth={2.5} />
      </button>
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
  onOverflowPill?: () => void;
  onNewTab: () => void;
  trailingSlot?: React.ReactNode;
}

export default function WindowTabStrip({
  tabs, activeTabId, isWindowActive,
  onActivate, onClose, onReorder, onOverflowPill, onNewTab, trailingSlot,
}: WindowTabStripProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const showPill = tabs.length > OVERFLOW_THRESHOLD;
  const visibleTabs = showPill ? tabs.slice(0, OVERFLOW_THRESHOLD) : tabs;

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const fromIndex = tabs.findIndex(t => t.id === active.id);
    const toIndex = tabs.findIndex(t => t.id === over.id);
    if (fromIndex !== -1 && toIndex !== -1) onReorder(fromIndex, toIndex);
  }, [tabs, onReorder]);

  return (
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
                onClose={() => onClose(tab.id)}
              />
            ))}
          </SortableContext>
        </DndContext>
      </div>

      {showPill && (
        <button
          onClick={onOverflowPill}
          style={{
            flexShrink: 0,
            padding: '0 8px',
            background: 'rgba(255,255,255,0.06)',
            border: 'none',
            borderRight: '1px solid rgba(255,255,255,0.05)',
            cursor: 'pointer',
            fontSize: '10px',
            fontWeight: 600,
            color: 'rgba(255,255,255,0.6)',
            display: 'flex', alignItems: 'center',
          }}
        >
          +{tabs.length - OVERFLOW_THRESHOLD}
        </button>
      )}

      <button
        onClick={onNewTab}
        style={{
          flexShrink: 0,
          width: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: 'rgba(255,255,255,0.4)', fontSize: 16, lineHeight: 1,
        }}
        title="New tab"
      >
        +
      </button>

      {trailingSlot}
    </div>
  );
}
