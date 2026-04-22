'use client';

/**
 * 3D neuro graph — multi-resolution, fractal-friendly.
 *
 * Layers:
 *   • L0 = nebula view — each kind_namespace is a cluster-bubble.
 *   • L1 = nodes       — individual neuros, laid out in clusters.
 *   • L2 = expanded    — clicking a composite (FlowNeuro w/ children)
 *                        pops its children out around it (fractal drill).
 *
 * The layer crossfades by camera distance (semantic zoom), and the user
 * can also click a cluster to "enter" it or a composite to "expand" it.
 */

import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Line, Billboard } from '@react-three/drei';
import { useMemo, useRef, useState, useEffect } from 'react';
import * as THREE from 'three';

export type NeuroEntry = {
  name: string;
  description: string;
  kind: string;
  kind_namespace: string;
  category?: string | null;
  color?: string | null;
  uses: string[];
  children: string[];
};

type Props = {
  neuros: NeuroEntry[];
  onSelect: (name: string) => void;
};

// ── palette ───────────────────────────────────────────────────────────
const NS_COLOR: Record<string, string> = {
  skill:       '#a78bfa',
  prompt:      '#c084fc',
  context:     '#67e8f9',
  memory:      '#5eead4',
  model:       '#fb923c',
  instruction: '#fde047',
  code:        '#86efac',
  agent:       '#f9a8d4',
  dev:         '#fca5a5',
  ide:         '#60a5fa',
  util:        '#9ca3af',
  system:      '#d1d5db',
  media:       '#fbbf24',
  upwork:      '#4ade80',
  library:     '#f472b6',
};
const colorFor = (ns: string) => NS_COLOR[ns] || '#888';

// ── layout helpers ────────────────────────────────────────────────────
function fibSphere(i: number, n: number, radius: number): [number, number, number] {
  const phi = Math.acos(1 - 2 * (i + 0.5) / n);
  const theta = Math.PI * (1 + Math.sqrt(5)) * i;
  return [
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.sin(phi) * Math.sin(theta),
    radius * Math.cos(phi),
  ];
}

type Layout = {
  nodePos: Record<string, [number, number, number]>;
  clusterCenter: Record<string, [number, number, number]>;
  clusterRadius: Record<string, number>;
  clusterMembers: Record<string, string[]>;
};

function computeLayout(neuros: NeuroEntry[]): Layout {
  const groups: Record<string, NeuroEntry[]> = {};
  for (const n of neuros) {
    const ns = n.kind_namespace || 'misc';
    (groups[ns] = groups[ns] || []).push(n);
  }
  const nsNames = Object.keys(groups).sort();
  const R_OUTER = 28;

  const clusterCenter: Record<string, [number, number, number]> = {};
  const clusterRadius: Record<string, number> = {};
  const clusterMembers: Record<string, string[]> = {};
  const nodePos: Record<string, [number, number, number]> = {};

  nsNames.forEach((ns, i) => {
    const c = fibSphere(i, nsNames.length, R_OUTER);
    clusterCenter[ns] = c;
    const members = groups[ns];
    const r = Math.max(2.5, Math.sqrt(members.length) * 1.1);
    clusterRadius[ns] = r;
    clusterMembers[ns] = members.map(m => m.name);
    members.forEach((n, j) => {
      const local = fibSphere(j, members.length, r);
      nodePos[n.name] = [c[0] + local[0], c[1] + local[1], c[2] + local[2]];
    });
  });

  return { nodePos, clusterCenter, clusterRadius, clusterMembers };
}

