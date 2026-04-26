'use client';
import { useState } from 'react';
import { Drawer } from 'vaul';
import { Building2, LayoutGrid, X } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { ProjectListPanel } from '@/components/project/ProjectPanel';
import WorkspaceSwitcher from '@/components/workspace/WorkspaceSwitcher';

interface Props {
  open: boolean;
  onClose: () => void;
  onSwitcherOpen: () => void;
}

const sheetStyle: React.CSSProperties = {
  position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 600,
  background: 'rgba(16,16,20,0.99)',
  border: '1px solid rgba(255,255,255,0.09)',
  borderRadius: '14px 14px 0 0',
  outline: 'none',
  maxHeight: '85vh',
  display: 'flex', flexDirection: 'column',
};

export default function MobileControlSheet({ open, onClose, onSwitcherOpen }: Props) {
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const [wsSwitcherOpen, setWsSwitcherOpen] = useState(false);

  const currentWs = workspaces.find(w => w.id === selectedWorkspaceId);

  const handleOpenWsSwitcher = () => {
    onClose();
    setTimeout(() => setWsSwitcherOpen(true), 200);
  };

  return (
    <>
      <Drawer.Root open={open} onOpenChange={(o) => !o && onClose()}>
        <Drawer.Portal>
          <Drawer.Overlay style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 599 }} />
          <Drawer.Content style={sheetStyle}>
            {/* Handle */}
            <div style={{ width: 36, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.18)', margin: '12px auto 0', flexShrink: 0 }} />

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 0' }}>
              {/* Workspace row */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#62666d', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Workspace</div>
                <div
                  onClick={handleOpenWsSwitcher}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                    borderRadius: 10, cursor: 'pointer',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    transition: 'background 0.12s',
                  }}
                  onPointerDown={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
                  onPointerUp={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                  onPointerLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                >
                  {currentWs ? (
                    <div style={{
                      width: 36, height: 36, borderRadius: 9,
                      background: `linear-gradient(135deg, ${currentWs.color}ee, ${currentWs.color}88)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 16, fontWeight: 700, color: '#fff', flexShrink: 0,
                    }}>
                      {currentWs.name[0]?.toUpperCase()}
                    </div>
                  ) : (
                    <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <Building2 size={16} color="#62666d" />
                    </div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#f7f8f8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {currentWs?.name ?? 'No Workspace'}
                    </div>
                    <div style={{ fontSize: 11, color: '#62666d', marginTop: 1 }}>Tap to switch</div>
                  </div>
                  <span style={{ fontSize: 16, color: 'rgba(255,255,255,0.25)' }}>›</span>
                </div>
              </div>

              {/* Projects section */}
              <ProjectListPanel onClose={onClose} />

              {/* Divider */}
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '16px 0 12px' }} />

              {/* Quick actions */}
              <button
                onClick={() => { onClose(); onSwitcherOpen(); }}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 12,
                  padding: '11px 12px', borderRadius: 10, cursor: 'pointer',
                  background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                  marginBottom: 8, transition: 'background 0.12s',
                }}
                onPointerDown={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
                onPointerUp={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                onPointerLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
              >
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(94,106,210,0.14)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <LayoutGrid size={15} color="#7170ff" />
                </div>
                <span style={{ fontSize: 14, color: '#d0d4dc', fontWeight: 500 }}>App Switcher</span>
              </button>
            </div>

            <div style={{ height: 'max(env(safe-area-inset-bottom), 16px)', flexShrink: 0 }} />
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>

      <WorkspaceSwitcher open={wsSwitcherOpen} onClose={() => setWsSwitcherOpen(false)} />
    </>
  );
}
