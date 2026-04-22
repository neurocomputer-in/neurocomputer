import * as THREE from 'three';
import { ThemeModule } from './types';

const COLUMN_COUNT = 60;
const CHARS_PER_COLUMN = 25;

let rainGroup: THREE.Group;
let columns: { mesh: THREE.InstancedMesh; speeds: number[]; offsets: number[] }[] = [];
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

      dummy.position.y -= col.speeds[i] * 0.008;

      if (dummy.position.y < -CHARS_PER_COLUMN * 0.15) {
        dummy.position.y = CHARS_PER_COLUMN * 0.15;
      }

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