// ── cluster (L0) bubble ───────────────────────────────────────────────
function ClusterBubble({
  center, radius, name, count, color, fade, onFocus,
}: {
  center: [number, number, number];
  radius: number;
  name: string;
  count: number;
  color: string;
  fade: number; // 0..1 visibility
  onFocus: () => void;
}) {
  return (
    <group position={center}>
      <mesh
        onClick={(e) => { e.stopPropagation(); onFocus(); }}
        visible={fade > 0.01}
      >
        <sphereGeometry args={[radius * 1.25, 32, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.08 * fade}
          depthWrite={false}
        />
      </mesh>
      {fade > 0.01 && (
        <Billboard position={[0, radius * 1.4, 0]}>
          <Html center style={{ pointerEvents: 'none' }}>
            <div style={{
              padding: '4px 10px',
              background: 'rgba(10,10,15,0.85)',
              border: `1px solid ${color}`,
              borderRadius: 6,
              color,
              fontFamily: 'monospace',
              fontSize: 13,
              opacity: fade,
              whiteSpace: 'nowrap',
            }}>
              {name} · <span style={{ color: '#888' }}>{count}</span>
            </div>
          </Html>
        </Billboard>
      )}
    </group>
  );
}

// ── node (L1) ────────────────────────────────────────────────────────
function NeuroNode({
  pos, color, name, description, size, pulse,
  hovered, selected, onClick, onHover,
}: {
  pos: [number, number, number];
  color: string;
  name: string;
  description: string;
  size: number;
  pulse: boolean;
  hovered: boolean;
  selected: boolean;
  onClick: () => void;
  onHover: (h: boolean) => void;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((_, dt) => {
    if (!ref.current) return;
    const s = hovered ? 1.35 : selected ? 1.2 : 1.0;
    ref.current.scale.lerp(new THREE.Vector3(s, s, s), Math.min(1, dt * 10));
    if (pulse) ref.current.rotation.y += dt * 0.4;
  });
  return (
    <mesh
      ref={ref}
      position={pos}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      onPointerOver={(e) => { e.stopPropagation(); onHover(true); }}
      onPointerOut={() => onHover(false)}
    >
      <sphereGeometry args={[size, 20, 20]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={selected ? 0.9 : hovered ? 0.6 : 0.25}
        roughness={0.35}
      />
    </mesh>
  );
}

// ── edge (simple line) ───────────────────────────────────────────────
function Edge({ from, to, color, opacity }: {
  from: [number, number, number];
  to:   [number, number, number];
  color: string;
  opacity: number;
}) {
  const pts = useMemo(
    () => [new THREE.Vector3(...from), new THREE.Vector3(...to)],
    [from, to],
  );
  return (
    <Line points={pts} color={color} transparent opacity={opacity} lineWidth={1} />
  );
}

// ── camera-distance sensor for semantic zoom ─────────────────────────
function ZoomSensor({ onDistance }: { onDistance: (d: number) => void }) {
  const { camera } = useThree();
  useFrame(() => {
    onDistance(camera.position.length());
  });
  return null;
}

// ── main component ───────────────────────────────────────────────────
export default function Graph3D({ neuros, onSelect }: Props) {
  const layout = useMemo(() => computeLayout(neuros), [neuros]);
  const byName = useMemo(() => new Map(neuros.map(n => [n.name, n])), [neuros]);

  const [hover, setHover] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null); // composite name
  const [camDist, setCamDist] = useState(60);

  // semantic-zoom fade: cluster bubbles visible when far, nodes when close
  const clusterFade = Math.min(1, Math.max(0, (camDist - 40) / 30));
  const nodeOpacity = Math.min(1, Math.max(0.15, (90 - camDist) / 60));

  // edges: only those where both endpoints are in `neuros`
  const edges = useMemo(() => {
    const out: { from: string; to: string; kind: 'uses' | 'child' }[] = [];
    for (const n of neuros) {
      for (const u of n.uses || [])
        if (byName.has(u)) out.push({ from: n.name, to: u, kind: 'uses' });
      for (const c of n.children || [])
        if (byName.has(c)) out.push({ from: n.name, to: c, kind: 'child' });
    }
    return out;
  }, [neuros, byName]);

  // expanded composite: lay its children out locally around it
  const expandedPositions = useMemo(() => {
    if (!expanded) return {} as Record<string, [number, number, number]>;
    const parent = byName.get(expanded);
    if (!parent || !parent.children?.length) return {};
    const center = layout.nodePos[expanded];
    if (!center) return {};
    const out: Record<string, [number, number, number]> = {};
    parent.children.forEach((c, i) => {
      const local = fibSphere(i, parent.children.length, 3);
      out[c] = [center[0] + local[0], center[1] + local[1], center[2] + local[2]];
    });
    return out;
  }, [expanded, byName, layout.nodePos]);

  const posOf = (name: string): [number, number, number] | undefined =>
    expandedPositions[name] || layout.nodePos[name];

  return (
    <Canvas
      camera={{ position: [0, 0, 60], fov: 55 }}
      style={{ background: 'radial-gradient(ellipse at center, #0a0a15 0%, #000 90%)' }}
      onPointerMissed={() => setExpanded(null)}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[40, 40, 40]} intensity={1.2} />
      <pointLight position={[-40, -40, -40]} intensity={0.6} color="#a78bfa" />

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        rotateSpeed={0.55}
        zoomSpeed={0.9}
        panSpeed={0.8}
        minDistance={8}
        maxDistance={160}
      />

      <ZoomSensor onDistance={setCamDist} />

      {/* cluster bubbles — semantic-zoom out */}
      {Object.keys(layout.clusterCenter).map(ns => (
        <ClusterBubble
          key={ns}
          center={layout.clusterCenter[ns]}
          radius={layout.clusterRadius[ns]}
          name={ns}
          count={layout.clusterMembers[ns].length}
          color={colorFor(ns)}
          fade={clusterFade}
          onFocus={() => { /* could auto-dolly here in a later pass */ }}
        />
      ))}

      {/* edges */}
      {edges.map((e, i) => {
        const a = posOf(e.from), b = posOf(e.to);
        if (!a || !b) return null;
        const base = e.kind === 'child' ? '#a78bfa' : '#3a4050';
        return (
          <Edge
            key={i}
            from={a}
            to={b}
            color={base}
            opacity={nodeOpacity * (e.kind === 'child' ? 0.55 : 0.3)}
          />
        );
      })}

      {/* nodes */}
      {neuros.map(n => {
        const pos = posOf(n.name);
        if (!pos) return null;
        const color = n.color || colorFor(n.kind_namespace);
        const hasChildren = (n.children?.length || 0) > 0;
        const size = hasChildren ? 0.85 : 0.55;
        return (
          <NeuroNode
            key={n.name}
            pos={pos}
            color={color}
            name={n.name}
            description={n.description}
            size={size}
            pulse={hasChildren}
            hovered={hover === n.name}
            selected={expanded === n.name}
            onClick={() => {
              if (hasChildren && expanded !== n.name) setExpanded(n.name);
              else onSelect(n.name);
            }}
            onHover={(h) => setHover(h ? n.name : null)}
          />
        );
      })}

      {/* hover tooltip */}
      {hover && layout.nodePos[hover] && (
        <Html position={posOf(hover)!} center style={{ pointerEvents: 'none' }}>
          <div style={{
            padding: '5px 9px',
            background: 'rgba(10,10,15,0.92)',
            border: '1px solid #333',
            borderRadius: 5,
            color: '#eee',
            fontFamily: 'monospace',
            fontSize: 11,
            whiteSpace: 'nowrap',
            transform: 'translateY(-28px)',
          }}>
            {hover}
            {byName.get(hover)?.children?.length
              ? <span style={{ color: '#a78bfa' }}> · click to expand</span>
              : null}
          </div>
        </Html>
      )}
    </Canvas>
  );
}
