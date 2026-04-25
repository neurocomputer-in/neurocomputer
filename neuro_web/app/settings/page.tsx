'use client';
import { Suspense, useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useIsMobile } from '@/hooks/useIsMobile';
import { ArrowLeft, User, Key, Monitor, Mic as MicIcon, Waves, Info, Library, Plus, Trash2, Pin, PinOff } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setTabBarPosition, setLiveWallpaperEnabled, setInterfaceMode } from '@/store/uiSlice';
import { updateWorkspace } from '@/store/workspaceSlice';
import { THEME_LIST, getTheme } from '@/theme/presets';
import { apiGetLlmProviders, apiGetModelLibrary, apiPutModelLibrary } from '@/services/api';
import { LlmProviderInfo, ModelAlias, ModelLibrary, ModelRole } from '@/types';

type TabId =
  | 'profile'
  | 'api-keys'
  | 'models'
  | 'appearance'
  | 'voice'
  | 'background'
  | 'about';

const TABS: { id: TabId; label: string; icon: any }[] = [
  { id: 'profile',    label: 'Profile',    icon: User },
  { id: 'api-keys',   label: 'API Keys',   icon: Key },
  { id: 'models',     label: 'Model Library', icon: Library },
  { id: 'appearance', label: 'Appearance', icon: Monitor },
  { id: 'voice',      label: 'Voice & Audio', icon: MicIcon },
  { id: 'background', label: 'Background', icon: Waves },
  { id: 'about',      label: 'About',      icon: Info },
];

export default function SettingsPage() {
  // Next.js 14+ requires useSearchParams() consumers to live under a
  // Suspense boundary; without this the route fails to pre-render and
  // returns 404. Keep all the page body inside SettingsPageInner.
  return (
    <Suspense fallback={null}>
      <SettingsPageInner />
    </Suspense>
  );
}

function SettingsPageInner() {
  const search = useSearchParams();
  const isMobile = useIsMobile();
  const initialTab = (search.get('tab') as TabId) || 'profile';
  const [tab, setTab] = useState<TabId>(initialTab);
  // Mobile: show nav list (false) or content panel (true)
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    const q = search.get('tab') as TabId | null;
    if (q && TABS.some(t => t.id === q)) setTab(q);
  }, [search]);

  const navPanel = (
    <aside style={{
      width: isMobile ? '100%' : '240px',
      flexShrink: 0,
      background: '#0f1011',
      borderRight: isMobile ? 'none' : '1px solid rgba(255,255,255,0.05)',
      display: 'flex', flexDirection: 'column',
      minHeight: 0,
    }}>
      <div style={{ padding: '18px 18px 12px' }}>
        <Link href="/" style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          color: '#8a8f98', fontSize: '13px', textDecoration: 'none',
          padding: '6px 8px', borderRadius: '6px',
          minHeight: '40px',
        }}>
          <ArrowLeft size={14} /> Back to chat
        </Link>
      </div>
      <div style={{
        fontSize: '11px', textTransform: 'uppercase',
        letterSpacing: '0.8px', color: '#62666d', fontWeight: 510,
        padding: '8px 20px 10px',
      }}>
        Settings
      </div>
      <nav style={{ flex: 1, padding: '0 8px 16px', display: 'flex', flexDirection: 'column', gap: '2px', overflowY: 'auto' }}>
        {TABS.map(t => {
          const active = t.id === tab;
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); if (isMobile) setShowContent(true); }}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: isMobile ? '14px 14px' : '9px 12px',
                borderRadius: '8px',
                background: active ? 'rgba(94,106,210,0.12)' : 'transparent',
                border: '1px solid ' + (active ? 'rgba(94,106,210,0.2)' : 'transparent'),
                color: active ? '#f7f8f8' : '#d0d6e0',
                fontSize: isMobile ? '15px' : '13px',
                fontWeight: active ? 510 : 400,
                cursor: 'pointer', textAlign: 'left',
                transition: 'background 0.12s',
                touchAction: 'manipulation',
                WebkitTapHighlightColor: 'transparent',
              }}
            >
              <Icon size={isMobile ? 16 : 14} color={active ? '#c4b5fd' : '#8a8f98'} />
              <span>{t.label}</span>
              {isMobile && <ArrowLeft size={14} color="#4a4f58" style={{ marginLeft: 'auto', transform: 'rotate(180deg)' }} />}
            </button>
          );
        })}
      </nav>
    </aside>
  );

  const contentPanel = (
    <main style={{ flex: 1, overflow: 'auto', padding: isMobile ? '20px 16px' : '40px 48px', minHeight: 0 }}>
      {isMobile && (
        <button
          onClick={() => setShowContent(false)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            color: '#8a8f98', fontSize: '13px', background: 'transparent',
            border: 'none', cursor: 'pointer', padding: '6px 0', marginBottom: '16px',
            touchAction: 'manipulation',
          }}
        >
          <ArrowLeft size={14} /> Settings
        </button>
      )}
      <div style={{ maxWidth: '760px' }}>
        {tab === 'profile'    && <ProfileSection />}
        {tab === 'api-keys'   && <ApiKeysSection />}
        {tab === 'models'     && <ModelLibrarySection />}
        {tab === 'appearance' && <AppearanceSection />}
        {tab === 'voice'      && <VoiceSection />}
        {tab === 'background' && <BackgroundSection />}
        {tab === 'about'      && <AboutSection />}
      </div>
    </main>
  );

  return (
    <div style={{
      display: 'flex', height: 'var(--app-height, 100vh)',
      background: '#0a0a0b', color: '#d0d6e0', overflow: 'hidden',
      flexDirection: isMobile ? 'column' : 'row',
    }}>
      {isMobile
        ? (!showContent ? navPanel : contentPanel)
        : <>{navPanel}{contentPanel}</>
      }
    </div>
  );
}

