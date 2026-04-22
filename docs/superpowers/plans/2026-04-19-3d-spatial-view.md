# 3D Spatial View Implementation Plan (Phase A prototype)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a working 3D spatial alternative to the linear tab bar, toggleable from Settings. Each open tab renders as a 3D card; click flies into focus, Esc flies out. Zero backend changes.

**Architecture:** `@react-three/fiber` + `@react-three/drei` over existing `three@0.183`. A `SpatialRoot` component replaces the `ChatPanel/ChatInput/TerminalPanel` area when `ui.interfaceMode === 'spatial'`. Nodes clustered by project. Minimap in a separate small `<Canvas>`. Focus mode reuses today's `ChatPanel` / `TerminalPanel` as an overlay.

**Tech Stack:** React 18, Redux Toolkit, three 0.183, new deps `@react-three/fiber` + `@react-three/drei`.

---

## Task 1: Deps + uiSlice extension

**Files:**
- Modify: `neuro_web/package.json`
- Modify: `neuro_web/store/uiSlice.ts`

- [ ] **Step 1: Install r3f packages**

Run in `neuro_web/`:
```bash
npm install @react-three/fiber @react-three/drei
```

- [ ] **Step 2: Add `interfaceMode` and `focusedCid` to uiSlice**

Open `store/uiSlice.ts`. Add to state interface:
```ts
interfaceMode: 'classic' | 'spatial';
focusedCid: string | null;
```
Default `'classic'` and `null`. Add reducers:
```ts
setInterfaceMode(state, a: PayloadAction<'classic' | 'spatial'>) {
  state.interfaceMode = a.payload;
},
setFocusedCid(state, a: PayloadAction<string | null>) {
  state.focusedCid = a.payload;
},
```
Export both actions. If uiSlice already persists via localStorage, include the new key in the persisted shape.

- [ ] **Step 3: Commit**

```bash
git add neuro_web/package.json neuro_web/package-lock.json neuro_web/store/uiSlice.ts
git commit -m "feat(3d): add r3f deps + interfaceMode state"
```

---

## Task 2: Settings toggle

**Files:**
- Modify: `neuro_web/app/settings/page.tsx`

- [ ] **Step 1: Add a row at the top of `AppearanceSection`**

Find `AppearanceSection` in `app/settings/page.tsx`. Above the existing "Tab bar position" row, insert:

```tsx
const interfaceMode = useAppSelector(s => s.ui.interfaceMode);

<Row label="Interface mode"
     description="Switch between classic tabs and a 3D spatial view of your open sessions.">
  <SegmentedControl
    value={interfaceMode}
    options={[
      { value: 'classic', label: 'Classic' },
      { value: 'spatial', label: '3D' },
    ]}
    onChange={v => dispatch(setInterfaceMode(v))}
  />
</Row>
```

Import `setInterfaceMode` from `@/store/uiSlice`.

- [ ] **Step 2: Commit**

```bash
git add neuro_web/app/settings/page.tsx
git commit -m "feat(3d): Settings → Appearance → Interface mode toggle"
```

---

## Task 3: SpatialRoot skeleton + Canvas mount

**Files:**
- Create: `neuro_web/components/spatial/SpatialRoot.tsx`
- Create: `neuro_web/components/spatial/types.ts`

- [ ] **Step 1: Types**

```ts
// components/spatial/types.ts
export interface NodeModel {
  cid: string;
  title: string;
  kind: 'chat' | 'terminal' | 'dashboard';
  projectId: string | null;
  position: [number, number, number];
  active: boolean;
  running?: boolean;
}
```

- [ ] **Step 2: Skeleton root**

