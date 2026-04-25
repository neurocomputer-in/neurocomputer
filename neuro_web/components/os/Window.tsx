'use client';
import { useRef, useCallback, useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Minus, Square, Copy, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  closeWindow, removeWindow, focusWindow, minimizeWindow, maximizeWindow,
  moveWindow, resizeWindow, closeTabFromWindow, setActiveTabInWindow, reorderWindowTabs,
} from '@/store/osSlice';
import { closeTab, deleteConversation } from '@/store/conversationSlice';
import { WindowContext } from './WindowContext';
import WindowTabStrip from './WindowTabStrip';
import AppPicker from './AppPicker';
import TabOverviewPopover from './TabOverviewPopover';
import { useIsMobile } from '@/hooks/useIsMobile';

const TITLEBAR_H = 36;

interface Props {
  windowId: string;
  children: ReactNode;
  desktopRect?: { width: number; height: number } | null;
  onNewTab?: (windowId: string, appId: string, tabKind: string) => void;
}

export default function Window({ windowId, children, desktopRect, onNewTab }: Props) {
  const dispatch = useAppDispatch();
  const win = useAppSelector(s => s.os.windows.find(w => w.id === windowId));
  const activeWindowId = useAppSelector(s => s.os.activeWindowId);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const isMobile = useIsMobile();
  const isActive = activeWindowId === windowId;
  const [hoverTraffic, setHoverTraffic] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [overviewOpen, setOverviewOpen] = useState(false);

  const dragRef = useRef<{ startX: number; startY: number; winX: number; winY: number } | null>(null);
  const resizeRef = useRef<{
    startX: number; startY: number; winX: number; winY: number;
    winW: number; winH: number; edge: string;
  } | null>(null);

  const activeTab = win?.tabs.find(t => t.id === win.activeTabId);

  const handleDragStart = useCallback((e: React.PointerEvent) => {
    if (win?.maximized) return;
    if ((e.target as HTMLElement).closest('button')) return;
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { startX: e.clientX, startY: e.clientY, winX: win!.x, winY: win!.y };
  }, [win]);

  const handleDragMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current || !win) return;
    dispatch(moveWindow({ id: win.id, x: dragRef.current.winX + (e.clientX - dragRef.current.startX), y: dragRef.current.winY + (e.clientY - dragRef.current.startY) }));
  }, [win, dispatch]);

  const handleDragEnd = useCallback(() => { dragRef.current = null; }, []);

  const handleResizeStart = useCallback((edge: string) => (e: React.PointerEvent) => {
    if (!win || win.maximized) return;
    e.preventDefault(); e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    resizeRef.current = { startX: e.clientX, startY: e.clientY, winX: win.x, winY: win.y, winW: win.width, winH: win.height, edge };
  }, [win]);

  const handleResizeMove = useCallback((e: React.PointerEvent) => {
    if (!resizeRef.current || !win) return;
    const r = resizeRef.current;
    const dx = e.clientX - r.startX, dy = e.clientY - r.startY;
    let newX = r.winX, newY = r.winY, newW = r.winW, newH = r.winH;
    if (r.edge.includes('e')) newW = Math.max(320, r.winW + dx);
    if (r.edge.includes('w')) { newW = Math.max(320, r.winW - dx); newX = r.winX + dx; }
    if (r.edge.includes('s')) newH = Math.max(200, r.winH + dy);
    if (r.edge.includes('n')) { newH = Math.max(200, r.winH - dy); newY = r.winY + dy; }
    dispatch(resizeWindow({ id: win.id, width: newW, height: newH, x: newX, y: newY }));
  }, [win, dispatch]);

  const handleResizeEnd = useCallback(() => { resizeRef.current = null; }, []);

  const handleCloseWindow = useCallback(() => {
    if (!win) return;
    for (const tab of win.tabs) {
      const msgs = tabMessages[tab.cid];
      const isChatEmpty = tab.type === 'chat' && msgs !== undefined && msgs.length === 0;
      if (isChatEmpty) {
        dispatch(removeWindow(win.id));
        dispatch(closeTab(tab.cid));
        dispatch(deleteConversation(tab.cid));
        return;
      }
    }
    dispatch(closeWindow(win.id));
    for (const tab of win.tabs) dispatch(closeTab(tab.cid));
  }, [win, dispatch, tabMessages]);

  if (!win || !activeTab) return null;

  const isMax = win.maximized;
  const winStyle: React.CSSProperties = isMax
    ? { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: win.zIndex }
    : { position: 'absolute', left: win.x, top: win.y, width: win.width, height: win.height, zIndex: win.zIndex };

  return (
    <AnimatePresence>
      {!win.minimized && (
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.92 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          style={{
            ...winStyle,
            display: 'flex', flexDirection: 'column',
            borderRadius: isMax ? '0' : '12px',
            overflow: 'hidden',
            boxShadow: isActive
              ? '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08)'
              : '0 4px 16px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.04)',
            background: 'rgba(22, 22, 24, 0.92)',
            backdropFilter: 'blur(20px) saturate(180%)',
            WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          }}
          onMouseDown={() => dispatch(focusWindow(win.id))}
        >
          {/* Title / Tab bar */}
          <div
            onPointerDown={handleDragStart}
            onPointerMove={handleDragMove}
            onPointerUp={handleDragEnd}
            onDoubleClick={() => dispatch(maximizeWindow(win.id))}
            onMouseEnter={() => setHoverTraffic(true)}
            onMouseLeave={() => setHoverTraffic(false)}
            style={{
              position: 'relative', zIndex: 10,
              height: TITLEBAR_H, minHeight: TITLEBAR_H,
              display: 'flex', alignItems: 'stretch',
              background: isActive ? 'rgba(40,40,44,0.95)' : 'rgba(30,30,34,0.9)',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
              cursor: isMax ? 'default' : 'grab',
              userSelect: 'none', flexShrink: 0,
            }}
          >
            {/* Traffic lights */}
            <div style={{ display: 'flex', gap: '7px', alignItems: 'center', padding: '0 12px', flexShrink: 0 }}>
              {([
                { color: '#ff5f57', hoverBg: '#ff3b30', action: handleCloseWindow, Icon: X },
                { color: '#febd2f', hoverBg: '#f5a623', action: () => dispatch(minimizeWindow(win.id)), Icon: Minus },
                { color: '#28c840', hoverBg: '#26b024', action: () => dispatch(maximizeWindow(win.id)), Icon: isMax ? Copy : Square },
              ] as const).map((btn, i) => (
                <button
                  key={i}
                  onPointerDown={(e) => e.stopPropagation()}
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => { e.stopPropagation(); btn.action(); }}
                  style={{
                    width: 12, height: 12, borderRadius: '50%',
                    background: hoverTraffic && isActive ? btn.hoverBg : btn.color,
                    border: 'none', cursor: 'pointer', padding: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'background 0.15s',
                    opacity: hoverTraffic && isActive ? 1 : (isActive ? 0.85 : 0.5),
                  }}
                >
                  {hoverTraffic && isActive && <btn.Icon size={7} color="#000" strokeWidth={3} />}
                </button>
              ))}
            </div>

            {/* Tab strip */}
            <WindowTabStrip
              tabs={win.tabs}
              activeTabId={win.activeTabId}
              isWindowActive={isActive}
              onActivate={(tabId) => dispatch(setActiveTabInWindow({ windowId: win.id, tabId }))}
              onClose={(tabId) => {
                const tab = win.tabs.find(t => t.id === tabId);
                if (tab) dispatch(closeTab(tab.cid));
                dispatch(closeTabFromWindow({ windowId: win.id, tabId }));
              }}
              onReorder={(from, to) => dispatch(reorderWindowTabs({ windowId: win.id, fromIndex: from, toIndex: to }))}
              onOverflowPill={() => setOverviewOpen(true)}
              onNewTab={() => setPickerOpen(true)}
            />
          </div>

          {/* Content — keyed to activeTab.id so components re-mount on tab switch */}
          <div key={activeTab.id} style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <WindowContext.Provider value={{ windowId: win.id, cid: activeTab.cid }}>
              {children}
            </WindowContext.Provider>
          </div>

          {/* Resize handles */}
          {!isMax && !isMobile && (
            <>
              {['n','s','e','w','ne','nw','se','sw'].map(edge => {
                const isCorner = edge.length === 2;
                const size = isCorner ? 12 : 6;
                const style: React.CSSProperties = {
                  position: 'absolute', zIndex: 5,
                  ...(edge.includes('n') ? { top: 0 } : {}),
                  ...(edge.includes('s') ? { bottom: 0 } : {}),
                  ...(edge.includes('e') ? { right: 0 } : {}),
                  ...(edge.includes('w') ? { left: 0 } : {}),
                  ...(edge === 'n' || edge === 's' ? { left: size, right: size, height: size, cursor: `${edge}-resize` } : {}),
                  ...(edge === 'e' || edge === 'w' ? { top: size, bottom: size, width: size, cursor: `${edge}-resize` } : {}),
                  ...(isCorner ? { width: size*2, height: size*2, cursor: `${edge}-resize` } : {}),
                };
                return (
                  <div key={edge}
                    onPointerDown={handleResizeStart(edge)}
                    onPointerMove={handleResizeMove}
                    onPointerUp={handleResizeEnd}
                    style={style}
                  />
                );
              })}
            </>
          )}

          {/* Pickers */}
          {pickerOpen && (
            <AppPicker
              onPick={(appId, tabKind) => { setPickerOpen(false); onNewTab?.(win.id, appId, tabKind); }}
              onClose={() => setPickerOpen(false)}
            />
          )}
          {overviewOpen && (
            <TabOverviewPopover
              tabs={win.tabs}
              activeTabId={win.activeTabId}
              onActivate={(tabId) => { dispatch(setActiveTabInWindow({ windowId: win.id, tabId })); setOverviewOpen(false); }}
              onClose={() => setOverviewOpen(false)}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
