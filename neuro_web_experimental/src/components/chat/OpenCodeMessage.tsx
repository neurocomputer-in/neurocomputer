'use client';
import { Message } from '@/types';
import ToolCallCard from './ToolCallCard';
import MarkdownRenderer from '@/components/common/MarkdownRenderer';

interface Props {
  message: Message;
}

export default function OpenCodeMessage({ message }: Props) {
  const steps = message.openCodeSteps || [];
  const tools = message.toolCalls || [];
  const hasSteps = steps.length > 0;
  const hasTools = tools.length > 0;
  const isStreaming = !!message.isStreaming;

  if (!hasSteps && !hasTools) {
    return (
      <>
        <MarkdownRenderer content={message.text} />
        {isStreaming && <BlinkingCursor />}
      </>
    );
  }

  const completedTools = tools.filter(t => t.status === 'completed' || t.status === 'error').length;
  const doneSteps = steps.filter(s => s.status === 'done').length;
  const lastStep = steps[steps.length - 1];
  const isStepRunning = lastStep?.status === 'running';

  return (
    <div>
      {/* Step progress dots */}
      {hasSteps && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center',
          marginBottom: '8px',
        }}>
          {steps.map(s => (
            <div key={s.step} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: s.status === 'done' ? '#27a644' : 'var(--accent)',
                ...(s.status === 'running' ? { animation: 'pulse 1.5s ease-in-out infinite' } : {}),
              }} />
              <span style={{ fontSize: '11px', color: '#62666d', fontWeight: 400 }}>Step {s.step}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tool call cards */}
      {hasTools && (
        <div style={{ marginBottom: '8px' }}>
          {tools.map(tc => (
            <ToolCallCard key={tc.callId} toolCall={tc} />
          ))}
        </div>
      )}

      {/* Current step running indicator */}
      {isStepRunning && !message.text && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '6px 0', color: '#8a8f98', fontSize: '12px', fontWeight: 400,
        }}>
          <div style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: 'var(--accent)',
            animation: 'pulse 1.5s ease-in-out infinite',
          }} />
          <span>Processing step {lastStep.step}...</span>
        </div>
      )}

      {/* Response text */}
      {message.text && (
        <>
          <MarkdownRenderer content={message.text} />
          {isStreaming && <BlinkingCursor />}
        </>
      )}

      {/* Summary after completion */}
      {!isStreaming && (hasTools || hasSteps) && message.text && (
        <div style={{
          marginTop: '8px', fontSize: '11px', color: '#62666d', fontWeight: 400,
        }}>
          {completedTools > 0 && `${completedTools} tool${completedTools > 1 ? 's' : ''}`}
          {completedTools > 0 && doneSteps > 0 && ', '}
          {doneSteps > 0 && `${doneSteps} step${doneSteps > 1 ? 's' : ''}`}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.3); }
        }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>
    </div>
  );
}

function BlinkingCursor() {
  return (
    <span style={{
      display: 'inline-block', width: '2px', height: '14px',
      background: 'var(--accent)', marginLeft: '2px',
      animation: 'blink 1s step-end infinite', verticalAlign: 'text-bottom',
    }} />
  );
}