```tsx
// components/spatial/SpatialRoot.tsx
'use client';
import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useAppSelector } from '@/store/hooks';
import type { NodeModel } from './types';

const COLOR: Record<NodeModel['kind'], string> = {
  chat: '#3b82f6',
  terminal: '#22c55e',
  dashboard: '#a855f7',
};

export default function SpatialRoot() {
  const tabs = useAppSelector(s => s.conversations.openTabs);
  const activeCid = useAppSelector(s => s.conversations.activeTabCid);

  const nodes: NodeModel[] = useMemo(() => layoutNodes(tabs, activeCid), [tabs, activeCid]);

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0, background: '#05060a' }}>
      <Canvas camera={{ position: [0, 6, 12], fov: 55 }}>
        <color attach="background" args={['#05060a']} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        <Suspense fallback={null}>
          {nodes.map(n => (
            <mesh key={n.cid} position={n.position}>
              <boxGeometry args={[1.6, 0.9, 0.12]} />
              <meshStandardMaterial color={COLOR[n.kind]} />
            </mesh>
          ))}
        </Suspense>
        <OrbitControls enableDamping makeDefault />
        <gridHelper args={[30, 30, '#1f2937', '#111827']} position={[0, -0.5, 0]} />
      </Canvas>
    </div>
  );
}

function layoutNodes(tabs: { cid: string; title: string; agentId: string; type?: string; }[], activeCid: string | null): NodeModel[] {
  // Group by projectId if present on tab; MVP treats every tab as one cluster
  // for simplicity. Next task expands this.
  return tabs.map((t, i) => ({
    cid: t.cid,
    title: t.title,
    kind: (t.type === 'terminal' ? 'terminal' : 'chat'),
    projectId: null,
    position: [(i % 6) * 2 - 5, 0, Math.floor(i / 6) * 2],
    active: t.cid === activeCid,
  }));
}
```

- [ ] **Step 3: Wire into `app/page.tsx`**

Import and switch on `interfaceMode`:

```tsx
const SpatialRoot = dynamic(() => import('@/components/spatial/SpatialRoot'), { ssr: false });
const interfaceMode = useAppSelector(s => s.ui.interfaceMode);
// ...
{interfaceMode === 'spatial'
  ? <SpatialRoot />
  : (activeTabKind === 'terminal'
      ? <TerminalPanel />
      : <><ChatPanel /><ChatInput /></>)}
```

- [ ] **Step 4: Manual smoke**

Restart frontend dev. Toggle Settings → 3D. Main panel becomes a dark 3D scene with colored boxes, one per open tab. Drag rotates, scroll zooms.

- [ ] **Step 5: Commit**

```bash
git add neuro_web/components/spatial neuro_web/app/page.tsx
git commit -m "feat(3d): SpatialRoot + Canvas mount, primitive nodes"
```

---

## Task 4: Session card visuals + billboard + cluster-by-project

**Files:**
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`
- Create: `neuro_web/components/spatial/SessionCard.tsx`

- [ ] **Step 1: Build `SessionCard.tsx`**

```tsx
'use client';
import { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Billboard, RoundedBox, Text } from '@react-three/drei';
import * as THREE from 'three';
import type { NodeModel } from './types';

const COLOR: Record<NodeModel['kind'], string> = {
  chat: '#3b82f6', terminal: '#22c55e', dashboard: '#a855f7',
};
const ICON: Record<NodeModel['kind'], string> = {
  chat: '\u{1F4AC}', terminal: '>_', dashboard: '\u{1F4CA}',
};

interface Props {
  node: NodeModel;
  selected: boolean;
  onClick: () => void;
  onDoubleClick: () => void;
}

