# Voice Call Panel — Enhanced UI with 3D Reactive Orb

## Overview

Replace the current minimal VoiceCallBar (40px strip with colored dot) with an expanded voice call panel (~160px) featuring a real-time audio-reactive 3D orb, frequency bar visualizer, live transcript display, and call controls. The panel sits at the top of the chat area when a voice call is active; chat messages remain visible below.

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `services/audioAnalyser.ts` | Web Audio API wrapper — creates AudioContext + AnalyserNode, exposes frequency data |
| `components/three/VoiceOrb.tsx` | 80x80 Three.js canvas — displaced icosahedron sphere with custom shaders |
| `components/chat/VoiceCallPanel.tsx` | Main panel component — orchestrates orb, bars, transcript, controls |
| `components/chat/FrequencyBars.tsx` | Full-width 20px canvas — 32 frequency bars with smooth decay |

### Modified Files

| File | Change |
|------|--------|
| `hooks/useVoiceCall.ts` | Expose `micStream` and `agentAudioElement` refs for audio analysis |
| `components/chat/ChatPanel.tsx` | Render `VoiceCallPanel` instead of `VoiceCallBar` when call active |

### Deleted Files

| File | Reason |
|------|--------|
| `components/chat/VoiceCallBar.tsx` | Replaced by VoiceCallPanel |

## Component Design

### 1. VoiceCallPanel.tsx

Top-level panel rendered at the top of the chat area when `voiceCall.active === true`.

**Layout (flex row, ~160px tall):**

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌────────┐  Activity Label          Duration    [Mute] [End]   │
│ │  Voice  │  Interim transcript text scrolling...               │
│ │   Orb   │                                                     │
│ │  80x80  │                                                     │
│ └────────┘                                                      │
│ ▁▂▃▅▇▅▃▂▁▁▂▃▅▇▅▃▁  (frequency bars, full panel width, 20px)   │
└─────────────────────────────────────────────────────────────────┘
```

**Styling:**
- Background: `rgba(8, 8, 22, 0.85)` with `backdrop-filter: blur(12px)`
- Border-bottom: `1px solid rgba(255,255,255,0.06)`
- Border-radius: none (flush with chat area edges)
- Smooth slide-down animation on mount (CSS transition `max-height` 0→160px, 300ms ease)

**Props:** None — reads all state from Redux (`voiceCall.*`, `interimTranscript`).

**Children:**
- `<VoiceOrb />` — left side
- Transcript + controls section — center/right
- `<FrequencyBars />` — bottom strip, full width

**Audio analyser lifecycle:**
- On mount: create `AudioAnalyser` instance
- Connect mic stream (from `useVoiceCall.micStream`) for user audio
- Connect agent audio element (from `useVoiceCall.agentAudioElement`) for agent audio
- Pass analyser ref to VoiceOrb and FrequencyBars
- On unmount: dispose analyser

### 2. VoiceOrb.tsx

Self-contained Three.js canvas (80x80px) rendering an audio-reactive displaced sphere.

**Setup:**
- `WebGLRenderer` with `alpha: true`, `antialias: true`, pixel ratio capped at 2
- `PerspectiveCamera` FOV 45, positioned at z=3
- `IcosahedronGeometry(1, 4)` — smooth enough at 80px

**Custom ShaderMaterial:**

Vertex shader uniforms:
- `uTime: float` — elapsed time for base animation
- `uFrequencyData: float[32]` — FFT bin amplitudes (0.0–1.0)
- `uAmplitude: float` — overall displacement strength (varies by activity)
- `uColor: vec3` — base color (changes per activity state)

Vertex displacement formula:
```glsl
float freq = uFrequencyData[int(mod(vertexIndex, 32.0))];
float displacement = sin(position.x * 3.0 + uTime) * 0.1 + freq * uAmplitude;
vec3 newPos = position + normal * displacement;
```

Fragment shader:
- Fresnel-based rim glow (brighter at edges)
- Base color from `uColor` uniform
- Additive glow layer

**Activity-driven parameters:**

| Activity | Color | Amplitude | Animation |
|----------|-------|-----------|-----------|
| `idle` | `#8B5CF6` (purple) | 0.05 | Slow sine breathing |
| `listening` | `#3B82F6` (blue) | 0.4 | FFT-driven spikes from mic |
| `thinking` | `#F59E0B` (amber) | 0.15 | Smooth noise-based morphing |
| `speaking` | `#8B5CF6` (purple) | 0.3 | FFT-driven pulses from agent audio |

**Glow effect:** Second slightly larger sphere (scale 1.15) behind the main one, same color at low opacity (0.15), additive blending. No post-processing needed — keeps it lightweight.

