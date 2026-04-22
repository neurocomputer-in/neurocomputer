'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { AgentInfo } from '@/types';
import AgentIcon from '@/components/agent/AgentIcon';

interface Props {
  thinkingContent: string | null;
  currentStep: { nodeId: string; neuro: string; status: string } | null;
  agentInfo?: AgentInfo;
}

export default function ThinkingIndicator({ thinkingContent, currentStep, agentInfo }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
      <div
        style={{
          width: '28px', height: '28px', minWidth: '28px',
          background: 'rgba(255,255,255,0.04)',
          borderRadius: '6px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: '2px', flexShrink: 0,
        }}
      >
        {agentInfo ? (
          <div style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>
            <AgentIcon agent={agentInfo} size={14} />
          </div>
        ) : (
          <Loader2 size={13} color="#7170ff" style={{ animation: 'spin 1s linear infinite' }} />
        )}
      </div>

      <div style={{ minWidth: 0, flex: 1 }}>
        <motion.div
          key="indicator-header"
          onClick={() => thinkingContent && setExpanded(!expanded)}
          className="glass-panel"
          style={{
            borderRadius: '6px', padding: '10px 14px',
            cursor: thinkingContent ? 'pointer' : 'default',
          }}
          whileHover={thinkingContent ? { backgroundColor: 'rgba(255,255,255,0.04)' } : {}}
          whileTap={thinkingContent ? { scale: 0.995 } : {}}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: 'var(--accent)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }} />
            <span style={{ fontSize: '13px', color: '#8a8f98', fontWeight: 400 }}>
              {currentStep
                ? `Running: ${currentStep.neuro}`
                : 'Thinking...'}
            </span>
            {thinkingContent && (
              <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                {expanded ? <ChevronUp size={12} color="#62666d" /> : <ChevronDown size={12} color="#62666d" />}
              </span>
            )}
          </div>

            <AnimatePresence>
              {expanded && thinkingContent && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{
                    marginTop: '8px', paddingTop: '8px',
                    borderTop: '1px solid rgba(255,255,255,0.05)',
                    fontSize: '12px', color: '#8a8f98', lineHeight: 1.6,
                    fontStyle: 'italic', whiteSpace: 'pre-wrap',
                    maxHeight: '200px', overflowY: 'auto',
                    fontWeight: 400,
                  }}
                >
                  {thinkingContent}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
      </div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
