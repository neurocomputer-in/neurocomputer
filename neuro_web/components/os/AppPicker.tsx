'use client';
import { Drawer } from 'vaul';
import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass, Mic, Languages, Tv2,
} from 'lucide-react';
import { APP_LIST, AppDef } from '@/lib/appRegistry';
import { useIsMobile } from '@/hooks/useIsMobile';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
  search: Search, pen: Pen, barchart: BarChart2, folder: Folder,
  mail: Mail, calendar: Calendar, note: StickyNote, compass: Compass,
  mic: Mic, languages: Languages, tv: Tv2,
};

interface Props {
  onPick: (appId: string, tabKind: string) => void;
  onClose: () => void;
}

function AppGrid({ onPick }: { onPick: (app: AppDef) => void }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 8,
      padding: '8px 4px',
    }}>
      {APP_LIST.map(app => {
        const Icon = ICON_MAP[app.icon] || Globe;
        return (
          <button
            key={app.id}
            onClick={() => onPick(app)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              padding: '8px 4px',
              background: 'transparent', border: 'none', cursor: 'pointer', borderRadius: 8,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: app.color,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon size={18} color="#fff" strokeWidth={1.6} />
            </div>
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.7)', textAlign: 'center', lineHeight: 1.2, maxWidth: 52, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {app.name}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function AppPicker({ onPick, onClose }: Props) {
  const isMobile = useIsMobile();
  const handlePick = (app: AppDef) => onPick(app.id, app.tabKind);

  if (isMobile) {
    return (
      <Drawer.Root open onOpenChange={(open) => { if (!open) onClose(); }}>
        <Drawer.Portal>
          <Drawer.Overlay style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)' }} />
          <Drawer.Content style={{
            background: 'rgba(22,22,24,0.98)',
            borderTop: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '16px 16px 0 0',
            position: 'fixed', bottom: 0, left: 0, right: 0,
            padding: '16px 12px 32px',
            zIndex: 9999,
          }}>
            <div style={{ width: 36, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.15)', margin: '0 auto 16px' }} />
            <p style={{ fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: 8, paddingLeft: 4 }}>New tab</p>
            <AppGrid onPick={handlePick} />
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    );
  }

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, zIndex: 9000 }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(28,28,32,0.98)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 12,
          padding: '12px 8px',
          width: 260,
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          zIndex: 9001,
        }}
      >
        <p style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.7)', marginBottom: 8, paddingLeft: 4 }}>New tab</p>
        <AppGrid onPick={handlePick} />
      </div>
    </div>
  );
}
