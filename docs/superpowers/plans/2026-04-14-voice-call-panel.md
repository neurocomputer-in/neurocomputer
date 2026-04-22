# Voice Call Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal VoiceCallBar with an expanded panel featuring a 3D audio-reactive orb, frequency bar visualizer, and live transcript display.

**Architecture:** New `AudioAnalyser` service wraps Web Audio API. New `VoiceOrb` renders a shader-displaced icosahedron in a small Three.js canvas. New `FrequencyBars` renders a 2D canvas bar visualizer. New `VoiceCallPanel` orchestrates all three plus existing transcript/controls. `useVoiceCall` hook exposes mic/agent audio streams for analysis.

**Tech Stack:** Three.js (already installed), Web Audio API (AnalyserNode), GLSL shaders, HTML Canvas 2D

---

### Task 1: AudioAnalyser Service

**Files:**
- Create: `neuro_web/services/audioAnalyser.ts`

- [ ] **Step 1: Create AudioAnalyser class**

Create `neuro_web/services/audioAnalyser.ts`:

```typescript
/**
 * Wraps Web Audio API for real-time frequency analysis.
 * Connects to microphone streams or audio elements and exposes FFT data.
 */
export class AudioAnalyser {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private source: MediaStreamAudioSourceNode | MediaElementAudioSourceNode | null = null;
  private dataArray: Uint8Array;
  private readonly fftSize: number;

  constructor(fftSize = 64) {
    this.fftSize = fftSize;
    this.dataArray = new Uint8Array(fftSize / 2);
  }

  private ensureContext() {
    if (!this.ctx) {
      this.ctx = new AudioContext();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = this.fftSize;
      this.analyser.smoothingTimeConstant = 0.8;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    }
    // Resume if suspended (autoplay policy)
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  /** Connect a microphone MediaStream for analysis. */
  connectStream(stream: MediaStream) {
    this.ensureContext();
    this.disconnect();
    this.source = this.ctx!.createMediaStreamSource(stream);
    this.source.connect(this.analyser!);
  }

  /** Connect an HTMLAudioElement for analysis (audio still plays). */
  connectElement(el: HTMLAudioElement) {
    this.ensureContext();
    this.disconnect();
    // Prevent double-connecting the same element
    try {
      this.source = this.ctx!.createMediaElementSource(el);
      this.source.connect(this.analyser!);
      this.analyser!.connect(this.ctx!.destination);
    } catch {
      // Element may already be connected to a different context
    }
  }

  /** Disconnect current audio source. */
  disconnect() {
    try { this.source?.disconnect(); } catch {}
    this.source = null;
  }

  /** Get raw frequency bin data (0-255 per bin). */
  getFrequencyData(): Uint8Array {
    if (this.analyser) {
      this.analyser.getByteFrequencyData(this.dataArray);
    }
    return this.dataArray;
  }

  /** Get normalized average amplitude (0.0 - 1.0). */
  getAverageAmplitude(): number {
    const data = this.getFrequencyData();
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    return data.length > 0 ? sum / (data.length * 255) : 0;
  }

  /** Get number of frequency bins. */
  get binCount(): number {
    return this.analyser?.frequencyBinCount ?? this.fftSize / 2;
  }

  /** Clean up all resources. */
  dispose() {
    this.disconnect();
    try { this.ctx?.close(); } catch {}
    this.ctx = null;
    this.analyser = null;
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add neuro_web/services/audioAnalyser.ts
git commit -m "feat: add AudioAnalyser service for real-time FFT analysis"
```

---

### Task 2: VoiceOrb Component (3D Reactive Sphere)

**Files:**
- Create: `neuro_web/components/three/VoiceOrb.tsx`

- [ ] **Step 1: Create VoiceOrb with shader-displaced icosahedron**

Create `neuro_web/components/three/VoiceOrb.tsx`:

