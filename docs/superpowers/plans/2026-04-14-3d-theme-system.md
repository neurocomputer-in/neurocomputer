# 3D Theme System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add selectable 3D animated backgrounds (Three.js) behind the existing chat UI, with 4 themes: Neural Network, Deep Space, Digital Rain, and Minimal Dark.

**Architecture:** A `<ThreeBackground />` component renders a full-screen Three.js canvas behind all UI via CSS `position: fixed; z-index: 0`. Each theme is a standalone module exporting `setup(scene, camera)` and `animate(time)`. Theme selection persists in Redux (`uiSlice.theme`) and localStorage. All existing UI components remain unchanged — they just sit on top of the 3D canvas with transparent/semi-transparent backgrounds.

**Tech Stack:** three.js, @react-three/fiber (React integration), Next.js dynamic import (SSR-safe), Redux Toolkit.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `neuro_web/components/three/ThreeBackground.tsx` | **Create** | Full-screen Three.js canvas, loads active theme, renders behind UI |
| `neuro_web/components/three/themes/neural-network.ts` | **Create** | Particle field with synaptic connections |
| `neuro_web/components/three/themes/deep-space.ts` | **Create** | Stars, nebula clouds, floating orbs |
| `neuro_web/components/three/themes/digital-rain.ts` | **Create** | Matrix-style falling data streams |
| `neuro_web/components/three/themes/types.ts` | **Create** | Theme interface: `{ setup, animate, cleanup }` |
| `neuro_web/components/three/ThemeSelector.tsx` | **Create** | Dropdown/picker UI for theme selection |
| `neuro_web/store/uiSlice.ts` | **Modify** | Add `theme` state + `setTheme` action |
| `neuro_web/app/page.tsx` | **Modify** | Add `<ThreeBackground />` behind layout |
| `neuro_web/app/globals.css` | **Modify** | Make surfaces semi-transparent for 3D bleed-through |

---

## Task 1: Install Three.js and Create Theme Interface

**Files:**
- Create: `neuro_web/components/three/themes/types.ts`

- [ ] **Step 1: Install three.js**

```bash
cd neuro_web && npm install three @types/three
```

- [ ] **Step 2: Create the theme interface**

Create `neuro_web/components/three/themes/types.ts`:

```typescript
import * as THREE from 'three';

export interface ThemeConfig {
  name: string;
  label: string;
  description: string;
}

export interface ThemeModule {
  config: ThemeConfig;
  setup: (scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) => void;
  animate: (time: number, delta: number) => void;
  cleanup: () => void;
  /** Optional: handle window resize */
  onResize?: (width: number, height: number) => void;
}

export const THEME_IDS = ['neural-network', 'deep-space', 'digital-rain', 'minimal-dark'] as const;
export type ThemeId = typeof THEME_IDS[number];
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/package.json neuro_web/package-lock.json neuro_web/components/three/themes/types.ts
git commit -m "feat(3d): install three.js and define theme interface"
```

---

## Task 2: Create Neural Network Theme

**Files:**
- Create: `neuro_web/components/three/themes/neural-network.ts`

- [ ] **Step 1: Implement the neural network particle theme**

Create `neuro_web/components/three/themes/neural-network.ts`:

