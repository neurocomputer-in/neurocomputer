import * as THREE from 'three';

export interface ThemeConfig {
  name: string;
  label: string;
  description: string;
}

export interface ThemeModule {
  config: ThemeConfig;
  setup: (scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) => void;
  animate: (time: number, delta: number) => void;
  cleanup: () => void;
  onResize?: (width: number, height: number) => void;
}

export const THEME_IDS = ['neural-network', 'deep-space', 'digital-rain', 'minimal-dark'] as const;
export type ThemeId = typeof THEME_IDS[number];
