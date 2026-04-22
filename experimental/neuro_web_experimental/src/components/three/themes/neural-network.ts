import * as THREE from 'three';
import { ThemeModule } from './types';

const PARTICLE_COUNT = 350;
const CONNECTION_DISTANCE = 3.0;
const FIELD_SIZE = 18;

let particles: THREE.Points;
let lines: THREE.LineSegments;
let positions: Float32Array;
let velocities: Float32Array;
let linePositions: Float32Array;
let lineGeometry: THREE.BufferGeometry;
let particleGeometry: THREE.BufferGeometry;

function setup(scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) {
  camera.position.z = 14;
  scene.fog = new THREE.FogExp2(0x060612, 0.035);
  renderer.setClearColor(0x060612, 1);

  particleGeometry = new THREE.BufferGeometry();
  positions = new Float32Array(PARTICLE_COUNT * 3);
  velocities = new Float32Array(PARTICLE_COUNT * 3);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    positions[i * 3] = (Math.random() - 0.5) * FIELD_SIZE;
    positions[i * 3 + 1] = (Math.random() - 0.5) * FIELD_SIZE;
    positions[i * 3 + 2] = (Math.random() - 0.5) * FIELD_SIZE;
    velocities[i * 3] = (Math.random() - 0.5) * 0.008;
    velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.008;
    velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.004;
  }

  particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const particleMaterial = new THREE.PointsMaterial({
    color: 0x9B6CF6,
    size: 0.12,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  particles = new THREE.Points(particleGeometry, particleMaterial);
  scene.add(particles);

  const maxLines = PARTICLE_COUNT * PARTICLE_COUNT;
  linePositions = new Float32Array(maxLines * 6);
  lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
  lineGeometry.setDrawRange(0, 0);

  const lineMaterial = new THREE.LineBasicMaterial({
    color: 0x8B5CF6,
    transparent: true,
    opacity: 0.25,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  lines = new THREE.LineSegments(lineGeometry, lineMaterial);
  scene.add(lines);
}

function animate(time: number, _delta: number) {
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const i3 = i * 3;
    positions[i3] += velocities[i3];
    positions[i3 + 1] += velocities[i3 + 1];
    positions[i3 + 2] += velocities[i3 + 2];

    for (let j = 0; j < 3; j++) {
      if (positions[i3 + j] > FIELD_SIZE / 2) positions[i3 + j] = -FIELD_SIZE / 2;
      if (positions[i3 + j] < -FIELD_SIZE / 2) positions[i3 + j] = FIELD_SIZE / 2;
    }
  }
  particleGeometry.attributes.position.needsUpdate = true;

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

  particles.rotation.y = time * 0.00005;
  lines.rotation.y = time * 0.00005;
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