```typescript
import * as THREE from 'three';
import { ThemeModule } from './types';

const PARTICLE_COUNT = 200;
const CONNECTION_DISTANCE = 2.5;
const FIELD_SIZE = 15;

let particles: THREE.Points;
let lines: THREE.LineSegments;
let positions: Float32Array;
let velocities: Float32Array;
let linePositions: Float32Array;
let lineGeometry: THREE.BufferGeometry;
let particleGeometry: THREE.BufferGeometry;

function setup(scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) {
  camera.position.z = 12;
  scene.fog = new THREE.FogExp2(0x060612, 0.06);
  renderer.setClearColor(0x060612, 1);

  // Particles
  particleGeometry = new THREE.BufferGeometry();
  positions = new Float32Array(PARTICLE_COUNT * 3);
  velocities = new Float32Array(PARTICLE_COUNT * 3);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    positions[i * 3] = (Math.random() - 0.5) * FIELD_SIZE;
    positions[i * 3 + 1] = (Math.random() - 0.5) * FIELD_SIZE;
    positions[i * 3 + 2] = (Math.random() - 0.5) * FIELD_SIZE;
    velocities[i * 3] = (Math.random() - 0.5) * 0.005;
    velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.005;
    velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.005;
  }

  particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const particleMaterial = new THREE.PointsMaterial({
    color: 0x8B5CF6,
    size: 0.06,
    transparent: true,
    opacity: 0.7,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  particles = new THREE.Points(particleGeometry, particleMaterial);
  scene.add(particles);

  // Connection lines
  const maxLines = PARTICLE_COUNT * PARTICLE_COUNT;
  linePositions = new Float32Array(maxLines * 6);
  lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
  lineGeometry.setDrawRange(0, 0);

  const lineMaterial = new THREE.LineBasicMaterial({
    color: 0x8B5CF6,
    transparent: true,
    opacity: 0.12,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  lines = new THREE.LineSegments(lineGeometry, lineMaterial);
  scene.add(lines);
}

function animate(time: number, _delta: number) {
  // Move particles
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const i3 = i * 3;
    positions[i3] += velocities[i3];
    positions[i3 + 1] += velocities[i3 + 1];
    positions[i3 + 2] += velocities[i3 + 2];

    // Wrap around
    for (let j = 0; j < 3; j++) {
      if (positions[i3 + j] > FIELD_SIZE / 2) positions[i3 + j] = -FIELD_SIZE / 2;
      if (positions[i3 + j] < -FIELD_SIZE / 2) positions[i3 + j] = FIELD_SIZE / 2;
    }
  }
  particleGeometry.attributes.position.needsUpdate = true;

  // Update connections
  let lineIndex = 0;
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    for (let j = i + 1; j < PARTICLE_COUNT; j++) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

      if (dist < CONNECTION_DISTANCE) {
        linePositions[lineIndex++] = positions[i * 3];
        linePositions[lineIndex++] = positions[i * 3 + 1];
        linePositions[lineIndex++] = positions[i * 3 + 2];
        linePositions[lineIndex++] = positions[j * 3];
        linePositions[lineIndex++] = positions[j * 3 + 1];
        linePositions[lineIndex++] = positions[j * 3 + 2];
      }
    }
  }
  lineGeometry.attributes.position.needsUpdate = true;
  lineGeometry.setDrawRange(0, lineIndex / 3);

  // Slow rotation
  particles.rotation.y = time * 0.00003;
  lines.rotation.y = time * 0.00003;
}

function cleanup() {
  particleGeometry?.dispose();
  lineGeometry?.dispose();
}

const theme: ThemeModule = {
  config: { name: 'neural-network', label: 'Neural Network', description: 'Floating particles with synaptic connections' },
  setup,
  animate,
  cleanup,
};

export default theme;
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/three/themes/neural-network.ts
git commit -m "feat(3d): add neural network particle theme"
```

---

## Task 3: Create Deep Space Theme

**Files:**
- Create: `neuro_web/components/three/themes/deep-space.ts`

- [ ] **Step 1: Implement the deep space theme**

Create `neuro_web/components/three/themes/deep-space.ts`:

