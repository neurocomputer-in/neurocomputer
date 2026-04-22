'use client';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import dynamic from 'next/dynamic';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setFocusedCid } from '@/store/uiSlice';
import { setActiveTab } from '@/store/conversationSlice';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';
import SessionCard from './SessionCard';
import CameraRig from './CameraRig';
import HUD from './HUD';
import Minimap from './Minimap';
import { useThree } from '@react-three/fiber';
import type { NodeModel } from './types';

const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });

interface RawTab {
  cid: string;
  title: string;
  type?: string;
}

export default function SpatialRoot() {
  const dispatch = useAppDispatch();
  const tabs = useAppSelector(s => s.conversations.openTabs) as unknown as RawTab[];
  const activeCid = useAppSelector(s => s.conversations.activeTabCid);
  const focusedCid = useAppSelector(s => s.ui.focusedCid);

  // project_id for each open tab is sourced from the conversations list we
  // already fetched. Map cid → projectId with a null fallback.
  const projectByCid = useAppSelector((s) => {
    const map: Record<string, string | null> = {};
    const list = (s.conversations.conversations as unknown as Array<{ id: string; projectId?: string | null }>) || [];
    for (const c of list) map[c.id] = c.projectId ?? null;
    return map;
  });

  const nodes: NodeModel[] = useMemo(
    () => layoutNodes(tabs, activeCid, projectByCid),
    [tabs, activeCid, projectByCid],
  );

  const [selectedCid, setSelectedCid] = useState<string | null>(activeCid);
  useEffect(() => { setSelectedCid(activeCid); }, [activeCid]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Never steal keys while focused — chat/terminal inputs need them.
      if (focusedCid) {
        if (e.key === 'Escape') dispatch(setFocusedCid(null));
        return;
      }
      const target = e.target as HTMLElement | null;
      if (target && /^(input|textarea|select)$/i.test(target.tagName)) return;
      if (target?.isContentEditable) return;

      if (e.key === 'Tab' && nodes.length) {
        e.preventDefault();
        const idx = nodes.findIndex(n => n.cid === selectedCid);
        const dir = e.shiftKey ? -1 : 1;
        const next = nodes[(idx + dir + nodes.length) % nodes.length];
        setSelectedCid(next.cid);
        return;
      }
      if ((e.key === 'Enter' || e.key.toLowerCase() === 'f') && selectedCid) {
        dispatch(setFocusedCid(selectedCid));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [focusedCid, dispatch, nodes, selectedCid]);

  // WASD fly-nav (only active when no focus, no input focused).
  useEffect(() => {
    const keys = new Set<string>();
    const onDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(input|textarea|select)$/i.test(target.tagName)) return;
      if (target?.isContentEditable) return;
      keys.add(e.key.toLowerCase());
    };
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
        cam.getWorldDirection(forward);
        forward.y = 0;
        if (forward.lengthSq() > 0) forward.normalize();
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

  const focusedNode = nodes.find(n => n.cid === focusedCid) || null;
  const focusTarget = focusedNode ? new THREE.Vector3(...focusedNode.position) : null;
  const controlsRef = useRef<any>(null);
  const [camPose, setCamPose] = useState<{ pos: THREE.Vector3; yaw: number }>({
    pos: new THREE.Vector3(0, 6, 12),
    yaw: 0,
  });

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0, background: '#05060a' }}>
      <Canvas camera={{ position: [0, 6, 12], fov: 55 }}>
        <color attach="background" args={['#05060a']} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        <SceneDimmer dimmed={!!focusTarget}>
          <Suspense fallback={null}>
            {nodes.map(n => (
              <SessionCard
                key={n.cid}
                node={n}
                selected={n.cid === selectedCid}
                onClick={() => setSelectedCid(n.cid)}
                onDoubleClick={() => dispatch(setFocusedCid(n.cid))}
              />
            ))}
          </Suspense>
          <gridHelper args={[30, 30, '#1f2937', '#111827']} position={[0, -0.5, 0]} />
        </SceneDimmer>
        <OrbitControls
          ref={controlsRef}
          enableDamping
          makeDefault
          enabled={!focusTarget}
          maxPolarAngle={Math.PI / 2 - 0.05}
        />
        <CameraRig target={focusTarget} controlsRef={controlsRef} />
        <CamWatcher onChange={setCamPose} />
      </Canvas>
      <HUD />
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
      {focusedCid && (
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
        }}>
          <div style={{
            pointerEvents: 'auto',
            position: 'absolute', left: '6%', right: '6%',
            top: '6%', bottom: '6%',
            background: 'rgba(15, 16, 17, 0.82)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 10,
            backdropFilter: 'blur(16px)',
            boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
            overflow: 'hidden',
            display: 'flex', flexDirection: 'column',
          }}>
            <FocusedPanel cid={focusedCid} onClose={() => dispatch(setFocusedCid(null))} />
          </div>
        </div>
      )}
      {nodes.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#62666d', fontSize: 14, pointerEvents: 'none',
        }}>
          Open a chat or terminal to see it in 3D.
        </div>
      )}
    </div>
  );
}

