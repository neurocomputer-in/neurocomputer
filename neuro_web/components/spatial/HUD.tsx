'use client';
import { useState } from 'react';
import { Layout, Keyboard } from 'lucide-react';
import { useAppDispatch } from '@/store/hooks';
import { setInterfaceMode } from '@/store/uiSlice';

export default function HUD() {
  const dispatch = useAppDispatch();
  const [showHelp, setShowHelp] = useState(false);

  return (
    <>
      <div style={{
        position: 'absolute', top: 12, left: 12, display: 'flex', gap: 6,
        pointerEvents: 'auto', zIndex: 20,
      }}>
        <button onClick={() => dispatch(setInterfaceMode('classic'))} style={btn}>
          <Layout size={12} /> Classic
        </button>
        <button onClick={() => setShowHelp(s => !s)} style={btn}>
          <Keyboard size={12} /> Keys
        </button>
      </div>
      {showHelp && (
        <div style={{
          position: 'absolute', bottom: 12, left: 12,
          background: 'rgba(15,16,17,0.9)', color: '#d0d6e0',
          border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
          padding: '10px 14px', fontSize: 12, fontFamily: 'monospace',
          pointerEvents: 'auto', zIndex: 20,
          lineHeight: 1.6,
        }}>
          <div>LMB drag — orbit · RMB drag — pan · scroll — zoom</div>
          <div>Click — select · Dbl-click / Enter — focus</div>
          <div>Esc — exit focus · F — frame selected</div>
          <div>Tab / Shift+Tab — cycle · WASD — fly · Q/E — up/down</div>
        </div>
      )}
    </>
  );
}

const btn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '5px 10px', fontSize: 12, borderRadius: 6,
  background: 'rgba(15,16,17,0.85)', color: '#d0d6e0',
  border: '1px solid rgba(255,255,255,0.08)', cursor: 'pointer',
  fontFamily: 'inherit',
};