```typescript
import * as THREE from 'three';
import { ThemeModule } from './types';

const STAR_COUNT = 1500;
const ORB_COUNT = 8;

let stars: THREE.Points;
let orbs: THREE.Mesh[] = [];
let starGeometry: THREE.BufferGeometry;
let orbGeometries: THREE.SphereGeometry[] = [];
let orbMaterials: THREE.MeshBasicMaterial[] = [];

function setup(scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) {
  camera.position.z = 10;
  scene.fog = new THREE.FogExp2(0x040410, 0.04);
  renderer.setClearColor(0x040410, 1);

  // Stars
  starGeometry = new THREE.BufferGeometry();
  const starPositions = new Float32Array(STAR_COUNT * 3);
  const starSizes = new Float32Array(STAR_COUNT);

  for (let i = 0; i < STAR_COUNT; i++) {
    starPositions[i * 3] = (Math.random() - 0.5) * 40;
    starPositions[i * 3 + 1] = (Math.random() - 0.5) * 40;
    starPositions[i * 3 + 2] = (Math.random() - 0.5) * 40;
    starSizes[i] = Math.random() * 0.04 + 0.01;
  }

  starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));

  const starMaterial = new THREE.PointsMaterial({
    color: 0xccccff,
    size: 0.05,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  stars = new THREE.Points(starGeometry, starMaterial);
  scene.add(stars);

  // Nebula orbs (soft glowing spheres)
  const orbColors = [0x4a1a8a, 0x1a3a8a, 0x8a1a4a, 0x1a6a5a, 0x6a3a8a, 0x2a2a8a, 0x5a1a6a, 0x1a4a7a];
  for (let i = 0; i < ORB_COUNT; i++) {
    const geo = new THREE.SphereGeometry(Math.random() * 1.5 + 0.5, 16, 16);
    const mat = new THREE.MeshBasicMaterial({
      color: orbColors[i],
      transparent: true,
      opacity: 0.06,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const orb = new THREE.Mesh(geo, mat);
    orb.position.set(
      (Math.random() - 0.5) * 16,
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10 - 5,
    );
    orb.userData.speed = Math.random() * 0.0003 + 0.0001;
    orb.userData.offset = Math.random() * Math.PI * 2;
    scene.add(orb);
    orbs.push(orb);
    orbGeometries.push(geo);
    orbMaterials.push(mat);
  }
}

function animate(time: number, _delta: number) {
  stars.rotation.y = time * 0.000015;
  stars.rotation.x = time * 0.000005;

  for (const orb of orbs) {
    const s = orb.userData.speed;
    const o = orb.userData.offset;
    orb.position.x += Math.sin(time * s + o) * 0.003;
    orb.position.y += Math.cos(time * s * 1.3 + o) * 0.002;
    orb.scale.setScalar(1 + Math.sin(time * 0.0005 + o) * 0.1);
  }
}

function cleanup() {
  starGeometry?.dispose();
  orbGeometries.forEach(g => g.dispose());
  orbMaterials.forEach(m => m.dispose());
  orbs = [];
  orbGeometries = [];
  orbMaterials = [];
}

const theme: ThemeModule = {
  config: { name: 'deep-space', label: 'Deep Space', description: 'Stars, nebula clouds, and floating orbs' },
  setup,
  animate,
  cleanup,
};

export default theme;
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/three/themes/deep-space.ts
git commit -m "feat(3d): add deep space theme"
```

---

## Task 4: Create Digital Rain Theme

**Files:**
- Create: `neuro_web/components/three/themes/digital-rain.ts`

- [ ] **Step 1: Implement the digital rain theme**

Create `neuro_web/components/three/themes/digital-rain.ts`:

```typescript
import * as THREE from 'three';
import { ThemeModule } from './types';

const COLUMN_COUNT = 60;
const CHARS_PER_COLUMN = 25;

let rainGroup: THREE.Group;
let columns: { mesh: THREE.InstancedMesh; speeds: number[]; offsets: number[] }[] = [];

// Simple plane geometry for characters
let charGeometry: THREE.PlaneGeometry;

function setup(scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) {
  camera.position.z = 15;
  scene.fog = new THREE.FogExp2(0x050510, 0.05);
  renderer.setClearColor(0x050510, 1);

  rainGroup = new THREE.Group();
  charGeometry = new THREE.PlaneGeometry(0.12, 0.18);

  for (let col = 0; col < COLUMN_COUNT; col++) {
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color().setHSL(0.45 + Math.random() * 0.15, 0.8, 0.3 + Math.random() * 0.2),
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const mesh = new THREE.InstancedMesh(charGeometry, material, CHARS_PER_COLUMN);
    const speeds: number[] = [];
    const offsets: number[] = [];

    const x = (col - COLUMN_COUNT / 2) * 0.45;
    const z = (Math.random() - 0.5) * 8 - 3;

    const dummy = new THREE.Object3D();
    for (let i = 0; i < CHARS_PER_COLUMN; i++) {
      dummy.position.set(x, (i - CHARS_PER_COLUMN / 2) * 0.3, z);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      speeds.push(Math.random() * 2 + 1);
      offsets.push(Math.random() * 20);
    }
    mesh.instanceMatrix.needsUpdate = true;

    columns.push({ mesh, speeds, offsets });
    rainGroup.add(mesh);
  }

  scene.add(rainGroup);
}

function animate(time: number, _delta: number) {
  const t = time * 0.001;
  const dummy = new THREE.Object3D();

  for (const col of columns) {
    for (let i = 0; i < CHARS_PER_COLUMN; i++) {
      col.mesh.getMatrixAt(i, dummy.matrix);
      dummy.matrix.decompose(dummy.position, dummy.quaternion, dummy.scale);

      // Move down
      dummy.position.y -= col.speeds[i] * 0.008;

      // Reset to top when off screen
      if (dummy.position.y < -CHARS_PER_COLUMN * 0.15) {
        dummy.position.y = CHARS_PER_COLUMN * 0.15;
      }

      // Flicker opacity via scale
      const flicker = Math.sin(t * col.speeds[i] + col.offsets[i]) * 0.5 + 0.5;
      dummy.scale.setScalar(0.5 + flicker * 0.5);

      dummy.updateMatrix();
      col.mesh.setMatrixAt(i, dummy.matrix);
    }
    col.mesh.instanceMatrix.needsUpdate = true;
  }
}

function cleanup() {
  charGeometry?.dispose();
  columns.forEach(c => {
    (c.mesh.material as THREE.Material).dispose();
    c.mesh.geometry.dispose();
  });
  columns = [];
}

const theme: ThemeModule = {
  config: { name: 'digital-rain', label: 'Digital Rain', description: 'Matrix-style falling data streams' },
  setup,
  animate,
  cleanup,
};

export default theme;
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/three/themes/digital-rain.ts
git commit -m "feat(3d): add digital rain theme"
```

