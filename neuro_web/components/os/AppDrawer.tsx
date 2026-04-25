'use client';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass, Mic, Languages,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeLauncher } from '@/store/osSlice';
import { APP_LIST, AppDef } from '@/lib/appRegistry';
import { useIsMobile } from '@/hooks/useIsMobile';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
  search: Search, pen: Pen, barchart: BarChart2, folder: Folder,
  mail: Mail, calendar: Calendar, note: StickyNote, compass: Compass,
  mic: Mic, languages: Languages,
};

function AppIcon({ app, size = 64 }: { app: AppDef; size?: number }) {
  const LucideIcon = ICON_MAP[app.icon] || Globe;
  return <LucideIcon size={size * 0.44} color="#fff" strokeWidth={1.6} />;
}

interface Props {
  onLaunch: (app: AppDef) => void;
}

export default function AppDrawer({ onLaunch }: Props) {
  const dispatch = useAppDispatch();
  const open = useAppSelector(s => s.os.launcherOpen);
  const isMobile = useIsMobile();

  const handleClose = () => dispatch(closeLauncher());

  const pinnedApps = APP_LIST.filter(a => a.pinned);
  const moreApps = APP_LIST.filter(a => !a.pinned);
  const cols = isMobile ? 4 : 5;

  const gridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `repeat(${cols}, 1fr)`,
    gap: isMobile ? '20px 16px' : '28px 24px',
  };

  const iconSize = isMobile ? 52 : 64;

  return typeof window !== 'undefined' ? createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          key="launcher-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={handleClose}
          style={{
            position: 'fixed', inset: 0, zIndex: 9000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.55)',
            backdropFilter: 'blur(48px) saturate(180%)',
            WebkitBackdropFilter: 'blur(48px) saturate(180%)',
          }}
        >
          <motion.div
            key="launcher-panel"
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 16 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            onClick={e => e.stopPropagation()}
            style={{
              background: 'rgba(18,18,20,0.85)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '20px',
              boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
              padding: isMobile ? '24px 20px 28px' : '32px 40px 36px',
              maxWidth: isMobile ? '92vw' : '600px',
              width: '100%',
              maxHeight: '80vh',
              overflowY: 'auto',
              backdropFilter: 'blur(20px)',
            }}
          >
            {/* Core Apps */}
            <div style={{ marginBottom: isMobile ? '20px' : '28px' }}>
              <p style={{
                fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.35)',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                marginBottom: isMobile ? '14px' : '18px',
              }}>
                Core
              </p>
              <div style={gridStyle}>
                {pinnedApps.map(app => (
                  <AppButton key={app.id} app={app} iconSize={iconSize} isMobile={isMobile}
                    onClick={() => { onLaunch(app); handleClose(); }} />
                ))}
              </div>
            </div>

            <div style={{ height: '1px', background: 'rgba(255,255,255,0.07)', marginBottom: isMobile ? '20px' : '28px' }} />

            {/* More Apps */}
            <div>
              <p style={{
                fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.35)',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                marginBottom: isMobile ? '14px' : '18px',
              }}>
                More Apps
              </p>
              <div style={gridStyle}>
                {moreApps.map(app => (
                  <AppButton key={app.id} app={app} iconSize={iconSize} isMobile={isMobile}
                    onClick={() => { onLaunch(app); handleClose(); }} />
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  ) : null;
}

function AppButton({ app, iconSize, isMobile, onClick }: {
  app: AppDef; iconSize: number; isMobile: boolean; onClick: () => void;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.92 }}
      onClick={onClick}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
        background: 'none', border: 'none', cursor: 'pointer',
        padding: '4px', outline: 'none',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      <div style={{
        width: iconSize, height: iconSize,
        borderRadius: '14px',
        background: app.color,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: `0 4px 14px ${app.color}55, 0 1px 3px rgba(0,0,0,0.3)`,
        flexShrink: 0,
      }}>
        <AppIcon app={app} size={iconSize} />
      </div>
      <span style={{
        fontSize: isMobile ? '11px' : '12px', fontWeight: 500,
        color: 'rgba(255,255,255,0.85)',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: iconSize + 16,
        textShadow: '0 1px 3px rgba(0,0,0,0.4)',
      }}>
        {app.name}
      </span>
    </motion.button>
  );
}