export default function SessionCard({ node, selected, onClick, onDoubleClick }: Props) {
  const ref = useRef<THREE.Mesh>(null);
  const [hover, setHover] = useState(false);

  useFrame((_, dt) => {
    if (!ref.current) return;
    const target = (hover || selected) ? 1.08 : 1;
    ref.current.scale.lerp(new THREE.Vector3(target, target, target), Math.min(1, dt * 10));
  });

  const glow = hover || selected;
  const activityColor = node.running ? '#c4b5fd' : '#334155';

  return (
    <Billboard follow position={node.position}>
      <mesh
        ref={ref}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { setHover(false); document.body.style.cursor = ''; }}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
        onDoubleClick={(e) => { e.stopPropagation(); onDoubleClick(); }}
      >
        <RoundedBox args={[1.6, 0.9, 0.12]} radius={0.08} smoothness={4}>
          <meshStandardMaterial
            color={COLOR[node.kind]}
            emissive={glow ? '#7170ff' : '#000000'}
            emissiveIntensity={glow ? 0.6 : 0}
            metalness={0.2}
            roughness={0.4}
          />
        </RoundedBox>
        <Text
          position={[0, 0.15, 0.07]}
          fontSize={0.12}
          color="#ffffff"
          anchorX="center"
          anchorY="middle"
          maxWidth={1.4}
        >
          {ICON[node.kind]} {truncate(node.title, 18)}
        </Text>
        <mesh position={[-0.68, -0.33, 0.07]}>
          <circleGeometry args={[0.04, 16]} />
          <meshStandardMaterial color={activityColor} emissive={activityColor} emissiveIntensity={0.6} />
        </mesh>
        {selected && (
          <mesh position={[0, -0.48, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.5, 0.55, 32]} />
            <meshBasicMaterial color="#7170ff" transparent opacity={0.6} />
          </mesh>
        )}
      </mesh>
    </Billboard>
  );
}

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n - 1) + '…';
}
```

- [ ] **Step 2: Replace primitives in `SpatialRoot` with `SessionCard`**

Swap `mesh/boxGeometry` loop for:

```tsx
{nodes.map(n => (
  <SessionCard
    key={n.cid}
    node={n}
    selected={n.cid === selectedCid}
    onClick={() => setSelectedCid(n.cid)}
    onDoubleClick={() => dispatch(setFocusedCid(n.cid))}
  />
))}
```

Add `const [selectedCid, setSelectedCid] = useState<string | null>(activeCid);` at top of the component. Import `setFocusedCid`.

- [ ] **Step 3: Upgrade `layoutNodes` — cluster by project**

```ts
function layoutNodes(
  tabs: { cid: string; title: string; type?: string; }[],
  activeCid: string | null,
  projectByCid: Record<string, string | null>,
): NodeModel[] {
  const groups = new Map<string, typeof tabs>();
  for (const t of tabs) {
    const key = projectByCid[t.cid] || '__no_project__';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(t);
  }
  const out: NodeModel[] = [];
  let clusterIdx = 0;
  for (const [pid, members] of groups.entries()) {
    const cols = Math.ceil(Math.sqrt(members.length));
    const cx = (clusterIdx % 4) * 8 - 12;
    const cz = Math.floor(clusterIdx / 4) * 6 - 4;
    members.forEach((t, i) => {
      const col = i % cols, row = Math.floor(i / cols);
      out.push({
        cid: t.cid,
        title: t.title,
        kind: (t.type === 'terminal' ? 'terminal' : 'chat'),
        projectId: pid === '__no_project__' ? null : pid,
        position: [cx + (col - (cols - 1) / 2) * 2.0, 0, cz + row * 1.6],
        active: t.cid === activeCid,
      });
    });
    clusterIdx++;
  }
  return out;
}
```

Build `projectByCid` by reading `state.conversations.conversations` (array with `id + projectId`).

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/spatial
git commit -m "feat(3d): SessionCard with hover/selected + cluster-by-project layout"
```

---

## Task 5: Camera fly-to on focus + dim on focus

**Files:**
- Create: `neuro_web/components/spatial/CameraRig.tsx`
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`

- [ ] **Step 1: CameraRig**

```tsx
'use client';
import { useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Props {
  target: THREE.Vector3 | null;          // null = free-orbit
  controlsRef: React.RefObject<any>;
}

export default function CameraRig({ target, controlsRef }: Props) {
  const { camera } = useThree();
  const savedPose = useRef<{ pos: THREE.Vector3; tgt: THREE.Vector3 } | null>(null);
  const desiredPos = useRef<THREE.Vector3 | null>(null);
  const desiredTarget = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    if (target && !savedPose.current) {
      const ctrl = controlsRef.current;
      savedPose.current = {
        pos: camera.position.clone(),
        tgt: ctrl ? ctrl.target.clone() : new THREE.Vector3(),
      };
    }
    if (target) {
      const offset = new THREE.Vector3(0, 0.4, 1.2);
      desiredPos.current = target.clone().add(offset);
      desiredTarget.current = target.clone();
    } else if (savedPose.current) {
      desiredPos.current = savedPose.current.pos.clone();
      desiredTarget.current = savedPose.current.tgt.clone();
      savedPose.current = null;
    }
  }, [target, camera, controlsRef]);

  useFrame((_, dt) => {
    const ctrl = controlsRef.current;
    if (!desiredPos.current || !desiredTarget.current || !ctrl) return;
    const k = Math.min(1, dt * 5);
    camera.position.lerp(desiredPos.current, k);
    ctrl.target.lerp(desiredTarget.current, k);
    ctrl.update();
  });

  return null;
}
```

- [ ] **Step 2: Wire in `SpatialRoot`**

```tsx
import CameraRig from './CameraRig';
import * as THREE from 'three';