```tsx
'use client';
import { useEffect, useRef } from 'react';
import { AudioAnalyser } from '@/services/audioAnalyser';

// Activity-driven visual config
const ACTIVITY_COLORS: Record<string, [number, number, number]> = {
  idle:      [0.545, 0.361, 0.965],   // #8B5CF6
  listening: [0.231, 0.510, 0.965],   // #3B82F6
  thinking:  [0.961, 0.620, 0.043],   // #F59E0B
  speaking:  [0.545, 0.361, 0.965],   // #8B5CF6
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

    // Map vertex to a frequency bin based on its angle
    float angle = atan(position.y, position.x) * 0.5 + 0.5;
    int bin = int(angle * 31.0);
    float freq = uFreqData[bin] / 255.0;

    // Combine frequency data with time-based animation
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
    // Fresnel rim glow
    vec3 viewDir = normalize(cameraPosition - vPosition);
    float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 2.5);

    // Base color with fresnel glow
    vec3 color = uColor * (0.4 + fresnel * 1.2);

    // Subtle pulse
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

      // Main orb — displaced icosahedron
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

      // Glow sphere (larger, low opacity, additive)
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

        // Update frequency data from analyser
        if (analyser) {
          const data = analyser.getFrequencyData();
          for (let i = 0; i < 32 && i < data.length; i++) {
            freqArray[i] = data[i];
          }
          material.uniforms.uFreqData.value = freqArray;
        }

        // Smooth color/amplitude transitions
        const targetColor = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;
        const targetAmp = ACTIVITY_AMPLITUDE[activity] || 0.05;
        const c = material.uniforms.uColor.value as THREE.Vector3;
        c.x += (targetColor[0] - c.x) * 0.05;
        c.y += (targetColor[1] - c.y) * 0.05;
        c.z += (targetColor[2] - c.z) * 0.05;
        material.uniforms.uAmplitude.value +=
          (targetAmp - material.uniforms.uAmplitude.value) * 0.08;

        // Update glow color to match
        (glowMaterial.color as THREE.Color).setRGB(c.x, c.y, c.z);

        // Slow rotation
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
  }, [size]); // Only re-init on size change; activity/analyser read in loop

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
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/three/VoiceOrb.tsx
git commit -m "feat: add VoiceOrb — 3D audio-reactive displaced sphere"
```

---

### Task 3: FrequencyBars Component (2D Canvas Visualizer)

**Files:**
- Create: `neuro_web/components/chat/FrequencyBars.tsx`

- [ ] **Step 1: Create FrequencyBars component**

Create `neuro_web/components/chat/FrequencyBars.tsx`:

```tsx
'use client';
import { useEffect, useRef } from 'react';
import { AudioAnalyser } from '@/services/audioAnalyser';

const BAR_COUNT = 32;
const BAR_GAP = 2;

const ACTIVITY_COLORS: Record<string, string> = {
  idle: '#22C55E',
  listening: '#3B82F6',
  thinking: '#F59E0B',
  speaking: '#8B5CF6',
};

interface Props {
  activity: string;
  analyser: AudioAnalyser | null;
  height?: number;
}

export default function FrequencyBars({ activity, analyser, height = 20 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const displayValues = useRef(new Float32Array(BAR_COUNT));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let cancelled = false;

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width * Math.min(window.devicePixelRatio, 2);
        canvas.height = height * Math.min(window.devicePixelRatio, 2);
        canvas.style.width = `${rect.width}px`;
        canvas.style.height = `${height}px`;
      }
    };
    resize();
    window.addEventListener('resize', resize);

    const loop = () => {
      if (cancelled) return;
      animationId = requestAnimationFrame(loop);

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // Get frequency data
      const data = analyser?.getFrequencyData();
      const display = displayValues.current;
      const barWidth = (w - BAR_GAP * (BAR_COUNT - 1)) / BAR_COUNT;
      const color = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;

      for (let i = 0; i < BAR_COUNT; i++) {
        // Current value from analyser (or ambient noise when idle/thinking)
        let target: number;
        if (data && data.length > i && (activity === 'listening' || activity === 'speaking')) {
          target = (data[i] / 255) * h;
        } else {
          // Ambient flicker for idle/thinking
          target = (Math.random() * 0.12 + 0.02) * h;
        }

        // Smooth decay: rise fast, fall slowly
        if (target > display[i]) {
          display[i] += (target - display[i]) * 0.6;
        } else {
          display[i] *= 0.88;
        }

        const barH = Math.max(display[i], 1);
        const x = i * (barWidth + BAR_GAP);

        // Gradient from activity color to transparent
        const grad = ctx.createLinearGradient(0, h, 0, h - barH);
        grad.addColorStop(0, color);
        grad.addColorStop(1, color + '00');

        ctx.fillStyle = grad;
        ctx.beginPath();
        // Rounded top
        const radius = Math.min(barWidth / 2, 2);
        ctx.roundRect(x, h - barH, barWidth, barH, [radius, radius, 0, 0]);
        ctx.fill();
      }
    };
    animationId = requestAnimationFrame(loop);

    return () => {
      cancelled = true;
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, [activity, analyser, height]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: `${height}px`,
        display: 'block',
      }}
    />
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/chat/FrequencyBars.tsx
git commit -m "feat: add FrequencyBars — 2D canvas frequency bar visualizer"
```

