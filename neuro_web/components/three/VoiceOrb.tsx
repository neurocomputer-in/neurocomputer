'use client';
import { useEffect, useRef } from 'react';
import { AudioAnalyser } from '@/services/audioAnalyser';

const ACTIVITY_COLORS: Record<string, [number, number, number]> = {
  idle:      [0.545, 0.361, 0.965],
  listening: [0.231, 0.510, 0.965],
  thinking:  [0.961, 0.620, 0.043],
  speaking:  [0.545, 0.361, 0.965],
};

const ACTIVITY_AMPLITUDE: Record<string, number> = {
  idle: 0.05,
  listening: 0.4,
  thinking: 0.15,
  speaking: 0.3,
};

const VERTEX_SHADER = `
  uniform float uTime;
  uniform float uAmplitude;
  uniform float uFreqData[32];
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vNormal = normal;
    vPosition = position;

    float angle = atan(position.y, position.x) * 0.5 + 0.5;
    int bin = int(angle * 31.0);
    float freq = uFreqData[bin] / 255.0;

    float breathe = sin(uTime * 1.5) * 0.02;
    float displacement = freq * uAmplitude + breathe;

    vec3 newPos = position + normal * displacement;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  uniform vec3 uColor;
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vec3 viewDir = normalize(cameraPosition - vPosition);
    float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 2.5);

    vec3 color = uColor * (0.4 + fresnel * 1.2);

    float pulse = sin(uTime * 2.0) * 0.05 + 1.0;
    color *= pulse;

    gl_FragColor = vec4(color, 0.85 + fresnel * 0.15);
  }
`;

interface Props {
  activity: string;
  analyser: AudioAnalyser | null;
  size?: number;
}

export default function VoiceOrb({ activity, analyser, size = 80 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;
    let animationId: number;

    (async () => {
      const THREE = await import('three');
      if (cancelled) return;

      const container = containerRef.current!;
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(size, size);
      renderer.setClearColor(0x000000, 0);
      container.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
      camera.position.z = 3;

      const geometry = new THREE.IcosahedronGeometry(1, 4);
      const freqArray = new Float32Array(32);
      const material = new THREE.ShaderMaterial({
        vertexShader: VERTEX_SHADER,
        fragmentShader: FRAGMENT_SHADER,
        uniforms: {
          uTime: { value: 0 },
          uAmplitude: { value: 0.05 },
          uFreqData: { value: freqArray },
          uColor: { value: new THREE.Vector3(...ACTIVITY_COLORS.idle) },
        },
        transparent: true,
        depthWrite: false,
      });
      const orb = new THREE.Mesh(geometry, material);
      scene.add(orb);

      const glowGeometry = new THREE.IcosahedronGeometry(1.15, 3);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(...ACTIVITY_COLORS.idle),
        transparent: true,
        opacity: 0.12,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      scene.add(glow);

      const startTime = performance.now();

      const loop = () => {
        if (cancelled) return;
        animationId = requestAnimationFrame(loop);

        const elapsed = (performance.now() - startTime) / 1000;
        material.uniforms.uTime.value = elapsed;

        if (analyser) {
          const data = analyser.getFrequencyData();
          for (let i = 0; i < 32 && i < data.length; i++) {
            freqArray[i] = data[i];
          }
          material.uniforms.uFreqData.value = freqArray;
        }

        const targetColor = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;
        const targetAmp = ACTIVITY_AMPLITUDE[activity] || 0.05;
        const c = material.uniforms.uColor.value as { x: number; y: number; z: number };
        c.x += (targetColor[0] - c.x) * 0.05;
        c.y += (targetColor[1] - c.y) * 0.05;
        c.z += (targetColor[2] - c.z) * 0.05;
        material.uniforms.uAmplitude.value +=
          (targetAmp - material.uniforms.uAmplitude.value) * 0.08;

        (glowMaterial.color as { setRGB: (r: number, g: number, b: number) => void }).setRGB(c.x, c.y, c.z);

        orb.rotation.y = elapsed * 0.3;
        orb.rotation.x = Math.sin(elapsed * 0.2) * 0.1;
        glow.rotation.y = elapsed * 0.2;

        renderer.render(scene, camera);
      };
      animationId = requestAnimationFrame(loop);

      (container as any).__orbCleanup = () => {
        cancelAnimationFrame(animationId);
        geometry.dispose();
        material.dispose();
        glowGeometry.dispose();
        glowMaterial.dispose();
        renderer.dispose();
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
      };
    })();

    return () => {
      cancelled = true;
      const cleanup = (containerRef.current as any)?.__orbCleanup;
      if (cleanup) cleanup();
    };
  }, [size]);

  return (
    <div
      ref={containerRef}
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: '50%',
        overflow: 'hidden',
      }}
    />
  );
}
