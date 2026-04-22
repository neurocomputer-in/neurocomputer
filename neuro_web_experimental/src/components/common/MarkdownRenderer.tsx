'use client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Props {
  content: string;
}

export default function MarkdownRenderer({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const isBlock = !!(match);
          if (isBlock) {
            return (
              <div style={{
                position: 'relative',
                margin: '12px 0',
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid rgba(255,255,255,0.08)',
              }}>
                {/* Language badge */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 14px',
                  background: 'rgba(255,255,255,0.03)',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                }}>
                  <span style={{
                    fontSize: '10px', fontWeight: 510, letterSpacing: '0.8px',
                    textTransform: 'uppercase', color: '#8a8f98',
                    fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                  }}>
                    {match[1]}
                  </span>
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    borderRadius: '0',
                    fontSize: '13px',
                    margin: 0,
                    background: '#0f1011',
                    border: 'none',
                    padding: '14px 16px',
                    fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
                  }}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            );
          }
          return (
            <code
              style={{
                background: 'rgba(255,255,255,0.05)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontSize: '13px',
                fontWeight: 510,
                color: '#d0d6e0',
                border: '1px solid rgba(255,255,255,0.05)',
                fontFamily: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, monospace",
              }}
              className={className}
              {...props}
            >
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p style={{ margin: '6px 0', lineHeight: 1.6, fontWeight: 400 }}>{children}</p>;
        },
        ul({ children }) {
          return <ul style={{ paddingLeft: '20px', margin: '6px 0', lineHeight: 1.6 }}>{children}</ul>;
        },
        ol({ children }) {
          return <ol style={{ paddingLeft: '20px', margin: '6px 0', lineHeight: 1.6 }}>{children}</ol>;
        },
        h1({ children }) {
          return <h1 style={{ fontSize: '20px', fontWeight: 590, color: '#f7f8f8', margin: '16px 0 8px', letterSpacing: '-0.24px' }}>{children}</h1>;
        },
        h2({ children }) {
          return <h2 style={{ fontSize: '17px', fontWeight: 590, color: '#f7f8f8', margin: '14px 0 6px', letterSpacing: '-0.2px' }}>{children}</h2>;
        },
        h3({ children }) {
          return <h3 style={{ fontSize: '15px', fontWeight: 590, color: '#f7f8f8', margin: '12px 0 4px' }}>{children}</h3>;
        },
        strong({ children }) {
          return <strong style={{ fontWeight: 590, color: '#f7f8f8' }}>{children}</strong>;
        },
        blockquote({ children }) {
          return (
            <blockquote style={{
              borderLeft: '2px solid rgba(255,255,255,0.08)',
              margin: '10px 0',
              padding: '8px 16px',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '0 6px 6px 0',
              color: '#8a8f98',
              fontStyle: 'italic',
            }}>
              {children}
            </blockquote>
          );
        },
        hr() {
          return <hr style={{ border: 'none', height: '1px', background: 'rgba(255,255,255,0.05)', margin: '16px 0' }} />;
        },
        a({ href, children }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" style={{
              color: '#7170ff', textDecoration: 'none', fontWeight: 510,
              borderBottom: '1px solid rgba(113,112,255,0.3)',
              transition: 'border-color 0.15s',
            }}>
              {children}
            </a>
          );
        },
        table({ children }) {
          return (
            <div style={{ overflowX: 'auto', margin: '10px 0' }}>
              <table style={{
                width: '100%', borderCollapse: 'collapse', fontSize: '13px',
                border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px',
              }}>
                {children}
              </table>
            </div>
          );
        },
        th({ children }) {
          return (
            <th style={{
              padding: '8px 12px', textAlign: 'left', fontWeight: 510,
              background: 'rgba(255,255,255,0.03)', color: '#d0d6e0',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>
              {children}
            </th>
          );
        },
        td({ children }) {
          return (
            <td style={{
              padding: '7px 12px',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
              color: '#d0d6e0',
            }}>
              {children}
            </td>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
