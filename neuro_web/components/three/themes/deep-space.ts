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

  starGeometry = new THREE.BufferGeometry();
  const starPositions = new Float32Array(STAR_COUNT * 3);

  for (let i = 0; i < STAR_COUNT; i++) {
    starPositions[i * 3] = (Math.random() - 0.5) * 40;
    starPositions[i * 3 + 1] = (Math.random() - 0.5) * 40;
    starPositions[i * 3 + 2] = (Math.random() - 0.5) * 40;
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
