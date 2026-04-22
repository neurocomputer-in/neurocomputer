'use client';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0a0a0b', color: '#f7f8f8', fontFamily: 'inherit',
    }}>
      <div style={{ maxWidth: 460, padding: 24, textAlign: 'center' }}>
        <h1 style={{ fontSize: 20, fontWeight: 590, marginBottom: 8 }}>Something went wrong</h1>
        <p style={{ fontSize: 13, color: '#8a8f98', marginBottom: 16 }}>
          {error?.message || 'An unexpected error occurred.'}
        </p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
          <button onClick={() => reset()} style={btnPrimary}>Retry</button>
          <Link href="/" style={btnSecondary}>Home</Link>
        </div>
      </div>
    </div>
  );
}

const btnBase: React.CSSProperties = {
  padding: '7px 14px', borderRadius: 6, fontSize: 13,
  cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'none',
};
const btnPrimary: React.CSSProperties = {
  ...btnBase, background: 'var(--accent)', color: '#fff', border: 'none',
};
const btnSecondary: React.CSSProperties = {
  ...btnBase, background: 'rgba(255,255,255,0.04)', color: '#d0d6e0',
  border: '1px solid rgba(255,255,255,0.08)',
};
