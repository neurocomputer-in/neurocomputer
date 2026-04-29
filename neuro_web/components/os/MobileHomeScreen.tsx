'use client';
import { useCallback, useRef } from 'react';
import {
  DndContext, closestCenter, PointerSensor,
  useSensor, useSensors, DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, rectSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setMobileOrder } from '@/store/iconsSlice';
import { APP_MAP, AppDef } from '@/lib/appRegistry';
import AppIconView from './AppIconView';

function MobileIcon({ appId, onLaunch }: { appId: string; onLaunch: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: appId });
  const app = APP_MAP[appId as keyof typeof APP_MAP];
  // Track tap via pointerdown/up on inner content — dnd-kit's preventDefault on outer
  // blocks synthetic click, so we detect taps manually.
  const tapRef = useRef<{ t: number; x: number; y: number } | null>(null);

  if (!app) return null;

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.3 : 1,
        touchAction: 'none',
      }}
      {...attributes}
      {...listeners}
    >
      {/* Inner wrapper detects taps independently from dnd-kit drag */}
      <div
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}
        onPointerDown={(e) => {
          tapRef.current = { t: Date.now(), x: e.clientX, y: e.clientY };
        }}
        onPointerUp={(e) => {
          if (!tapRef.current) return;
          const elapsed = Date.now() - tapRef.current.t;
          const dist = Math.hypot(e.clientX - tapRef.current.x, e.clientY - tapRef.current.y);
          tapRef.current = null;
          // Short tap with minimal movement and drag wasn't activated
          if (elapsed < 220 && dist < 10 && !isDragging) onLaunch();
        }}
        onPointerCancel={() => { tapRef.current = null; }}
      >
        <div style={{
          width: 60, height: 60, borderRadius: 16,
          background: app.iconImage ? 'transparent' : `linear-gradient(145deg, ${app.color}ee 0%, ${app.color}99 100%)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: `0 4px 14px ${app.color}55, 0 2px 6px rgba(0,0,0,0.35)`,
          overflow: 'hidden',
          transform: isDragging ? 'scale(1.1)' : 'scale(1)',
          transition: 'transform 0.15s',
        }}>
          {app.iconImage ? <AppIconView app={app} fill /> : <AppIconView app={app} size={32} />}
        </div>
        <span style={{
          fontSize: 10, fontWeight: 500,
          color: 'rgba(255,255,255,0.92)',
          textShadow: '0 1px 4px rgba(0,0,0,0.9)',
          maxWidth: 64, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          textAlign: 'center',
        }}>
          {app.name}
        </span>
      </div>
    </div>
  );
}

export default function MobileHomeScreen({ onLaunch }: { onLaunch: (app: AppDef) => void }) {
  const dispatch = useAppDispatch();
  const mobileOrder = useAppSelector(s => s.icons.mobileOrder);

  // 250ms hold to activate drag; quick tap handled by inner wrapper above
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { delay: 250, tolerance: 5 } })
  );

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = mobileOrder.indexOf(String(active.id));
    const newIndex = mobileOrder.indexOf(String(over.id));
    if (oldIndex !== -1 && newIndex !== -1) {
      dispatch(setMobileOrder(arrayMove(mobileOrder, oldIndex, newIndex)));
    }
  }, [mobileOrder, dispatch]);

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 0,
      overflowY: 'auto', overflowX: 'hidden',
    }}>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={mobileOrder} strategy={rectSortingStrategy}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '20px 8px',
            padding: '24px 16px 88px',
          }}>
            {mobileOrder.map(appId => {
              const app = APP_MAP[appId as keyof typeof APP_MAP];
              if (!app) return null;
              return (
                <MobileIcon
                  key={appId}
                  appId={appId}
                  onLaunch={() => onLaunch(app)}
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
