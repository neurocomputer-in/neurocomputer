import { AgentType } from '@/types';

export type AppId = 'neuro' | 'openclaw' | 'opencode' | 'neuroupwork' | 'terminal' | 'ide'
  | 'neurodesktop'
  | 'neuroresearch' | 'neurowrite' | 'neurodata' | 'neurofiles'
  | 'neuroemail' | 'neurocalendar' | 'neuronotes' | 'neurobrowse'
  | 'neurovoice' | 'neurotranslate';

export interface AppDef {
  id: AppId;
  name: string;
  description: string;
  icon: string;
  color: string;
  agentType?: AgentType;
  tabKind: 'chat' | 'terminal' | 'neuroide' | 'desktop';
  pinned: boolean;
}

export const APP_LIST: AppDef[] = [
  {
    id: 'neuro',
    name: 'Neuro',
    description: 'General AI assistant',
    icon: 'brain',
    color: '#8B5CF6',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: true,
  },
  {
    id: 'openclaw',
    name: 'OpenClaw',
    description: 'Web automation & scraping',
    icon: 'globe',
    color: '#f97316',
    agentType: AgentType.OPENCLAW,
    tabKind: 'chat',
    pinned: true,
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    description: 'Code assistant',
    icon: 'code',
    color: '#3b82f6',
    agentType: AgentType.OPENCODE,
    tabKind: 'chat',
    pinned: true,
  },
  {
    id: 'neuroupwork',
    name: 'NeuroUpwork',
    description: 'Upwork automation',
    icon: 'briefcase',
    color: '#14b8a6',
    agentType: AgentType.NEUROUPWORK,
    tabKind: 'chat',
    pinned: true,
  },
  {
    id: 'terminal',
    name: 'Terminal',
    description: 'Shell access',
    icon: 'terminal',
    color: '#6b7280',
    tabKind: 'terminal',
    pinned: true,
  },
  {
    id: 'ide',
    name: 'IDE',
    description: 'Neuro library editor',
    icon: 'layers',
    color: '#a855f7',
    tabKind: 'neuroide',
    pinned: true,
  },
  {
    id: 'neurodesktop',
    name: 'Desktop',
    description: 'Stream and control your desktop',
    icon: 'tv',
    color: '#1d4ed8',
    tabKind: 'desktop',
    pinned: true,
  },
  // ── Launcher-only apps (not pinned to dock) ──────────────────────
  {
    id: 'neuroresearch',
    name: 'NeuroResearch',
    description: 'Deep research & web analysis',
    icon: 'search',
    color: '#0ea5e9',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurowrite',
    name: 'NeuroWrite',
    description: 'AI writing & editing assistant',
    icon: 'pen',
    color: '#ec4899',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurodata',
    name: 'NeuroData',
    description: 'Data analysis & visualization',
    icon: 'barchart',
    color: '#f59e0b',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurofiles',
    name: 'NeuroFiles',
    description: 'File & document manager',
    icon: 'folder',
    color: '#84cc16',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neuroemail',
    name: 'NeuroEmail',
    description: 'Smart email assistant',
    icon: 'mail',
    color: '#8b5cf6',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurocalendar',
    name: 'NeuroCalendar',
    description: 'Calendar & scheduling AI',
    icon: 'calendar',
    color: '#10b981',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neuronotes',
    name: 'NeuroNotes',
    description: 'Smart notes & knowledge base',
    icon: 'note',
    color: '#f97316',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurobrowse',
    name: 'NeuroBrowse',
    description: 'AI-powered web browser',
    icon: 'compass',
    color: '#6366f1',
    agentType: AgentType.OPENCLAW,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurovoice',
    name: 'NeuroVoice',
    description: 'Voice & audio processing',
    icon: 'mic',
    color: '#e11d48',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
  {
    id: 'neurotranslate',
    name: 'NeuroTranslate',
    description: 'Real-time AI translation',
    icon: 'languages',
    color: '#06b6d4',
    agentType: AgentType.NEURO,
    tabKind: 'chat',
    pinned: false,
  },
];

export const APP_MAP: Record<AppId, AppDef> = Object.fromEntries(
  APP_LIST.map(a => [a.id, a])
) as Record<AppId, AppDef>;

export function appForAgent(agentId: string): AppDef | undefined {
  return APP_LIST.find(a => a.agentType === agentId);
}

export function appForTabKind(kind: string): AppDef | undefined {
  return APP_LIST.find(a => a.tabKind === kind);
}