---

### Task 4: Expose Audio Streams from useVoiceCall

**Files:**
- Modify: `neuro_web/hooks/useVoiceCall.ts`

- [ ] **Step 1: Add micStream and agentAudio refs to useVoiceCall**

In `neuro_web/hooks/useVoiceCall.ts`, make the following changes:

Add `useRef` to imports:
```typescript
import { useState, useCallback, useRef } from 'react';
```

Add refs inside the hook body (after `const [connecting, setConnecting] = useState(false);`):
```typescript
const micStreamRef = useRef<MediaStream | null>(null);
const agentAudioRef = useRef<HTMLAudioElement | null>(null);
```

In `startCall`, after `await voiceRoom.localParticipant.publishTrack(micTrack);` (line 65), add:
```typescript
// Expose mic stream for audio analysis
micStreamRef.current = micTrack.mediaStream ?? null;
```

In `startCall`, inside the `RoomEvent.TrackSubscribed` handler, after `document.body.appendChild(el);` (line 38), add:
```typescript
agentAudioRef.current = el as HTMLAudioElement;
```

In `endCall`, after `(window as any).__voiceCallMicTrack = null;` (line 90), add:
```typescript
micStreamRef.current = null;
agentAudioRef.current = null;
```

Also in `endCall`, inside the `document.querySelectorAll('#voice-call-audio')` cleanup (line 98), add before `.forEach`:
```typescript
agentAudioRef.current = null;
```

Update the return object to include the new refs:
```typescript
return {
    startCall,
    endCall,
    toggleMute,
    connecting,
    isActive: voiceCall.active,
    isMuted: voiceCall.muted,
    startedAt: voiceCall.startedAt,
    interimTranscript,
    micStreamRef,
    agentAudioRef,
};
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add neuro_web/hooks/useVoiceCall.ts
git commit -m "feat: expose micStream and agentAudio refs from useVoiceCall"
```

---

### Task 5: VoiceCallPanel Component (Orchestrator)

**Files:**
- Create: `neuro_web/components/chat/VoiceCallPanel.tsx`

- [ ] **Step 1: Create VoiceCallPanel that assembles orb + bars + controls**

Create `neuro_web/components/chat/VoiceCallPanel.tsx`:

