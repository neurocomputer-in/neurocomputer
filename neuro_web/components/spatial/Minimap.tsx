'use client';
import { Canvas } from '@react-three/fiber';
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
    <mesh position={[pos.x, 0.2, pos.z]} rotation={[-Math.PI / 2, 0, -yaw]}>
      <coneGeometry args={[0.6, 1.4, 3]} />
      <meshBasicMaterial color="#fde047" />
    </mesh>
  );
}

export default function Minimap({ nodes, cameraPos, cameraYaw, onClick }: Props) {
  // Ortho half-width ≈ 18 (zoom=6, width=180 → 180/(6*2) = 15); we use a
  // comfortable 18/12 mapping so clicks land near the visible area without
  // needing exact geometry.
  return (
    <div
      style={{
        position: 'absolute', top: 12, right: 12,
        width: 180, height: 120, borderRadius: 8, overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.1)',
        background: 'rgba(5,6,10,0.9)', pointerEvents: 'auto', zIndex: 15,
      }}
      onClick={(e) => {
        const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
        const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
        const nz = ((e.clientY - r.top) / r.height) * 2 - 1;
        onClick(nx * 18, nz * 12);
      }}
    >
      <Canvas
        orthographic
        camera={{ position: [0, 40, 0], up: [0, 0, -1], near: 0.1, far: 100, zoom: 6 }}
      >
        <ambientLight intensity={1} />
        {nodes.map(n => (
          <mesh key={n.cid} position={[n.position[0], 0, n.position[2]]}>
            <boxGeometry args={[0.9, 0.2, 0.6]} />
            <meshBasicMaterial color={colorFor(n.kind)} />
          </mesh>
        ))}
        <Tri pos={cameraPos} yaw={cameraYaw} />
      </Canvas>
    </div>
  );
}

function colorFor(kind: NodeModel['kind']): string {
  switch (kind) {
    case 'terminal':  return '#22c55e';
    case 'dashboard': return '#a855f7';
    default:          return '#3b82f6';
  }
}
