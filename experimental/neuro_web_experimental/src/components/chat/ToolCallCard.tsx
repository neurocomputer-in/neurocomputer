'use client';
import { useState } from 'react';
import {
  Terminal, FileText, Edit3, Search, Globe,
  CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronRight,
} from 'lucide-react';
import { OpenCodeToolCall } from '@/types';

const TOOL_META: Record<string, { label: string; Icon: typeof Terminal }> = {
  bash:      { label: 'Bash',       Icon: Terminal },
  read:      { label: 'Read',       Icon: FileText },
  write:     { label: 'Write',      Icon: Edit3 },
  edit:      { label: 'Edit',       Icon: Edit3 },
  glob:      { label: 'Find Files', Icon: Search },
  grep:      { label: 'Search',     Icon: Search },
  webfetch:  { label: 'Fetch',      Icon: Globe },
  todowrite: { label: 'Plan',       Icon: FileText },
};

function statusIcon(status: OpenCodeToolCall['status']) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={13} color="#27a644" />;
    case 'error':
      return <AlertCircle size={13} color="#EF4444" />;
    default:
      return <Loader2 size={13} color="#7170ff" style={{ animation: 'spin 1s linear infinite' }} />;
  }
}

function inputSummary(tool: string, input: Record<string, unknown>): string {
  switch (tool) {
    case 'read':
    case 'edit':
    case 'write':
      return String(input.file_path || input.filename || input.path || '');
    case 'bash':
      return String(input.command || '').slice(0, 80);
    case 'grep':
    case 'glob':
      return String(input.pattern || '');
    case 'webfetch': {
      try {
        return new URL(String(input.url || '')).hostname;
      } catch {
        return String(input.url || '');
      }
    }
    default:
      return '';
  }
}

function formatDuration(start?: number, end?: number): string | null {
  if (!start || !end) return null;
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

interface Props {
  toolCall: OpenCodeToolCall;
}

export default function ToolCallCard({ toolCall }: Props) {
  const [expanded, setExpanded] = useState(false);
  const meta = TOOL_META[toolCall.tool] || { label: toolCall.tool, Icon: Terminal };
  const { Icon } = meta;
  const summary = inputSummary(toolCall.tool, toolCall.input);
  const duration = formatDuration(toolCall.time?.start, toolCall.time?.end);

  return (
    <div style={{
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.05)',
      borderRadius: '6px',
      marginBottom: '6px',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          width: '100%', padding: '8px 12px',
          background: 'none', border: 'none', cursor: 'pointer',
          color: '#d0d6e0', fontSize: '12px', textAlign: 'left',
          fontFamily: 'inherit',
          fontFeatureSettings: '"cv01", "ss03"',
        }}
      >
        {expanded
          ? <ChevronDown size={12} color="#62666d" />
          : <ChevronRight size={12} color="#62666d" />}
        <Icon size={13} color="#8a8f98" />
        <span style={{ fontWeight: 510 }}>{meta.label}</span>
        {summary && (
          <span style={{
            color: '#62666d', fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace", fontSize: '11px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            flex: 1, minWidth: 0,
          }}>
            {summary}
          </span>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          {duration && <span style={{ color: '#62666d', fontSize: '10px', fontFamily: "'Berkeley Mono', ui-monospace, monospace" }}>{duration}</span>}
          {statusIcon(toolCall.status)}
        </span>
      </button>

      {/* Body */}
      {expanded && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.05)',
          padding: '10px 12px',
          fontSize: '12px', color: '#8a8f98',
        }}>
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#62666d', marginBottom: '3px', fontWeight: 510, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Input</div>
            <pre style={{
              background: '#0f1011', borderRadius: '4px',
              padding: '8px', margin: 0,
              fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace", fontSize: '11px', color: '#d0d6e0',
              whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              maxHeight: '200px', overflow: 'auto',
              border: '1px solid rgba(255,255,255,0.05)',
            }}>
              {JSON.stringify(toolCall.input, null, 2)}
            </pre>
          </div>
          {toolCall.output && (
            <div>
              <div style={{ color: '#62666d', marginBottom: '3px', fontWeight: 510, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Output</div>
              <pre style={{
                background: '#0f1011', borderRadius: '4px',
                padding: '8px', margin: 0,
                fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace", fontSize: '11px', color: '#d0d6e0',
                whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                maxHeight: '200px', overflow: 'auto',
                border: '1px solid rgba(255,255,255,0.05)',
              }}>
                {toolCall.output.length > 1000
                  ? toolCall.output.slice(0, 1000) + '\n... (truncated)'
                  : toolCall.output}
              </pre>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