const focusedCid = useAppSelector(s => s.ui.focusedCid);
const controlsRef = useRef<any>(null);
const focusedNode = nodes.find(n => n.cid === focusedCid) || null;
const focusTarget = focusedNode
  ? new THREE.Vector3(...focusedNode.position)
  : null;
```

Replace `<OrbitControls enableDamping makeDefault />` with:

```tsx
<OrbitControls ref={controlsRef} enableDamping makeDefault enabled={!focusTarget} />
<CameraRig target={focusTarget} controlsRef={controlsRef} />
```

- [ ] **Step 3: Dim scene during focus**

Wrap everything inside `<Canvas>` children in a `<group>` and animate opacity via `useFrame`:

```tsx
import { useFrame } from '@react-three/fiber';

function SceneDimmer({ dimmed, children }: { dimmed: boolean; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (!ref.current) return;
    const target = dimmed ? 0.35 : 1;
    ref.current.traverse((o: any) => {
      if (o.material && 'opacity' in o.material) {
        o.material.transparent = true;
        o.material.opacity += (target - o.material.opacity) * Math.min(1, dt * 5);
      }
    });
  });
  return <group ref={ref}>{children}</group>;
}
```

Use: `<SceneDimmer dimmed={!!focusTarget}>{/* nodes + grid */}</SceneDimmer>`.

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/spatial
git commit -m "feat(3d): CameraRig fly-to + SceneDimmer on focus"
```

---

## Task 6: Focus overlay — reuse ChatPanel / TerminalPanel

