'use client';
import { useState, useEffect } from 'react';

const BREAKPOINT = 768;

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${BREAKPOINT - 1}px)`);
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);

    function updateAppHeight() {
      // Skip updates while the on-screen keyboard is open. When the keyboard
      // shows, visualViewport.height shrinks well below window.innerHeight;
      // if we resize the app root at that moment the whole layout cascades,
      // ResizeObservers fire on the terminal, xterm redraws, the focused
      // textarea blurs and the keyboard snaps shut. Only update when the
      // visualViewport reflects the real, keyboard-less window size.
      const vv = window.visualViewport?.height ?? window.innerHeight;
      const iv = window.innerHeight;
      if (window.visualViewport && vv < iv - 100) return;
      document.documentElement.style.setProperty('--app-height', `${vv}px`);
    }
    function forceUpdateAppHeight() {
      document.documentElement.style.setProperty('--app-height', `${window.innerHeight}px`);
    }
    updateAppHeight();
    window.visualViewport?.addEventListener('resize', updateAppHeight);
    window.addEventListener('orientationchange', forceUpdateAppHeight);
    return () => {
      mq.removeEventListener('change', handler);
      window.visualViewport?.removeEventListener('resize', updateAppHeight);
      window.removeEventListener('orientationchange', forceUpdateAppHeight);
    };
  }, []);
  return isMobile;
}