// ── Section components ───────────────────────────────────────────────

function SectionHeader({ title, description }: { title: string; description?: string }) {
  return (
    <header style={{ marginBottom: '28px' }}>
      <h1 style={{
        fontSize: '24px', fontWeight: 590, color: '#f7f8f8',
        margin: 0, marginBottom: '6px', letterSpacing: '-0.4px',
      }}>{title}</h1>
      {description && (
        <p style={{ color: '#8a8f98', fontSize: '13px', margin: 0 }}>{description}</p>
      )}
    </header>
  );
}

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div style={{
      padding: '16px 0',
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
      gap: '16px', flexWrap: 'wrap',
    }}>
      <div style={{ flex: '1 1 140px', minWidth: 0 }}>
        <div style={{ fontSize: '13px', color: '#f7f8f8', fontWeight: 510, marginBottom: '4px' }}>{label}</div>
        {description && <div style={{ fontSize: '12px', color: '#8a8f98' }}>{description}</div>}
      </div>
      <div style={{ flexShrink: 0, maxWidth: '100%' }}>{children}</div>
    </div>
  );
}

function SegmentedControl<T extends string>({ value, options, onChange }: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div style={{
      display: 'flex', background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px',
      padding: '2px',
    }}>
      {options.map(o => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              padding: '5px 12px',
              background: active ? 'rgba(94,106,210,0.15)' : 'transparent',
              color: active ? '#f7f8f8' : '#8a8f98',
              border: 'none', borderRadius: '4px',
              fontSize: '12px', fontWeight: active ? 510 : 400,
              cursor: 'pointer',
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      style={{
        width: '36px', height: '20px', borderRadius: '999px',
        background: checked ? '#5e6ad2' : 'rgba(255,255,255,0.08)',
        border: 'none', cursor: 'pointer',
        position: 'relative', transition: 'background 0.15s',
      }}
    >
      <span style={{
        position: 'absolute', top: '2px',
        left: checked ? '18px' : '2px',
        width: '16px', height: '16px', borderRadius: '50%',
        background: '#fff', transition: 'left 0.15s',
      }} />
    </button>
  );
}

function ProfileSection() {
  return (
    <>
      <SectionHeader title="Profile" description="Your identity across Neuro sessions." />
      <Row label="Display name" description="Shown in future collaborative features.">
        <input
          placeholder="Not set"
          style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px', padding: '8px 10px', color: '#f7f8f8',
            fontSize: '14px', outline: 'none', width: '100%', maxWidth: '280px', minWidth: '120px',
          }}
        />
      </Row>
      <Row label="Email" description="Used for account sync (future).">
        <input
          placeholder="you@example.com"
          style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px', padding: '8px 10px', color: '#f7f8f8',
            fontSize: '14px', outline: 'none', width: '100%', maxWidth: '280px', minWidth: '120px',
          }}
        />
      </Row>
    </>
  );
}

