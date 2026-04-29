'use client';
import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { useAppSelector } from '@/store/hooks';
import { APP_MAP, AppDef } from '@/lib/appRegistry';
import AppIconView from './AppIconView';

const ICONS_ROW_H = 52;
const HANDLE_H = 14;

function WindowsGrid() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <rect x="0" y="0" width="6.5" height="6.5" rx="1.2" fill="white" opacity="0.95" />
      <rect x="8.5" y="0" width="6.5" height="6.5" rx="1.2" fill="white" opacity="0.95" />
      <rect x="0" y="8.5" width="6.5" height="6.5" rx="1.2" fill="white" opacity="0.95" />
      <rect x="8.5" y="8.5" width="6.5" height="6.5" rx="1.2" fill="white" opacity="0.95" />
    </svg>
  );
}

function DockIcon({ appId, onLaunch }: { appId: string; onLaunch: (app: AppDef) => void }) {
  const app = APP_MAP[appId as keyof typeof APP_MAP];
  const tapRef = useRef<{ t: number; x: number; y: number } | null>(null);
  const iconRef = useRef<HTMLDivElement>(null);

  if (!app) return null;

  return (
    <div
      onPointerDown={(e) => {
        tapRef.current = { t: Date.now(), x: e.clientX, y: e.clientY };
        if (iconRef.current) iconRef.current.style.transform = 'scale(0.88)';
      }}
      onPointerUp={(e) => {
        if (iconRef.current) iconRef.current.style.transform = 'scale(1)';
        if (!tapRef.current) return;
        const elapsed = Date.now() - tapRef.current.t;
        const dist = Math.hypot(e.clientX - tapRef.current.x, e.clientY - tapRef.current.y);
        tapRef.current = null;
        if (elapsed < 300 && dist < 10) onLaunch(app);
      }}
      onPointerLeave={() => { tapRef.current = null; if (iconRef.current) iconRef.current.style.transform = 'scale(1)'; }}
      onPointerCancel={() => { tapRef.current = null; if (iconRef.current) iconRef.current.style.transform = 'scale(1)'; }}
    >
      <div
        ref={iconRef}
        style={{
          width: 38, height: 38, borderRadius: 11,
          background: app.iconImage ? 'transparent' : `linear-gradient(145deg, ${app.color}ee 0%, ${app.color}88 100%)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: `0 2px 6px ${app.color}44`,
          overflow: 'hidden',
          cursor: 'pointer',
          transition: 'transform 0.1s',
        }}
      >
        {app.iconImage ? <AppIconView app={app} fill /> : <AppIconView app={app} size={22} />}
      </div>
    </div>
  );
}

export default function MobileDock({ onLaunch, onLauncherOpen }: {
  onLaunch: (app: AppDef) => void;
  onLauncherOpen: () => void;
}) {
  const mobileDock = useAppSelector(s => s.icons.mobileDock);
  const [visible, setVisible] = useState(true);
  const launchRef = useRef<HTMLDivElement>(null);

  const left = mobileDock.slice(0, 2);
  const right = mobileDock.slice(2, 4);

  return (
    <motion.div
      animate={{ y: visible ? 0 : ICONS_ROW_H }}
      transition={{ type: 'spring', stiffness: 440, damping: 40, mass: 0.65 }}
      style={{ position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 10, pointerEvents: 'auto' }}
    >
      {/* Handle strip */}
      <div
        onClick={() => setVisible(v => !v)}
        style={{
          height: HANDLE_H,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(14,14,18,0.6)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderTop: '1px solid rgba(255,255,255,0.07)',
          borderRadius: '7px 7px 0 0',
          cursor: 'pointer',
          gap: 5,
        }}
      >
        <motion.svg
          width="10" height="6" viewBox="0 0 10 6"
          animate={{ rotate: visible ? 0 : 180 }}
          transition={{ duration: 0.2 }}
          style={{ display: 'block' }}
        >
          <polyline
            points="1,5 5,1.5 9,5"
            fill="none"
            stroke="rgba(255,255,255,0.28)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </motion.svg>
      </div>

      {/* Icon row */}
      <div style={{
        height: ICONS_ROW_H,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 14,
        padding: '0 18px',
        paddingBottom: 'max(env(safe-area-inset-bottom), 8px)',
        background: 'rgba(14,14,18,0.82)',
        backdropFilter: 'blur(28px) saturate(180%)',
        WebkitBackdropFilter: 'blur(28px) saturate(180%)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        boxSizing: 'border-box',
      }}>
        {left.map(appId => (
          <DockIcon key={appId} appId={appId} onLaunch={onLaunch} />
        ))}

        {/* Windows-style launcher */}
        <div
          ref={launchRef}
          style={{
            width: 40, height: 40, borderRadius: '50%',
            background: 'linear-gradient(135deg, #5e6ad2 0%, #7170ff 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 12px rgba(94,106,210,0.5)',
            cursor: 'pointer', flexShrink: 0,
            transition: 'transform 0.1s',
            userSelect: 'none',
          }}
          onPointerDown={() => { if (launchRef.current) launchRef.current.style.transform = 'scale(0.88)'; }}
          onPointerUp={() => { if (launchRef.current) launchRef.current.style.transform = 'scale(1)'; onLauncherOpen(); }}
          onPointerLeave={() => { if (launchRef.current) launchRef.current.style.transform = 'scale(1)'; }}
          onPointerCancel={() => { if (launchRef.current) launchRef.current.style.transform = 'scale(1)'; }}
        >
          <WindowsGrid />
        </div>

        {right.map(appId => (
          <DockIcon key={appId} appId={appId} onLaunch={onLaunch} />
        ))}
      </div>
    </motion.div>
  );
}
