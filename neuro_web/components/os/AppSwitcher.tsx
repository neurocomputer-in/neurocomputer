'use client';
import { useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Globe } from 'lucide-react';
import { useGesture } from '@use-gesture/react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { focusWindow, closeWindow, WindowState } from '@/store/osSlice';
import { closeTab } from '@/store/conversationSlice';
import { APP_MAP } from '@/lib/appRegistry';
import { useIsMobile } from '@/hooks/useIsMobile';
import AppIconView from './AppIconView';

const APP_GRADIENTS: Record<string, string> = {
  'chat': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
  'terminal': 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)',
  'neuroide': 'linear-gradient(135deg, #1a0033 0%, #2d1b69 100%)',
};

interface Props {
  open: boolean;
  onClose: () => void;
  onNewWindow: () => void;
}

function WindowCard({ win, onFocus, onCloseWin }: {
  win: WindowState;
  onFocus: () => void;
  onCloseWin: () => void;
}) {
  const activeTab = win.tabs.find(t => t.id === win.activeTabId) ?? win.tabs[0];
  const app = activeTab ? APP_MAP[activeTab.appId as keyof typeof APP_MAP] : undefined;
  const color = app?.color ?? '#8B5CF6';
  const gradient = APP_GRADIENTS[activeTab?.type ?? 'chat'];
  const isMobile = useIsMobile();

  const bind = useGesture({
    onDrag: ({ swipe: [swipeX] }) => {
      if (isMobile && (swipeX === 1 || swipeX === -1)) onCloseWin();
    },
  });

  return (
    <motion.div
      {...(bind() as any)}
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.85, x: 60 }}
      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
      style={{
        background: gradient,
        borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.1)',
        overflow: 'hidden',
        cursor: 'pointer',
        position: 'relative',
        aspectRatio: isMobile ? '16/10' : '4/3',
        touchAction: 'pan-y',
      }}
    >
      <button
        onClick={(e) => { e.stopPropagation(); onCloseWin(); }}
        style={{
          position: 'absolute', top: 8, right: 8,
          width: 22, height: 22, borderRadius: '50%',
          background: 'rgba(0,0,0,0.5)', border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 2,
        }}
      >
        <X size={11} color="#fff" />
      </button>

      <div onClick={onFocus} style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: color, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {app ? <AppIconView app={app} size={16} /> : <Globe size={16} color="#fff" strokeWidth={1.6} />}
          </div>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0', margin: 0, lineHeight: 1.3 }}>
              {activeTab?.title ?? 'Window'}
            </p>
            <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', margin: 0 }}>
              {win.tabs.length} tab{win.tabs.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {win.tabs.slice(0, 4).map(tab => {
            const tApp = APP_MAP[tab.appId as keyof typeof APP_MAP];
            return (
              <div key={tab.id} style={{
                padding: '2px 6px', borderRadius: 4,
                background: 'rgba(255,255,255,0.08)',
                display: 'flex', alignItems: 'center', gap: 3,
              }}>
                {tApp ? <AppIconView app={tApp} size={9} color={tApp.color} /> : <Globe size={9} color="#888" strokeWidth={2} />}
                <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.6)', maxWidth: 56, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {tab.title}
                </span>
              </div>
            );
          })}
          {win.tabs.length > 4 && (
            <div style={{ padding: '2px 6px', borderRadius: 4, background: 'rgba(255,255,255,0.06)', fontSize: 9, color: 'rgba(255,255,255,0.4)' }}>
              +{win.tabs.length - 4}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function AppSwitcher({ open, onClose, onNewWindow }: Props) {
  const dispatch = useAppDispatch();
  const windows = useAppSelector(s => s.os.windows);
  const isMobile = useIsMobile();

  const handleFocus = useCallback((windowId: string) => {
    dispatch(focusWindow(windowId));
    onClose();
  }, [dispatch, onClose]);

  const handleClose = useCallback((win: WindowState) => {
    dispatch(closeWindow(win.id));
    for (const tab of win.tabs) dispatch(closeTab(tab.cid));
  }, [dispatch]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: isMobile ? '100%' : 0 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: isMobile ? '100%' : 0 }}
          transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.8 }}
          onClick={onClose}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(8,8,10,0.92)',
            backdropFilter: 'blur(20px)',
            zIndex: 10000,
            overflowY: 'auto',
            padding: isMobile ? '48px 16px 32px' : '40px',
            display: 'flex', flexDirection: 'column',
          }}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,0.5)', marginBottom: 16, textAlign: isMobile ? 'center' : 'left' }}>
              All Windows
            </p>
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
              gap: 12,
            }}>
              <AnimatePresence>
                {windows.map(win => (
                  <WindowCard
                    key={win.id}
                    win={win}
                    onFocus={() => handleFocus(win.id)}
                    onCloseWin={() => handleClose(win)}
                  />
                ))}
              </AnimatePresence>

              <motion.button
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                onClick={onNewWindow}
                style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8,
                  background: 'rgba(255,255,255,0.04)',
                  border: '2px dashed rgba(255,255,255,0.1)',
                  borderRadius: 16, cursor: 'pointer',
                  aspectRatio: isMobile ? '16/10' : '4/3',
                  color: 'rgba(255,255,255,0.4)',
                }}
              >
                <Plus size={24} strokeWidth={1.5} />
                <span style={{ fontSize: 12 }}>New window</span>
              </motion.button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