**Animation loop:**
- `requestAnimationFrame` loop
- Each frame: read `analyser.getFrequencyData()`, normalize to 0–1, set uniforms, render
- Target: runs at display refresh rate, stays under 1ms GPU time at 80x80

### 3. FrequencyBars.tsx

Full-width, 20px tall HTML Canvas element at the bottom of the panel.

**Rendering:**
- 32 bars (one per FFT bin), evenly spaced across canvas width
- Bar width: `canvasWidth / 32 - 2px` gap
- Bar height: `(bin_amplitude / 255) * 20px`
- Smooth decay: `displayValue = max(currentValue, previousDisplayValue * 0.85)` — bars fall smoothly
- Color: vertical gradient from activity color (full opacity at bottom) to transparent at top
- Rounded top caps: `ctx.roundRect` or draw with borderRadius

**When idle/thinking:** Show minimal ambient bars (random values 0–15% height) with gentle flicker.

**Animation:** Shares the same `requestAnimationFrame` loop as VoiceOrb or runs its own — read from same `AudioAnalyser` instance.

### 4. AudioAnalyser Service (`services/audioAnalyser.ts`)

Wraps Web Audio API for real-time frequency analysis.

**Class: `AudioAnalyser`**

```typescript
class AudioAnalyser {
  constructor(fftSize?: number);      // default 64 → 32 bins
  connectStream(stream: MediaStream): void;
  connectElement(el: HTMLAudioElement): void;
  disconnect(): void;
  getFrequencyData(): Uint8Array;     // 32 bins, values 0–255
  getAverageAmplitude(): number;      // 0.0–1.0
  dispose(): void;
}
```

**Internals:**
- Creates `AudioContext` (reuses singleton to avoid browser limits)
- Creates `AnalyserNode` with `fftSize: 64`, `smoothingTimeConstant: 0.8`
- `connectStream()`: creates `MediaStreamSource` → connects to analyser
- `connectElement()`: creates `MediaElementSource` → connects to analyser → connects to `destination` (so audio still plays)
- `disconnect()`: disconnects current source node
- `dispose()`: disconnects + closes AudioContext
- `getFrequencyData()`: fills and returns `Uint8Array(32)` via `analyser.getByteFrequencyData()`
- `getAverageAmplitude()`: returns mean of frequency data normalized to 0–1

**Source switching:**
- VoiceCallPanel switches between mic and agent audio based on `voiceCall.activity`:
  - `listening` → `connectStream(micStream)`
  - `speaking` → `connectElement(agentAudioElement)`
  - `idle`/`thinking` → `disconnect()` (orb shows ambient animation)

### 5. useVoiceCall.ts Modifications

Expose two new refs so VoiceCallPanel can access the raw audio sources:

```typescript
// Add to hook return value:
micStreamRef: RefObject<MediaStream | null>
agentAudioRef: RefObject<HTMLAudioElement | null>
```

- `micStreamRef`: set when local mic track is published (already have the stream from `getUserMedia`)
- `agentAudioRef`: set when remote agent audio track is attached to DOM (already create an `<audio>` element)

No changes to call lifecycle — just exposing existing objects.

### 6. ChatPanel.tsx Integration

Replace `VoiceCallBar` import with `VoiceCallPanel`:

```tsx
// Before chat messages:
{voiceCallActive && <VoiceCallPanel />}
```

The panel slides down (CSS transition) when call starts, slides up when call ends.

## Data Flow

```
Microphone Stream ──→ AudioAnalyser ──→ getFrequencyData()
                                              │
Agent Audio Element ──→ (switched in) ───────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ VoiceOrb shader  │ ← reads FFT every frame
                                    │ FrequencyBars    │ ← reads FFT every frame
                                    └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ voiceCall.activity│ ← drives color/amplitude
                                    │ interimTranscript │ ← drives text display
                                    └─────────────────┘
```

## Performance Budget

- VoiceOrb canvas: 80x80px, single sphere + glow sphere, no post-processing → <0.5ms GPU
- FrequencyBars canvas: 2D context, 32 rects → <0.1ms
- AudioAnalyser: `getByteFrequencyData` is near-zero cost
- Total overhead during call: <1ms per frame
- Three.js background continues running independently (separate canvas)

## Edge Cases

- **No microphone permission**: VoiceOrb shows idle animation, bars show flat. Call still works via LiveKit (permission handled in useVoiceCall already).
- **AudioContext suspended**: Call `audioContext.resume()` on first user interaction (click on call button serves as gesture).
- **Agent audio not yet connected**: Show idle/thinking animation until first agent audio track arrives.
- **Call ends mid-animation**: Dispose analyser, cancel animation frame, panel slides up with 300ms transition.
- **Theme interaction**: VoiceOrb is independent of ThreeBackground — separate canvas, separate renderer. No conflict.
