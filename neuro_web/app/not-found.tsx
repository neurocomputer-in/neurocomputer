import Link from 'next/link';

export default function NotFound() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0a0a0b', color: '#f7f8f8', fontFamily: 'inherit',
    }}>
      <div style={{ maxWidth: 460, padding: 24, textAlign: 'center' }}>
        <div style={{ fontSize: 44, fontWeight: 590, marginBottom: 8 }}>404</div>
        <p style={{ fontSize: 13, color: '#8a8f98', marginBottom: 16 }}>Page not found.</p>
        <Link href="/" style={{
          padding: '7px 14px', borderRadius: 6, fontSize: 13,
          background: 'var(--accent)', color: '#fff', textDecoration: 'none',
        }}>Home</Link>
      </div>
    </div>
  );
}
