'use client';
import { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Billboard, RoundedBox, Text } from '@react-three/drei';
import * as THREE from 'three';
import type { NodeModel } from './types';

const COLOR: Record<NodeModel['kind'], string> = {
  chat: '#3b82f6',
  terminal: '#22c55e',
  dashboard: '#a855f7',
};

const ICON: Record<NodeModel['kind'], string> = {
  chat: '\u{1F4AC}',
  terminal: '>_',
  dashboard: '\u{1F4CA}',
};

interface Props {
  node: NodeModel;
  selected: boolean;
  onClick: () => void;
  onDoubleClick: () => void;
}

export default function SessionCard({ node, selected, onClick, onDoubleClick }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const [hover, setHover] = useState(false);

  useFrame((_, dt) => {
    if (!groupRef.current) return;
    const target = hover || selected ? 1.08 : 1;
    const s = groupRef.current.scale;
    s.lerp(new THREE.Vector3(target, target, target), Math.min(1, dt * 10));
  });

  const glow = hover || selected;
  const activityColor = node.running ? '#c4b5fd' : '#334155';

  return (
    <Billboard follow position={node.position}>
      <group
        ref={groupRef}
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
          fontSize={0.13}
          color="#ffffff"
          anchorX="center"
          anchorY="middle"
          maxWidth={1.4}
        >
          {`${ICON[node.kind]}  ${truncate(node.title, 18)}`}
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
      </group>
    </Billboard>
  );
}

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n - 1) + '…';
}