function ApiKeysSection() {
  return (
    <>
      <SectionHeader
        title="API Keys"
        description="Provide keys here and Neuro will use them instead of env-vars. Keys are stored in your local .env; nothing is sent to a remote server."
      />
      {['OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'OPENCODE_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY'].map(k => (
        <Row key={k} label={k} description="Persisted locally on save.">
          <input
            type="password"
            placeholder="sk-..."
            style={{
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px', padding: '8px 10px', color: '#f7f8f8',
              fontSize: '13px', fontFamily: 'monospace', outline: 'none',
              width: '100%', maxWidth: '300px', minWidth: '120px',
            }}
          />
        </Row>
      ))}
      <p style={{ marginTop: '16px', fontSize: '12px', color: '#62666d', fontStyle: 'italic' }}>
        Save endpoint not wired yet — UI scaffold only.
      </p>
    </>
  );
}

function AppearanceSection() {
  const dispatch = useAppDispatch();
  const tabBarPosition = useAppSelector(s => s.ui.tabBarPosition);
  const interfaceMode = useAppSelector(s => s.ui.interfaceMode);
  const workspaces = useAppSelector(s => s.workspace.workspaces);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const activeWorkspace = workspaces.find(w => w.id === selectedWorkspaceId);
  const currentTheme = getTheme(activeWorkspace?.theme);

  const onThemeChange = async (themeId: string) => {
    if (!activeWorkspace) return;
    await dispatch(updateWorkspace({
      id: activeWorkspace.id,
      patch: { theme: themeId },
    }));
  };

  return (
    <>
      <SectionHeader
        title="Appearance"
        description={activeWorkspace
          ? `Layout and theme controls for ${activeWorkspace.name}. Theme applies per-workspace — switch workspace to tweak another's theme.`
          : 'Layout controls. Select a workspace to configure its theme.'}
      />
      <Row label="Interface mode"
           description="Switch between classic tabs and a 3D spatial view of your open sessions.">
        <SegmentedControl
          value={interfaceMode}
          options={[
            { value: 'classic', label: 'Classic' },
            { value: 'spatial', label: '3D' },
          ]}
          onChange={v => dispatch(setInterfaceMode(v))}
        />
      </Row>
      <Row label="Tab bar position" description="Where conversation tabs sit relative to the chat area.">
        <SegmentedControl
          value={tabBarPosition}
          options={[
            { value: 'bottom', label: 'Bottom' },
            { value: 'top',    label: 'Top' },
          ]}
          onChange={v => dispatch(setTabBarPosition(v))}
        />
      </Row>
      <div style={{ padding: '16px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: '13px', color: '#f7f8f8', fontWeight: 510, marginBottom: '4px' }}>
          Workspace theme {activeWorkspace && <span style={{ color: '#8a8f98', fontWeight: 400 }}>· {activeWorkspace.name}</span>}
        </div>
        <div style={{ fontSize: '12px', color: '#8a8f98', marginBottom: '12px' }}>
          Tokens (accent, background, wallpaper) applied instantly to this workspace.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' }}>
          {THEME_LIST.map(t => {
            const active = t.id === currentTheme.id;
            return (
              <button
                key={t.id}
                disabled={!activeWorkspace}
                onClick={() => onThemeChange(t.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '10px 12px', borderRadius: '8px', textAlign: 'left',
                  background: active ? 'rgba(94,106,210,0.12)' : 'rgba(255,255,255,0.02)',
                  border: '1px solid ' + (active ? 'rgba(94,106,210,0.3)' : 'rgba(255,255,255,0.06)'),
                  cursor: activeWorkspace ? 'pointer' : 'not-allowed',
                  opacity: activeWorkspace ? 1 : 0.4,
                  color: '#d0d6e0', fontFamily: 'inherit',
                }}
              >
                <span style={{
                  width: '18px', height: '18px', borderRadius: '50%',
                  background: t.swatch, flexShrink: 0,
                  border: '1px solid rgba(255,255,255,0.15)',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '12px', fontWeight: 510 }}>{t.label}</div>
                  <div style={{ fontSize: '10px', color: '#62666d', marginTop: '2px',
                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}

function VoiceSection() {
  const dispatch = useAppDispatch();
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);

  return (
    <>
      <SectionHeader title="Voice & Audio" description="Voice-call and TTS behaviour." />
      <Row label="Auto-play TTS" description="Speak assistant replies aloud when they arrive.">
        <Toggle checked={ttsAutoPlay} onChange={v => dispatch({ type: 'ui/setTtsAutoPlay', payload: v })} />
      </Row>
      <p style={{ marginTop: '16px', fontSize: '12px', color: '#62666d', fontStyle: 'italic' }}>
        More voice settings (STT provider, voice model, VAD sensitivity) coming soon.
      </p>
    </>
  );
}

function BackgroundSection() {
  const dispatch = useAppDispatch();
  const liveWallpaperEnabled = useAppSelector(s => s.ui.liveWallpaperEnabled);
  return (
    <>
      <SectionHeader title="Background" description="The 3D animated wallpaper behind the app." />
      <Row label="Live 3D wallpaper" description="Disable for lower GPU/CPU usage.">
        <Toggle checked={liveWallpaperEnabled} onChange={v => dispatch(setLiveWallpaperEnabled(v))} />
      </Row>
    </>
  );
}

function AboutSection() {
  return (
    <>
      <SectionHeader title="About" description="Build info." />
      <Row label="App" description="Neuro Desktop / Web"><span style={{ color: '#8a8f98', fontSize: '12px' }}>dev</span></Row>
      <Row label="Backend port"><span style={{ color: '#8a8f98', fontSize: '12px', fontFamily: 'monospace' }}>7001</span></Row>
      <Row label="Frontend port"><span style={{ color: '#8a8f98', fontSize: '12px', fontFamily: 'monospace' }}>3000 / 3002</span></Row>
    </>
  );
}

// ── Model Library ────────────────────────────────────────────────────

const fieldStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '6px',
  padding: '6px 10px',
  color: '#f7f8f8',
  fontSize: '12px',
  outline: 'none',
  width: '100%',
  fontFamily: 'inherit',
};

const selectStyle: React.CSSProperties = { ...fieldStyle, appearance: 'auto' };

const buttonStyle: React.CSSProperties = {
  background: 'rgba(94,106,210,0.15)',
  border: '1px solid rgba(94,106,210,0.3)',
  color: '#c4b5fd',
  borderRadius: '6px',
  padding: '6px 12px',
  fontSize: '12px',
  cursor: 'pointer',
  fontFamily: 'inherit',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
};

const ghostButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: 'transparent',
  border: '1px solid rgba(255,255,255,0.1)',
  color: '#8a8f98',
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.02)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '8px',
  padding: '14px',
  marginBottom: '10px',
};

const labelStyle: React.CSSProperties = {
  fontSize: '10px',
  textTransform: 'uppercase',
  letterSpacing: '0.6px',
  color: '#62666d',
  fontWeight: 510,
  marginBottom: '4px',
  display: 'block',
};

function slugify(s: string): string {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function ModelLibrarySection() {
  const [lib, setLib] = useState<ModelLibrary | null>(null);
  const [providers, setProviders] = useState<LlmProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([apiGetModelLibrary(), apiGetLlmProviders()])
      .then(([l, p]) => { setLib(l); setProviders(p.providers); })
      .catch(e => setError(String(e?.message || e)))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    if (!lib) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await apiPutModelLibrary(lib);
      setLib(saved);
      setNotice('Saved.');
      setTimeout(() => setNotice(null), 2000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const addAlias = () => {
    if (!lib) return;
    let slug = 'new-alias';
    let i = 1;
    while (lib.aliases[slug]) { slug = `new-alias-${++i}`; }
    const first = providers[0];
    const newAlias: ModelAlias = {
      display_name: 'New Alias',
      description: '',
      provider: first?.id || 'openrouter',
      model_id: first?.defaultModel || '',
    };
    setLib({ ...lib, aliases: { ...lib.aliases, [slug]: newAlias } });
  };

  const updateAlias = (slug: string, patch: Partial<ModelAlias>) => {
    if (!lib) return;
    setLib({ ...lib, aliases: { ...lib.aliases, [slug]: { ...lib.aliases[slug], ...patch } } });
  };

  const renameAlias = (oldSlug: string, newSlug: string) => {
    if (!lib || !newSlug || newSlug === oldSlug) return;
    if (lib.aliases[newSlug]) { setError(`Alias '${newSlug}' already exists`); return; }
    const { [oldSlug]: alias, ...rest } = lib.aliases;
    const nextAliases = { ...rest, [newSlug]: alias };
    // Update any role references
    const nextRoles: Record<string, ModelRole> = {};
    for (const [rslug, r] of Object.entries(lib.roles)) {
      nextRoles[rslug] = {
        ...r,
        candidates: r.candidates.map(c => c === oldSlug ? newSlug : c),
        pinned: r.pinned === oldSlug ? newSlug : r.pinned,
      };
    }
    setLib({ aliases: nextAliases, roles: nextRoles });
  };

  const deleteAlias = (slug: string) => {
    if (!lib) return;
    // Reject if any role references it
    const blockers = Object.entries(lib.roles)
      .filter(([, r]) => r.candidates.includes(slug))
      .map(([s]) => s);
    if (blockers.length) {
      setError(`Alias '${slug}' is used by role(s): ${blockers.join(', ')}`);
      return;
    }
    const { [slug]: _, ...rest } = lib.aliases;
    setLib({ ...lib, aliases: rest });
  };

  const addRole = () => {
    if (!lib) return;
    let slug = 'new-role';
    let i = 1;
    while (lib.roles[slug]) { slug = `new-role-${++i}`; }
    const firstAlias = Object.keys(lib.aliases)[0];
    if (!firstAlias) { setError('Create at least one alias before adding a role'); return; }
    const role: ModelRole = {
      display_name: 'New Role',
      description: '',
      candidates: [firstAlias],
      pinned: firstAlias,
    };
    setLib({ ...lib, roles: { ...lib.roles, [slug]: role } });
  };

  const updateRole = (slug: string, patch: Partial<ModelRole>) => {
    if (!lib) return;
    setLib({ ...lib, roles: { ...lib.roles, [slug]: { ...lib.roles[slug], ...patch } } });
  };

  const renameRole = (oldSlug: string, newSlug: string) => {
    if (!lib || !newSlug || newSlug === oldSlug) return;
    if (lib.roles[newSlug]) { setError(`Role '${newSlug}' already exists`); return; }
    const { [oldSlug]: role, ...rest } = lib.roles;
    setLib({ ...lib, roles: { ...rest, [newSlug]: role } });
  };

  const deleteRole = (slug: string) => {
    if (!lib) return;
    const { [slug]: _, ...rest } = lib.roles;
    setLib({ ...lib, roles: rest });
  };

  const toggleCandidate = (roleSlug: string, aliasSlug: string) => {
    if (!lib) return;
    const r = lib.roles[roleSlug];
    const has = r.candidates.includes(aliasSlug);
    let next = has ? r.candidates.filter(c => c !== aliasSlug) : [...r.candidates, aliasSlug];
    if (next.length === 0) { setError('A role needs at least one candidate'); return; }
    const pinned = next.includes(r.pinned) ? r.pinned : next[0];
    updateRole(roleSlug, { candidates: next, pinned });
  };

  const pinCandidate = (roleSlug: string, aliasSlug: string) => {
    if (!lib) return;
    const r = lib.roles[roleSlug];
    if (!r.candidates.includes(aliasSlug)) return;
    updateRole(roleSlug, { pinned: aliasSlug });
  };

  if (loading) return (<><SectionHeader title="Model Library" /><p style={{ color: '#8a8f98', fontSize: '13px' }}>Loading…</p></>);
  if (!lib) return (<><SectionHeader title="Model Library" /><p style={{ color: '#f87171', fontSize: '13px' }}>{error || 'Failed to load'}</p></>);

  return (
    <>
      <SectionHeader
        title="Model Library"
        description="Named model aliases grouped into roles. Skills and chat sessions pick a role; swap the pinned alias to change the model everywhere that role is used."
      />
      {error && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.25)', color: '#fca5a5', padding: '10px 12px', borderRadius: '6px', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}
      {notice && (
        <div style={{ background: 'rgba(94,234,212,0.08)', border: '1px solid rgba(94,234,212,0.25)', color: '#7dd3fc', padding: '10px 12px', borderRadius: '6px', fontSize: '12px', marginBottom: '12px' }}>
          {notice}
        </div>
      )}

      {/* Aliases */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', marginBottom: '10px' }}>
        <h2 style={{ fontSize: '15px', color: '#f7f8f8', fontWeight: 590, margin: 0 }}>Aliases</h2>
        <button style={buttonStyle} onClick={addAlias}><Plus size={12} /> Add alias</button>
      </div>
      {Object.keys(lib.aliases).length === 0 && (
        <p style={{ color: '#62666d', fontSize: '12px', fontStyle: 'italic' }}>No aliases. Add one to get started.</p>
      )}
      {Object.entries(lib.aliases).map(([slug, a]) => {
        const providerCfg = providers.find(p => p.id === a.provider);
        return (
          <div key={slug} style={cardStyle}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={labelStyle}>Slug</label>
                <input
                  style={{ ...fieldStyle, fontFamily: "'Berkeley Mono', ui-monospace, monospace" }}
                  defaultValue={slug}
                  onBlur={e => renameAlias(slug, slugify(e.target.value))}
                />
              </div>
              <div>
                <label style={labelStyle}>Display name</label>
                <input
                  style={fieldStyle}
                  value={a.display_name}
                  onChange={e => updateAlias(slug, { display_name: e.target.value })}
                />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={labelStyle}>Description</label>
                <input
                  style={fieldStyle}
                  value={a.description}
                  onChange={e => updateAlias(slug, { description: e.target.value })}
                  placeholder="e.g. Deep reflective, expensive"
                />
              </div>
              <div>
                <label style={labelStyle}>Provider</label>
                <select
                  style={selectStyle}
                  value={a.provider}
                  onChange={e => {
                    const nextProv = e.target.value;
                    const nextProvCfg = providers.find(p => p.id === nextProv);
                    updateAlias(slug, { provider: nextProv, model_id: nextProvCfg?.defaultModel || a.model_id });
                  }}
                >
                  {providers.map(p => <option key={p.id} value={p.id}>{p.name}{p.available ? '' : ' (no key)'}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Model</label>
                <select
                  style={{ ...selectStyle, fontFamily: "'Berkeley Mono', ui-monospace, monospace", fontSize: '11px' }}
                  value={providerCfg?.models.includes(a.model_id) ? a.model_id : ''}
                  onChange={e => updateAlias(slug, { model_id: e.target.value })}
                >
                  {!providerCfg?.models.includes(a.model_id) && a.model_id && (
                    <option value="">{a.model_id} (not in catalog)</option>
                  )}
                  {(providerCfg?.models || []).map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                style={{ ...ghostButtonStyle, color: '#f87171', borderColor: 'rgba(248,113,113,0.2)' }}
                onClick={() => deleteAlias(slug)}
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          </div>
        );
      })}

      {/* Roles */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '24px', marginBottom: '10px' }}>
        <h2 style={{ fontSize: '15px', color: '#f7f8f8', fontWeight: 590, margin: 0 }}>Roles</h2>
        <button style={buttonStyle} onClick={addRole}><Plus size={12} /> Add role</button>
      </div>
      {Object.keys(lib.roles).length === 0 && (
        <p style={{ color: '#62666d', fontSize: '12px', fontStyle: 'italic' }}>No roles yet.</p>
      )}
      {Object.entries(lib.roles).map(([slug, r]) => (
        <div key={slug} style={cardStyle}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={labelStyle}>Slug</label>
              <input
                style={{ ...fieldStyle, fontFamily: "'Berkeley Mono', ui-monospace, monospace" }}
                defaultValue={slug}
                onBlur={e => renameRole(slug, slugify(e.target.value))}
              />
            </div>
            <div>
              <label style={labelStyle}>Display name</label>
              <input
                style={fieldStyle}
                value={r.display_name}
                onChange={e => updateRole(slug, { display_name: e.target.value })}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={labelStyle}>Description</label>
              <input
                style={fieldStyle}
                value={r.description}
                onChange={e => updateRole(slug, { description: e.target.value })}
              />
            </div>
          </div>
          <div style={{ marginTop: '12px' }}>
            <label style={labelStyle}>Candidates (check to include, pin icon to select default)</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {Object.entries(lib.aliases).map(([aSlug, a]) => {
                const included = r.candidates.includes(aSlug);
                const isPinned = r.pinned === aSlug;
                return (
                  <div key={aSlug} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '6px 8px', borderRadius: '4px',
                    background: isPinned ? 'rgba(94,106,210,0.08)' : 'transparent',
                  }}>
                    <input
                      type="checkbox"
                      checked={included}
                      onChange={() => toggleCandidate(slug, aSlug)}
                    />
                    <span style={{ fontSize: '12px', color: '#f7f8f8', fontWeight: included ? 510 : 400, flex: 1 }}>
                      {a.display_name} <span style={{ color: '#62666d', fontFamily: "'Berkeley Mono', ui-monospace, monospace", fontSize: '10px' }}>({aSlug})</span>
                    </span>
                    <button
                      onClick={() => pinCandidate(slug, aSlug)}
                      disabled={!included}
                      title={isPinned ? 'Pinned' : 'Pin as default'}
                      style={{
                        ...ghostButtonStyle,
                        padding: '3px 6px',
                        opacity: included ? 1 : 0.35,
                        color: isPinned ? '#c4b5fd' : '#8a8f98',
                        borderColor: isPinned ? 'rgba(94,106,210,0.4)' : 'rgba(255,255,255,0.1)',
                      }}
                    >
                      {isPinned ? <Pin size={12} /> : <PinOff size={12} />}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              style={{ ...ghostButtonStyle, color: '#f87171', borderColor: 'rgba(248,113,113,0.2)' }}
              onClick={() => deleteRole(slug)}
            >
              <Trash2 size={12} /> Delete
            </button>
          </div>
        </div>
      ))}

      <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
        <button
          style={buttonStyle}
          onClick={save}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Save library'}
        </button>
      </div>
    </>
  );
}
