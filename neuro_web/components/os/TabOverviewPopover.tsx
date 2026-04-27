'use client';
import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass, Mic, Languages, Tv2,
} from 'lucide-react';
import { WindowTab } from '@/types';
import { APP_MAP } from '@/lib/appRegistry';

const ICON_MAP: Record<string, any> = {
  brain: Brain, globe: Globe, code: Code, briefcase: Briefcase,
  terminal: Terminal, layers: Layers,
  search: Search, pen: Pen, barchart: BarChart2, folder: Folder,
  mail: Mail, calendar: Calendar, note: StickyNote, compass: Compass,
  mic: Mic, languages: Languages, tv: Tv2,
};

interface Props {
  tabs: WindowTab[];
  activeTabId: string;
  onActivate: (tabId: string) => void;
  onClose: () => void;
}

export default function TabOverviewPopover({ tabs, activeTabId, onActivate, onClose }: Props) {
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 9500 }}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute', top: 44, right: 12,
          background: 'rgba(28,28,32,0.98)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 10,
          padding: '8px',
          width: 240,
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          display: 'flex', flexDirection: 'column', gap: 2,
        }}
      >
        <p style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.5)', padding: '0 4px 4px', margin: 0 }}>
          All tabs ({tabs.length})
        </p>
        {tabs.map(tab => {
          const app = APP_MAP[tab.appId as keyof typeof APP_MAP];
          const Icon = app ? (ICON_MAP[app.icon] || Globe) : Globe;
          const color = app?.color ?? '#888';
          const isActive = tab.id === activeTabId;
          return (
            <button
              key={tab.id}
              onClick={() => onActivate(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 8px', borderRadius: 6,
                background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
                border: 'none', cursor: 'pointer', textAlign: 'left', width: '100%',
              }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
            >
              <Icon size={13} color={color} strokeWidth={1.8} />
              <span style={{ fontSize: 12, color: isActive ? '#e0e0e0' : '#888', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {tab.title}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
