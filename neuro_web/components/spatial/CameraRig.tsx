'use client';
import { useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Props {
  target: THREE.Vector3 | null;
  controlsRef: React.RefObject<any>;
}

export default function CameraRig({ target, controlsRef }: Props) {
  const { camera } = useThree();
  const savedPose = useRef<{ pos: THREE.Vector3; tgt: THREE.Vector3 } | null>(null);
  const desiredPos = useRef<THREE.Vector3 | null>(null);
  const desiredTarget = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    const ctrl = controlsRef.current;
    if (target) {
      if (!savedPose.current) {
        savedPose.current = {
          pos: camera.position.clone(),
          tgt: ctrl ? ctrl.target.clone() : new THREE.Vector3(),
        };
      }
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
