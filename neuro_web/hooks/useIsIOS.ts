'use client';
import { useEffect, useState } from 'react';

// True on real iOS (iPhone/iPad/iPod) including iPadOS reporting as "Mac"
// with touch points. Used for iOS-specific workarounds (virtual-keyboard
// behavior, programmatic focus rules) that should NOT apply to desktop
// mobile-emulation in DevTools.
export function useIsIOS() {
  const [isIOS, setIsIOS] = useState(false);
  useEffect(() => {
    if (typeof navigator === 'undefined') return;
    const ua = navigator.userAgent || '';
    const iOSDevice = /iPad|iPhone|iPod/.test(ua);
    const iPadOS = ua.includes('Macintosh') && (navigator as any).maxTouchPoints > 1;
    setIsIOS(iOSDevice || iPadOS);
  }, []);
  return isIOS;
}