**Files:**
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`

- [ ] **Step 1: Add overlay DOM**

Below the `<Canvas>` block in `SpatialRoot`, render:

```tsx
{focusedCid && (
  <div style={{
    position: 'absolute', inset: 0, pointerEvents: 'none',
    display: 'flex', alignItems: 'stretch',
  }}>
    <div style={{
      pointerEvents: 'auto',
      position: 'absolute', left: '8%', right: '8%',
      top: '8%', bottom: '8%',
      background: 'rgba(15, 16, 17, 0.82)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 10,
      backdropFilter: 'blur(16px)',
      boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      <FocusedPanel cid={focusedCid} />
    </div>
  </div>
)}
```

- [ ] **Step 2: Build `FocusedPanel`**

Inside the same file:

```tsx
function FocusedPanel({ cid }: { cid: string }) {
  const tab = useAppSelector(s => s.conversations.openTabs.find(t => t.cid === cid));
  const dispatch = useAppDispatch();
  useEffect(() => {
    // Make the focused cid the active tab so ChatPanel / TerminalPanel read correctly
    dispatch(setActiveTab(cid));
  }, [cid, dispatch]);
  if (!tab) return null;
  if (tab.type === 'terminal') return <TerminalPanel />;
  return (<><ChatPanel /><ChatInput /></>);
}
```

Imports needed: `useAppDispatch`, `setActiveTab` from `@/store/conversationSlice`, `ChatPanel`, `ChatInput`, `TerminalPanel`.

- [ ] **Step 3: Keyboard — Esc exits focus**

Add to `SpatialRoot`:

```tsx
useEffect(() => {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && focusedCid) { dispatch(setFocusedCid(null)); }
  };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [focusedCid, dispatch]);
```

- [ ] **Step 4: Manual smoke**

In 3D mode: double-click a card → chat panel appears centred; type + send works. Terminal tab → xterm shows and works. Esc → overlay hides, camera returns to original pose.

- [ ] **Step 5: Commit**

```bash
git add neuro_web/components/spatial/SpatialRoot.tsx
git commit -m "feat(3d): focus overlay reusing ChatPanel/TerminalPanel"
```

---

## Task 7: HUD + keyboard cheatsheet

**Files:**
- Create: `neuro_web/components/spatial/HUD.tsx`
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`

- [ ] **Step 1: HUD**

```tsx
'use client';
import { useState } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setInterfaceMode } from '@/store/uiSlice';
import { Layout, Keyboard } from 'lucide-react';

export default function HUD() {
  const dispatch = useAppDispatch();
  const [showHelp, setShowHelp] = useState(false);
  return (
    <>
      <div style={{
        position: 'absolute', top: 12, left: 12, display: 'flex', gap: 6,
        pointerEvents: 'auto',
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
          pointerEvents: 'auto',
        }}>
          <div>LMB drag — orbit · RMB drag — pan · scroll — zoom</div>
          <div>Click — select · Dbl-click / Enter — focus</div>
          <div>Esc — exit focus · F — frame selected</div>
          <div>WASD — fly · Q/E — up/down</div>
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
  fontFamily: 'inherit', backdropFilter: 'blur(6px)',
};
```

- [ ] **Step 2: Mount in `SpatialRoot`**

Inside the top-level wrapper div, after the `<Canvas>` + focus overlay:

```tsx
<HUD />
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/spatial/HUD.tsx neuro_web/components/spatial/SpatialRoot.tsx
git commit -m "feat(3d): HUD with Classic-mode switch + keyboard cheatsheet"
```

---

## Task 8: WASD fly + Tab cycle + F frame

**Files:**
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`

- [ ] **Step 1: WASD on window**

```tsx
useEffect(() => {
  const keys = new Set<string>();
  const onDown = (e: KeyboardEvent) => keys.add(e.key.toLowerCase());
  const onUp = (e: KeyboardEvent) => keys.delete(e.key.toLowerCase());
  window.addEventListener('keydown', onDown);
  window.addEventListener('keyup', onUp);
  let raf = 0;
  const loop = () => {
    const ctrl = controlsRef.current;
    const cam = ctrl?.object;
    if (cam && !focusedCid) {
      const speed = 0.12;
      const forward = new THREE.Vector3();
      cam.getWorldDirection(forward); forward.y = 0; forward.normalize();
      const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();
      const d = new THREE.Vector3();
      if (keys.has('w')) d.add(forward);
      if (keys.has('s')) d.sub(forward);
      if (keys.has('d')) d.add(right);
      if (keys.has('a')) d.sub(right);
      if (keys.has('q')) d.y -= 1;
      if (keys.has('e')) d.y += 1;
      if (d.lengthSq() > 0) {
        d.multiplyScalar(speed);
        cam.position.add(d);
        ctrl.target.add(d);
        ctrl.update();
      }
    }
    raf = requestAnimationFrame(loop);
  };
  raf = requestAnimationFrame(loop);
  return () => {
    cancelAnimationFrame(raf);
    window.removeEventListener('keydown', onDown);
    window.removeEventListener('keyup', onUp);
  };
}, [focusedCid]);
```

- [ ] **Step 2: `Tab` cycles selection, `Enter` focuses, `F` frames**

Extend the existing keydown handler:

```tsx
if (e.key === 'Tab' && nodes.length) {
  e.preventDefault();
  const idx = nodes.findIndex(n => n.cid === selectedCid);
  const next = nodes[(idx + (e.shiftKey ? -1 : 1) + nodes.length) % nodes.length];
  setSelectedCid(next.cid);
}
if (e.key === 'Enter' && selectedCid) {
  dispatch(setFocusedCid(selectedCid));
}
if (e.key.toLowerCase() === 'f' && selectedCid) {
  // frame: dispatch a one-shot fly-to by temporarily setting focus target
  // without entering focus overlay. For MVP: just enter focus.
  dispatch(setFocusedCid(selectedCid));
}
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/spatial/SpatialRoot.tsx
git commit -m "feat(3d): WASD fly, Tab cycle, Enter/F focus"
```

---

## Task 9: Minimap

**Files:**
- Create: `neuro_web/components/spatial/Minimap.tsx`
- Modify: `neuro_web/components/spatial/SpatialRoot.tsx`

- [ ] **Step 1: Build Minimap**

```tsx
'use client';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import type { NodeModel } from './types';

interface Props {
  nodes: NodeModel[];
  cameraPos: THREE.Vector3;
  cameraYaw: number;
  onClick: (x: number, z: number) => void;
}

function Tri({ pos, yaw }: { pos: THREE.Vector3; yaw: number }) {
  return (
    <mesh position={[pos.x, 0, pos.z]} rotation={[-Math.PI / 2, 0, -yaw]}>
      <coneGeometry args={[0.6, 1.4, 3]} />
      <meshBasicMaterial color="#fde047" />
    </mesh>
  );
}

export default function Minimap({ nodes, cameraPos, cameraYaw, onClick }: Props) {
  return (
    <div style={{
      position: 'absolute', top: 12, right: 12,
      width: 180, height: 120, borderRadius: 8, overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.1)',
      background: 'rgba(5,6,10,0.9)', pointerEvents: 'auto',
    }}
    onClick={(e) => {
      const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      const nz = ((e.clientY - r.top) / r.height) * 2 - 1;
      // orthographic half-size = 18
      onClick(nx * 18, nz * 12);
    }}>
      <Canvas orthographic camera={{ position: [0, 40, 0], up: [0, 0, -1], near: 0.1, far: 100, zoom: 6 }}>
        <ambientLight intensity={1} />
        {nodes.map(n => (
          <mesh key={n.cid} position={[n.position[0], 0, n.position[2]]}>
            <boxGeometry args={[0.9, 0.2, 0.6]} />
            <meshBasicMaterial color={n.kind === 'terminal' ? '#22c55e' : '#3b82f6'} />
          </mesh>
        ))}
        <Tri pos={cameraPos} yaw={cameraYaw} />
      </Canvas>
    </div>
  );
}
```

- [ ] **Step 2: Mount in `SpatialRoot`**

Track camera pose in state via `useFrame` inside the main Canvas (or by reading `controlsRef.current.object.position` + `rotation.y` on each render). A simple-but-good-enough approach:

```tsx
const [camPose, setCamPose] = useState({ pos: new THREE.Vector3(0, 6, 12), yaw: 0 });
// Inside Canvas add a <CamWatcher onChange={setCamPose} />
```

Where `CamWatcher`:
```tsx
function CamWatcher({ onChange }: { onChange: (p: { pos: THREE.Vector3; yaw: number; }) => void }) {
  const { camera } = useThree();
  useFrame(() => {
    onChange({ pos: camera.position.clone(), yaw: camera.rotation.y });
  });
  return null;
}
```

Then below `<Canvas>`:
```tsx
<Minimap
  nodes={nodes}
  cameraPos={camPose.pos}
  cameraYaw={camPose.yaw}
  onClick={(x, z) => {
    const ctrl = controlsRef.current;
    if (!ctrl) return;
    const d = new THREE.Vector3(x - ctrl.target.x, 0, z - ctrl.target.z);
    ctrl.object.position.add(d);
    ctrl.target.add(d);
    ctrl.update();
  }}
