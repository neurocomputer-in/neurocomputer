'use client';
import { Globe, type LucideIcon } from 'lucide-react';
import { AgentInfo, AgentType } from '@/types';

const LOGO_MAP: Record<string, string> = {
  [AgentType.NEURO]: '/agents/neuro.png',
  [AgentType.OPENCLAW]: '/agents/openclaw.png',
  [AgentType.OPENCODE]: '/agents/opencode.png',
  [AgentType.NEUROUPWORK]: '/agents/upwork.png',
};

interface Props {
  agent: AgentInfo;
  size?: number;
}

export default function AgentIcon({ agent, size = 16 }: Props) {
  const logo = LOGO_MAP[agent.type];

  if (logo) {
    return (
      <img
        src={logo}
        alt={agent.name}
        width={size}
        height={size}
        style={{ borderRadius: '50%', objectFit: 'cover' }}
      />
    );
  }

  // Fallback for "All Agents" or unknown types
  return <Globe size={size} color={agent.color} strokeWidth={1.8} />;
}
