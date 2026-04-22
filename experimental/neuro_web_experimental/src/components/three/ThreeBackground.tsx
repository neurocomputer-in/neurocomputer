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
    console.log('[3D] ThreeBackground effect, theme:', themeId, 'container:', !!containerRef.current);
    if (!containerRef.current || themeId === 'minimal-dark') return;

    let cancelled = false;
    let animationId: number;
    let activeTheme: ThemeModule | null = null;

    (async () => {
      const THREE = await import('three');

      if (cancelled) return;

      const container = containerRef.current!;
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      container.appendChild(renderer.domElement);
      console.log('[3D] Canvas appended, loading theme:', themeId);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);

      const loader = themeLoaders[themeId];
      if (loader) {
        const mod = await loader();
        if (cancelled) {
          renderer.dispose();
          container.removeChild(renderer.domElement);
          return;
        }
        activeTheme = mod.default;
        activeTheme.setup(scene, camera, renderer);
        console.log('[3D] Theme setup complete:', themeId);
      }

      const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        activeTheme?.onResize?.(window.innerWidth, window.innerHeight);
      };
      window.addEventListener('resize', onResize);

      let lastTime = performance.now();
      const loop = (now: number) => {
        if (cancelled) return;
        animationId = requestAnimationFrame(loop);
        const delta = now - lastTime;
        lastTime = now;
        activeTheme?.animate(now, delta);
        renderer.render(scene, camera);
      };
      animationId = requestAnimationFrame(loop);

      (container as any).__threeCleanup = () => {
        window.removeEventListener('resize', onResize);
        cancelAnimationFrame(animationId);
        activeTheme?.cleanup();
        renderer.dispose();
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
      };
    })();

    return () => {
      cancelled = true;
      const cleanup = (containerRef.current as any)?.__threeCleanup;
      if (cleanup) cleanup();
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