/>
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/spatial/Minimap.tsx neuro_web/components/spatial/SpatialRoot.tsx
git commit -m "feat(3d): minimap with click-to-teleport"
```

---

## Task 10: Smoke + polish

- [ ] Manual checklist from the design spec.
- [ ] If WebGL context is lost or R3F throws, wrap `SpatialRoot` in an error boundary that falls back to classic mode with a toast.
- [ ] Fix any fitful visuals: ensure OrbitControls doesn't pan underground (`maxPolarAngle = Math.PI / 2 - 0.05`).
- [ ] Commit any polish.

---

## Critical files

| Action | Path |
|---|---|
| Create | `neuro_web/components/spatial/SpatialRoot.tsx` |
| Create | `neuro_web/components/spatial/SessionCard.tsx` |
| Create | `neuro_web/components/spatial/CameraRig.tsx` |
| Create | `neuro_web/components/spatial/HUD.tsx` |
| Create | `neuro_web/components/spatial/Minimap.tsx` |
| Create | `neuro_web/components/spatial/types.ts` |
| Modify | `neuro_web/store/uiSlice.ts` |
| Modify | `neuro_web/app/page.tsx` |
| Modify | `neuro_web/app/settings/page.tsx` |
| Modify | `neuro_web/package.json` |

No backend edits, no data migration.