function CamWatcher({ onChange }: { onChange: (p: { pos: THREE.Vector3; yaw: number }) => void }) {
  const { camera } = useThree();
  useFrame(() => {
    onChange({ pos: camera.position.clone(), yaw: camera.rotation.y });
  });
  return null;
}

function FocusedPanel({ cid, onClose }: { cid: string; onClose: () => void }) {
  const dispatch = useAppDispatch();
  const tab = useAppSelector(s => s.conversations.openTabs.find(t => t.cid === cid));
  useEffect(() => {
    dispatch(setActiveTab(cid));
  }, [cid, dispatch]);
  if (!tab) {
    return (
      <div style={{ padding: 24, color: '#8a8f98', fontSize: 13 }}>
        Tab not found. <button onClick={onClose} style={{ marginLeft: 8 }}>close</button>
      </div>
    );
  }
  if (tab.type === 'terminal') return <TerminalPanel />;
  return (<><ChatPanel /><ChatInput /></>);
}

function SceneDimmer({ dimmed, children }: { dimmed: boolean; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (!ref.current) return;
    const target = dimmed ? 0.35 : 1;
    ref.current.traverse((o: any) => {
      const mat = o.material;
      if (mat && 'opacity' in mat) {
        mat.transparent = true;
        mat.opacity += (target - mat.opacity) * Math.min(1, dt * 5);
      }
    });
  });
  return <group ref={ref}>{children}</group>;
}

function layoutNodes(
  tabs: RawTab[],
  activeCid: string | null,
  projectByCid: Record<string, string | null>,
): NodeModel[] {
  // Group tabs by their project id (null → '__no_project__').
  const groups = new Map<string, RawTab[]>();
  for (const t of tabs) {
    const key = projectByCid[t.cid] ?? '__no_project__';
    const list = groups.get(key) ?? [];
    list.push(t);
    groups.set(key, list);
  }
  const out: NodeModel[] = [];
  let clusterIdx = 0;
  for (const [pid, members] of groups.entries()) {
    const cols = Math.max(1, Math.ceil(Math.sqrt(members.length)));
    const cx = (clusterIdx % 4) * 8 - 12;
    const cz = Math.floor(clusterIdx / 4) * 6 - 4;
    members.forEach((t, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      out.push({
        cid: t.cid,
        title: t.title,
        kind: (t.type === 'terminal' ? 'terminal' : 'chat') as NodeModel['kind'],
        projectId: pid === '__no_project__' ? null : pid,
        position: [cx + (col - (cols - 1) / 2) * 2.0, 0, cz + row * 1.6],
        active: t.cid === activeCid,
      });
    });
    clusterIdx++;
  }
  return out;
}