---

## Task 5: Create ThreeBackground Component

**Files:**
- Create: `neuro_web/components/three/ThreeBackground.tsx`

- [ ] **Step 1: Create the background renderer component**

Create `neuro_web/components/three/ThreeBackground.tsx`:

```typescript
'use client';
import { useEffect, useRef } from 'react';
import { useAppSelector } from '@/store/hooks';
import type { ThemeId, ThemeModule } from './themes/types';

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

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);

      // Load theme module
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
      }

      // Resize handler
      const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        activeTheme?.onResize?.(window.innerWidth, window.innerHeight);
      };
      window.addEventListener('resize', onResize);

      // Animation loop
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

      // Cleanup stored for effect teardown
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
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/three/ThreeBackground.tsx
git commit -m "feat(3d): create ThreeBackground renderer component"
```

---

## Task 6: Add Theme State to Redux and Theme Selector UI

**Files:**
- Modify: `neuro_web/store/uiSlice.ts`
- Create: `neuro_web/components/three/ThemeSelector.tsx`

- [ ] **Step 1: Add theme to uiSlice**

In `neuro_web/store/uiSlice.ts`, add `theme` to the state:

Add the import and type at the top:
```typescript
type ThemeId = 'neural-network' | 'deep-space' | 'digital-rain' | 'minimal-dark';
```

Add to `UIState` interface:
```typescript
  theme: ThemeId;
```

Add to `initialState`:
```typescript
  theme: (typeof window !== 'undefined' && localStorage.getItem('neuro_theme') as ThemeId) || 'neural-network',
```

Wait — can't access `localStorage` in module scope with SSR. Use a simpler default:
```typescript
  theme: 'neural-network' as ThemeId,
```

Add reducer:
```typescript
    setTheme(state, action: PayloadAction<ThemeId>) {
      state.theme = action.payload;
      if (typeof window !== 'undefined') localStorage.setItem('neuro_theme', action.payload);
    },
```

Export action:
```typescript
export const { setSidebarOpen, setSidebarWidth, setShowProjectCreate, setShowAgentDropdown, setConnectionStatus, setTtsAutoPlay, setTheme } = uiSlice.actions;
```

- [ ] **Step 2: Create ThemeSelector component**

Create `neuro_web/components/three/ThemeSelector.tsx`:

```typescript
'use client';
import { useEffect, useRef, useState } from 'react';
import { Palette } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setTheme } from '@/store/uiSlice';

const THEMES = [
  { id: 'neural-network', label: 'Neural Network', emoji: '🧠', color: '#8B5CF6' },
  { id: 'deep-space', label: 'Deep Space', emoji: '🌌', color: '#4a6aaa' },
  { id: 'digital-rain', label: 'Digital Rain', emoji: '💻', color: '#22C55E' },
  { id: 'minimal-dark', label: 'Minimal Dark', emoji: '🌑', color: '#555' },
] as const;

export default function ThemeSelector() {
  const dispatch = useAppDispatch();
  const currentTheme = useAppSelector(s => s.ui.theme);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Restore from localStorage on mount
    const saved = localStorage.getItem('neuro_theme');
    if (saved && saved !== currentTheme) {
      dispatch(setTheme(saved as any));
    }
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const current = THEMES.find(t => t.id === currentTheme) ?? THEMES[0];

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '8px', padding: '5px 10px', cursor: 'pointer',
          fontSize: '12px', color: '#999', transition: 'all 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(139,92,246,0.3)')}
        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
        title="Change 3D theme"
      >
        <Palette size={13} color={current.color} />
        <span>{current.label}</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: '6px',
          background: '#16162a', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '10px', minWidth: '200px', zIndex: 1000,
          boxShadow: '0 12px 40px rgba(0,0,0,0.6)', padding: '4px',
          overflow: 'hidden',
        }}>
          {THEMES.map(theme => {
            const isSelected = currentTheme === theme.id;
            return (
              <div
                key={theme.id}
                onClick={() => { dispatch(setTheme(theme.id as any)); setOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '8px 12px', cursor: 'pointer', fontSize: '12px',
                  color: isSelected ? theme.color : '#ddd',
                  background: isSelected ? `${theme.color}15` : 'transparent',
                  borderRadius: '7px', transition: 'background 0.12s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? `${theme.color}15` : 'transparent'; }}
              >
                <span>{theme.emoji}</span>
                <span style={{ fontWeight: isSelected ? 600 : 400 }}>{theme.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/store/uiSlice.ts neuro_web/components/three/ThemeSelector.tsx
git commit -m "feat(3d): add theme state to Redux and ThemeSelector component"
```

