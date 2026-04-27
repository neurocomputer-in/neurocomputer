'use client';
import { useState, useEffect } from 'react';

const BREAKPOINT = 768;

export function useIsMobile() {
  // Synchronous initializer — without it, the first render returns false even
  // on mobile, which races with framer-motion's `initial` props in Window.tsx
  // (desktop initial scale: 0.92 gets stuck on mobile windows).
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(`(max-width: ${BREAKPOINT - 1}px) or (max-height: 500px)`).matches;
  });
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${BREAKPOINT - 1}px) or (max-height: 500px)`);
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return isMobile;
}
