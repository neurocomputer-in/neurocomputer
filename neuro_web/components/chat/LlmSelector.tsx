'use client';
import { CSSProperties, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import {
  apiGetConversationLlm,
  apiGetConversationRole,
  apiGetLlmProviders,
  apiGetModelLibrary,
  apiGetOpenCodeProviders,
  apiSetOpenCodeModel,
  apiUpdateConversationLlm,
  apiUpdateConversationRole,
} from '@/services/api';
import { LlmProviderInfo, ModelLibrary } from '@/types';

type Mode = 'role' | 'raw';

export default function LlmSelector() {
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeAgent = useMemo(() => {
    const tab = openTabs.find(t => t.cid === activeTabCid);
    return tab?.agentId || 'neuro';
  }, [openTabs, activeTabCid]);

  const [providers, setProviders] = useState<LlmProviderInfo[]>([]);
  const [library, setLibrary] = useState<ModelLibrary | null>(null);
  const [mode, setMode] = useState<Mode>('role');
  const [selectedRole, setSelectedRole] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [providerMenuOpen, setProviderMenuOpen] = useState(false);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    const isOpenCode = activeAgent === 'opencode';
    const fetchProviders = isOpenCode ? apiGetOpenCodeProviders : apiGetLlmProviders;

    Promise.all([
      fetchProviders(),
      apiGetModelLibrary().catch(() => null),
      activeTabCid ? apiGetConversationRole(activeTabCid).catch(() => ({ session_role: null })) : Promise.resolve({ session_role: null as string | null }),
      activeTabCid ? apiGetConversationLlm(activeTabCid).catch(() => null) : Promise.resolve(null),
    ]).then(([provResp, lib, roleResp, llmResp]) => {
      setProviders(provResp.providers);
      setLibrary(lib);

      const sessionRole = roleResp?.session_role || '';
      const hasRole = !!sessionRole && !!lib?.roles?.[sessionRole];
      setMode(hasRole ? 'role' : 'raw');
      setSelectedRole(hasRole ? sessionRole : '');

      const defaults = provResp.default;
      const savedProvider = llmResp?.provider || defaults.provider;
      const savedModel = llmResp?.model || defaults.model;
      const providerInList = provResp.providers.find(p => p.id === savedProvider);
      if (providerInList) {
        setSelectedProvider(savedProvider);
        setSelectedModel(savedModel);
      } else if (provResp.providers.length) {
        setSelectedProvider(defaults.provider || provResp.providers[0].id);
        setSelectedModel(defaults.model || provResp.providers[0].defaultModel);
      }

      setProviderMenuOpen(false);
      setModelMenuOpen(false);
      setRoleMenuOpen(false);
    }).catch(() => {});
  }, [activeAgent, activeTabCid]);

  const activeProvider = useMemo(
    () => providers.find(p => p.id === selectedProvider) || providers[0] || null,
    [providers, selectedProvider]
  );
  const visibleModels = activeProvider?.models || [];
  const modelValue = visibleModels.includes(selectedModel)
    ? selectedModel
    : (selectedModel || activeProvider?.defaultModel || '');

  const pinnedAliasSummary = useMemo(() => {
    if (!library || !selectedRole) return '';
    const role = library.roles[selectedRole];
    if (!role) return '';
    const alias = library.aliases[role.pinned];
    if (!alias) return '';
    return `${alias.display_name}`;
  }, [library, selectedRole]);

  const handleRoleChange = async (slug: string) => {
    setRoleMenuOpen(false);
    setSelectedRole(slug);
    if (!activeTabCid) return;
    try {
      const result = await apiUpdateConversationRole(activeTabCid, slug);
      // Reflect resolved values in raw-mode state so toggle is lossless.
      if (result.resolved) {
        setSelectedProvider(result.resolved.provider);
        setSelectedModel(result.resolved.model);
        if (activeAgent === 'opencode') {
          setSwitching(true);
          try { await apiSetOpenCodeModel(result.resolved.provider, result.resolved.model); } catch {}
          setSwitching(false);
        }
      }
    } catch {}
  };

  const handleModeToggle = async (nextMode: Mode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    if (!activeTabCid) return;
    if (nextMode === 'raw') {
      // Clear server-side session_role so legacy llm_settings takes over.
      try { await apiUpdateConversationRole(activeTabCid, null); } catch {}
      setSelectedRole('');
    }
  };

  const handleProviderChange = async (provider: string) => {
    const nextDefaultModel = providers.find(p => p.id === provider)?.defaultModel || '';
    setProviderMenuOpen(false);
    setModelMenuOpen(false);
    setSelectedProvider(provider);
    setSelectedModel(nextDefaultModel);
    try {
      localStorage.setItem('neuro_pending_llm',
        JSON.stringify({ provider, model: nextDefaultModel }));
    } catch {}
    if (!activeTabCid) return;
    try {
      await apiUpdateConversationLlm(activeTabCid, { provider, model: nextDefaultModel });
      if (activeAgent === 'opencode') {
        setSwitching(true);
        try { await apiSetOpenCodeModel(provider, nextDefaultModel); } catch {}
        setSwitching(false);
      }
    } catch {}
  };

  const handleModelChange = async (model: string) => {
    setModelMenuOpen(false);
    setSelectedModel(model);
    try {
      localStorage.setItem('neuro_pending_llm',
        JSON.stringify({ provider: selectedProvider, model }));
    } catch {}
    if (!activeTabCid) return;
    try {
      await apiUpdateConversationLlm(activeTabCid, { model });
      if (activeAgent === 'opencode') {
        setSwitching(true);
        try { await apiSetOpenCodeModel(selectedProvider, model); } catch {}
        setSwitching(false);
      }
    } catch {}
  };

  const btnStyle: CSSProperties = {
    background: 'rgba(255,255,255,0.02)',
    color: '#d0d6e0',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: '6px',
    padding: '4px 8px',
    fontSize: '11px',
    lineHeight: 1.2,
    minHeight: '26px',
    outline: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '6px',
    cursor: 'pointer',
    userSelect: 'none',
    transition: 'border-color 0.15s',
    fontFamily: 'inherit',
    fontFeatureSettings: '"cv01", "ss03"',
  };

  const dropStyle: CSSProperties = {
    position: 'absolute',
    bottom: 'calc(100% + 4px)',
    left: 0,
    minWidth: '100%',
    borderRadius: '8px',
    boxShadow: '0 -8px 30px rgba(0,0,0,0.5)',
    padding: '3px',
    zIndex: 50,
    maxHeight: '240px',
    overflowY: 'auto',
  };

  const itemStyle: CSSProperties = {
    width: '100%',
    border: 'none',
    background: 'transparent',
    color: '#d0d6e0',
    textAlign: 'left',
    padding: '6px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
    transition: 'background 0.12s',
    fontFamily: 'inherit',
    fontFeatureSettings: '"cv01", "ss03"',
  };

  const modeToggleStyle = (active: boolean): CSSProperties => ({
    padding: '3px 7px',
    background: active ? 'rgba(94,106,210,0.18)' : 'transparent',
    color: active ? '#c4b5fd' : '#8a8f98',
    border: 'none',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: active ? 510 : 400,
    cursor: 'pointer',
    fontFamily: 'inherit',
  });

  const roles = library?.roles ? Object.entries(library.roles) : [];
  const currentRole = selectedRole && library?.roles?.[selectedRole] || null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      {switching && (
        <Loader2 size={11} color="#7170ff" style={{ animation: 'spin 1s linear infinite' }} />
      )}

      {/* Mode toggle — only show if library has at least one role */}
      {roles.length > 0 && (
        <div style={{
          display: 'flex',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '6px',
          padding: '1px',
        }}>
          <button style={modeToggleStyle(mode === 'role')} onClick={() => handleModeToggle('role')}>Role</button>
          <button style={modeToggleStyle(mode === 'raw')} onClick={() => handleModeToggle('raw')}>Raw</button>
        </div>
      )}

      {mode === 'role' && roles.length > 0 ? (
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            onClick={() => { setRoleMenuOpen(o => !o); }}
            style={{ ...btnStyle, minWidth: '180px', maxWidth: '260px' }}
            title={pinnedAliasSummary || undefined}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span style={{ color: '#f7f8f8' }}>{currentRole?.display_name || 'Pick role'}</span>
              {pinnedAliasSummary && (
                <span style={{ color: '#62666d', marginLeft: '6px', fontSize: '10px' }}>· {pinnedAliasSummary}</span>
              )}
            </span>
            {roleMenuOpen ? <ChevronUp size={10} color="#62666d" /> : <ChevronDown size={10} color="#62666d" />}
          </button>
          <AnimatePresence>
            {roleMenuOpen && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                className="glass-dropdown"
                style={{ ...dropStyle, minWidth: '260px' }}
              >
                {roles.map(([slug, r]) => {
                  const pinnedAlias = library?.aliases?.[r.pinned];
                  const active = slug === selectedRole;
                  return (
                    <button
                      key={slug}
                      type="button"
                      onClick={() => handleRoleChange(slug)}
                      style={{
                        ...itemStyle,
                        background: active ? 'rgba(255,255,255,0.05)' : 'transparent',
                        color: active ? '#f7f8f8' : '#d0d6e0',
                        fontWeight: active ? 510 : 400,
                        display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px',
                      }}
                    >
                      <span>{r.display_name}</span>
                      {pinnedAlias && (
                        <span style={{ fontSize: '9px', color: '#62666d' }}>
                          → {pinnedAlias.display_name}
                        </span>
                      )}
                    </button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ) : (
        <>
          {/* Provider selector */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => { setProviderMenuOpen(o => !o); setModelMenuOpen(false); }}
              style={{ ...btnStyle, minWidth: '90px' }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {activeProvider?.name || 'Provider'}
              </span>
              {providerMenuOpen ? <ChevronUp size={10} color="#62666d" /> : <ChevronDown size={10} color="#62666d" />}
            </button>
            <AnimatePresence>
              {providerMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15, ease: 'easeOut' }}
                  className="glass-dropdown"
                  style={dropStyle}
                >
                  {providers.map(p => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleProviderChange(p.id)}
                      style={{
                        ...itemStyle,
                        background: p.id === (selectedProvider || activeProvider?.id) ? 'rgba(255,255,255,0.05)' : 'transparent',
                        color: p.id === (selectedProvider || activeProvider?.id) ? '#f7f8f8' : '#d0d6e0',
                        fontWeight: p.id === (selectedProvider || activeProvider?.id) ? 510 : 400,
                      }}
                    >
                      {p.name}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Model selector */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => { if (visibleModels.length > 0) { setModelMenuOpen(o => !o); setProviderMenuOpen(false); } }}
              disabled={visibleModels.length === 0}
              style={{ ...btnStyle, minWidth: '130px', maxWidth: '220px' }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace", fontSize: '10px' }}>
                {modelValue || 'Model'}
              </span>
              {modelMenuOpen ? <ChevronUp size={10} color="#62666d" /> : <ChevronDown size={10} color="#62666d" />}
            </button>
            <AnimatePresence>
              {modelMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15, ease: 'easeOut' }}
                  className="glass-dropdown"
                  style={{ ...dropStyle, minWidth: '240px' }}
                >
                  {visibleModels.map(m => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => handleModelChange(m)}
                      style={{
                        ...itemStyle,
                        background: m === modelValue ? 'rgba(255,255,255,0.05)' : 'transparent',
                        color: m === modelValue ? '#f7f8f8' : '#d0d6e0',
                        fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                        fontSize: '10px',
                        fontWeight: m === modelValue ? 510 : 400,
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </>
      )}
    </div>
  );
}
