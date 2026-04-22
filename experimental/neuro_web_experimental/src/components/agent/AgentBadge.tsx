'use client';
import { AgentInfo } from '@/types';
import AgentIcon from './AgentIcon';

interface Props {
  agent: AgentInfo;
  size?: 'sm' | 'md';
}

export default function AgentBadge({ agent, size = 'md' }: Props) {
  const fontSize = size === 'sm' ? '11px' : '12px';
  const padding = size === 'sm' ? '2px 8px' : '4px 10px';
  const iconSize = size === 'sm' ? 11 : 13;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: '4px',
        padding,
        fontSize,
        color: '#d0d6e0',
        fontWeight: 510,
      }}
    >
      <AgentIcon agent={agent} size={iconSize} />
      <span>{agent.name}</span>
    </div>
  );
}