---

## Task 7: Wire ThreeBackground into Layout and Make UI Semi-Transparent

**Files:**
- Modify: `neuro_web/app/page.tsx`
- Modify: `neuro_web/app/globals.css`
- Modify: `neuro_web/components/layout/TopBar.tsx` (add ThemeSelector)

- [ ] **Step 1: Add ThreeBackground to the main page layout**

In `neuro_web/app/page.tsx`, add import at top:

```typescript
import dynamic from 'next/dynamic';
const ThreeBackground = dynamic(() => import('@/components/three/ThreeBackground'), { ssr: false });
```

Then add `<ThreeBackground />` as the first child inside the root div (before `<TopBar />`):

Change the return JSX root div from:
```tsx
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', overflow: 'hidden', background: '#0a0a1a',
    }}>
      <TopBar />
```

To:
```tsx
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', overflow: 'hidden', background: 'transparent',
      position: 'relative', zIndex: 1,
    }}>
      <ThreeBackground />
      <TopBar />
```

- [ ] **Step 2: Update globals.css for semi-transparent surfaces**

Update CSS variables in `neuro_web/app/globals.css`:

```css
:root {
  --bg-deep: rgba(6, 6, 18, 0.85);
  --bg-base: rgba(10, 10, 26, 0.7);
  --bg-surface: rgba(15, 15, 32, 0.65);
  --bg-elevated: rgba(26, 26, 46, 0.75);
  --primary: #8B5CF6;
  --text-primary: #e0e0e0;
  --text-secondary: #888888;
  --text-muted: #555555;
  --success: #4ade80;
  --warning: #f59e0b;
  --error: #ef4444;
}
```

Update html/body background:
```css
html, body {
  height: 100%;
  overflow: hidden;
  background: #060612;
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 3: Add ThemeSelector to TopBar**

In `neuro_web/components/layout/TopBar.tsx`, import and render the ThemeSelector alongside existing controls. Add:

```typescript
import ThemeSelector from '@/components/three/ThemeSelector';
```

Then place `<ThemeSelector />` in the TopBar's right-side controls area.

- [ ] **Step 4: Make existing surfaces use CSS variables for transparency**

Update inline background colors across key components to use `var(--bg-surface)` etc. instead of hardcoded opaque hex values. Key files:
- `page.tsx`: main container → `background: 'transparent'`, inner content area → `background: var(--bg-surface)`
- `Sidebar`: `background: var(--bg-deep)`
- `ChatInput`: `background: var(--bg-surface)`
- `ChatPanel`: scrollable area → `background: transparent`

- [ ] **Step 5: Verify build and commit**

```bash
cd neuro_web && npx next build
git add neuro_web/app/page.tsx neuro_web/app/globals.css neuro_web/components/layout/TopBar.tsx
git commit -m "feat(3d): wire ThreeBackground into layout with semi-transparent UI"
```

---

## Task 8: Final Integration and Testing

- [ ] **Step 1: Verify all 4 themes work**

Start the dev server and test each theme:
1. Default: Neural Network — particles with connections
2. Switch to Deep Space — stars and orbs
3. Switch to Digital Rain — falling columns
4. Switch to Minimal Dark — no canvas, clean dark background

- [ ] **Step 2: Verify theme persists across reload**

Select "Deep Space", refresh browser, verify it loads Deep Space.

- [ ] **Step 3: Verify chat functionality unaffected**

Send a text message, verify it appears. Start a voice call, verify it works. Check sidebar, tabs, agent selector all functional.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "feat(3d): complete 3D theme system with 4 themes"
```
