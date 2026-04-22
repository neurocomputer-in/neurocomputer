'use client';
import { useEffect, useRef } from 'react';
import { useAppSelector } from '@/store/hooks';
import type { ThemeModule } from './themes/types';

const themeLoaders: Record<string, () => Promise<{ default: ThemeModule }>> = {
  'neural-network': () => import('./themes/neural-network'),
  'deep-space': () => import('./themes/deep-space'),
  'digital-rain': () => import('./themes/digital-rain'),
};

export default function ThreeBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const themeId = useAppSelector(s => s.ui.theme);

  useEffect(() => {
    if (!containerRef.current || themeId === 'minimal-dark') return;

    let cancelled = false;
    let animationId = 0;
    let renderer: import('three').WebGLRenderer | null = null;
    let activeTheme: ThemeModule | null = null;
    let onResize: (() => void) | null = null;
    const container = containerRef.current;

    const runCleanup = () => {
      if (onResize) window.removeEventListener('resize', onResize);
      if (animationId) cancelAnimationFrame(animationId);
      try { activeTheme?.cleanup(); } catch {}
      if (renderer) {
        try { renderer.forceContextLoss(); } catch {}
        try { renderer.dispose(); } catch {}
        const el = renderer.domElement;
        if (el.parentNode === container) container.removeChild(el);
      }
      renderer = null;
      activeTheme = null;
    };

    (async () => {
      const THREE = await import('three');
      if (cancelled) return;

      try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
      } catch (err) {
        console.error('[3D] WebGL context creation failed:', err);
        return;
      }
      if (cancelled) { runCleanup(); return; }

      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      container.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);

      const loader = themeLoaders[themeId];
      if (loader) {
        const mod = await loader();
        if (cancelled) { runCleanup(); return; }
        activeTheme = mod.default;
        activeTheme.setup(scene, camera, renderer);
      }

      onResize = () => {
        if (!renderer) return;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        activeTheme?.onResize?.(window.innerWidth, window.innerHeight);
      };
      window.addEventListener('resize', onResize);

      let lastTime = performance.now();
      const loop = (now: number) => {
        if (cancelled || !renderer) return;
        animationId = requestAnimationFrame(loop);
        const delta = now - lastTime;
        lastTime = now;
        activeTheme?.animate(now, delta);
        renderer.render(scene, camera);
      };
      animationId = requestAnimationFrame(loop);
    })();

    return () => {
      cancelled = true;
      runCleanup();
    };
  }, [themeId]);

  if (themeId === 'minimal-dark') return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}