```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { PhoneOff, MicOff, Mic } from 'lucide-react';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import { useAppSelector } from '@/store/hooks';
import { AudioAnalyser } from '@/services/audioAnalyser';
import dynamic from 'next/dynamic';
import FrequencyBars from './FrequencyBars';

const VoiceOrb = dynamic(() => import('@/components/three/VoiceOrb'), { ssr: false });

function formatDuration(startedAt: string | null): string {
  if (!startedAt) return '0:00';
  const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const ACTIVITY_LABELS: Record<string, string> = {
  idle: 'Voice Call Active',
  listening: 'Listening...',
  thinking: 'Thinking...',
  speaking: 'Speaking...',
};

const ACTIVITY_COLORS: Record<string, string> = {
  idle: '#22C55E',
  listening: '#3B82F6',
  thinking: '#F59E0B',
  speaking: '#8B5CF6',
};

export default function VoiceCallPanel() {
  const {
    isActive, isMuted, startedAt, interimTranscript,
    endCall, toggleMute, micStreamRef, agentAudioRef,
  } = useVoiceCall();
  const activity = useAppSelector(s => s.chat.voiceCall.activity);
  const [duration, setDuration] = useState('0:00');
  const analyserRef = useRef<AudioAnalyser | null>(null);
  const [analyser, setAnalyser] = useState<AudioAnalyser | null>(null);

  // Duration timer
  useEffect(() => {
    if (!isActive || !startedAt) return;
    const interval = setInterval(() => setDuration(formatDuration(startedAt)), 1000);
    return () => clearInterval(interval);
  }, [isActive, startedAt]);

  // AudioAnalyser lifecycle
  useEffect(() => {
    if (!isActive) {
      analyserRef.current?.dispose();
      analyserRef.current = null;
      setAnalyser(null);
      return;
    }
    if (!analyserRef.current) {
      analyserRef.current = new AudioAnalyser(64);
      setAnalyser(analyserRef.current);
    }
    return () => {
      analyserRef.current?.dispose();
      analyserRef.current = null;
      setAnalyser(null);
    };
  }, [isActive]);

  // Switch audio source based on activity
  useEffect(() => {
    const a = analyserRef.current;
    if (!a) return;

    if (activity === 'listening' && micStreamRef.current) {
      a.connectStream(micStreamRef.current);
    } else if (activity === 'speaking' && agentAudioRef.current) {
      a.connectElement(agentAudioRef.current);
    } else {
      a.disconnect();
    }
  }, [activity, micStreamRef, agentAudioRef]);

  if (!isActive) return null;

  const color = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;
  const label = ACTIVITY_LABELS[activity] || ACTIVITY_LABELS.idle;

  return (
    <div
      style={{
        background: 'rgba(8, 8, 22, 0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        overflow: 'hidden',
        animation: 'voicePanelSlideDown 0.3s ease forwards',
      }}
    >
      {/* Main content row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '14px 24px 10px',
          maxWidth: '1024px',
          margin: '0 auto',
          width: '100%',
          boxSizing: 'border-box',
        }}
      >
        {/* 3D Orb */}
        <VoiceOrb activity={activity} analyser={analyser} size={80} />

        {/* Info section */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <span style={{
              fontSize: '13px', fontWeight: 600, color,
              transition: 'color 0.3s',
            }}>
              {label}
            </span>
            <span style={{
              fontSize: '12px', color: '#555', fontFamily: 'monospace',
            }}>
              {duration}
            </span>
          </div>

          {/* Interim transcript */}
          <div style={{
            fontSize: '12px', color: '#777', fontStyle: 'italic',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            minHeight: '18px',
            transition: 'opacity 0.2s',
            opacity: interimTranscript ? 1 : 0.3,
          }}>
            {interimTranscript || 'Waiting for speech...'}
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <button
            onClick={toggleMute}
            style={{
              width: '36px', height: '36px', borderRadius: '50%',
              background: isMuted ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.06)',
              border: isMuted ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(255,255,255,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <MicOff size={15} color="#ef4444" /> : <Mic size={15} color="#aaa" />}
          </button>

          <button
            onClick={endCall}
            style={{
              width: '36px', height: '36px', borderRadius: '50%',
              background: 'rgba(239,68,68,0.2)',
              border: '1px solid rgba(239,68,68,0.35)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.35)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.2)')}
            title="End call"
          >
            <PhoneOff size={15} color="#ef4444" />
          </button>
        </div>
      </div>

      {/* Frequency bars — full width */}
      <div style={{ padding: '0 24px 8px', maxWidth: '1024px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        <FrequencyBars activity={activity} analyser={analyser} height={20} />
      </div>

      <style>{`
        @keyframes voicePanelSlideDown {
          from { max-height: 0; opacity: 0; }
          to { max-height: 200px; opacity: 1; }
        }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/chat/VoiceCallPanel.tsx
git commit -m "feat: add VoiceCallPanel — orchestrates orb, bars, transcript, controls"
```

---

### Task 6: Wire VoiceCallPanel into ChatPanel

**Files:**
- Modify: `neuro_web/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Replace VoiceCallBar with VoiceCallPanel**

In `neuro_web/components/chat/ChatPanel.tsx`:

Change the import (find the line `import VoiceCallBar from './VoiceCallBar';`):
```typescript
// Replace:
import VoiceCallBar from './VoiceCallBar';
// With:
import VoiceCallPanel from './VoiceCallPanel';
```

Change the usage (find `<VoiceCallBar />`):
```tsx
// Replace:
<VoiceCallBar />
// With:
<VoiceCallPanel />
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 3: Test in browser**

Open `http://localhost:3002`, start a voice call. Verify:
- Panel expands with slide-down animation (~160px)
- 3D orb renders on the left, glowing purple
- Frequency bars show at the bottom of the panel
- Activity label and duration display correctly
- Mute and end call buttons work
- Chat messages still visible below the panel
- When activity changes (listening/thinking/speaking), orb color and bars react
- Panel slides away when call ends

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/chat/ChatPanel.tsx
git commit -m "feat: replace VoiceCallBar with VoiceCallPanel in ChatPanel"
```

---

### Task 7: Delete Old VoiceCallBar

**Files:**
- Delete: `neuro_web/components/chat/VoiceCallBar.tsx`

- [ ] **Step 1: Verify VoiceCallBar is not imported anywhere else**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && grep -r "VoiceCallBar" --include="*.ts" --include="*.tsx" .`
Expected: No results (the import was replaced in Task 6)

- [ ] **Step 2: Delete the file**

```bash
rm neuro_web/components/chat/VoiceCallBar.tsx
```

- [ ] **Step 3: Verify build still works**

Run: `cd /home/ubuntu/neurocomputer-dev/neuro_web && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add -A neuro_web/components/chat/VoiceCallBar.tsx
git commit -m "chore: remove old VoiceCallBar (replaced by VoiceCallPanel)"
```
