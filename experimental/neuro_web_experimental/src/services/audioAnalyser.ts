/**
 * Wraps Web Audio API for real-time frequency analysis.
 * Connects to microphone streams or audio elements and exposes FFT data.
 */
export class AudioAnalyser {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private source: MediaStreamAudioSourceNode | MediaElementAudioSourceNode | null = null;
  private dataArray: Uint8Array<ArrayBuffer>;
  private readonly fftSize: number;

  constructor(fftSize = 64) {
    this.fftSize = fftSize;
    this.dataArray = new Uint8Array(new ArrayBuffer(fftSize / 2));
  }

  private ensureContext() {
    if (!this.ctx) {
      this.ctx = new AudioContext();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = this.fftSize;
      this.analyser.smoothingTimeConstant = 0.8;
      this.dataArray = new Uint8Array(new ArrayBuffer(this.analyser.frequencyBinCount));
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  connectStream(stream: MediaStream) {
    this.ensureContext();
    this.disconnect();
    this.source = this.ctx!.createMediaStreamSource(stream);
    this.source.connect(this.analyser!);
  }

  connectElement(el: HTMLAudioElement) {
    this.ensureContext();
    this.disconnect();
    try {
      this.source = this.ctx!.createMediaElementSource(el);
      this.source.connect(this.analyser!);
      this.analyser!.connect(this.ctx!.destination);
    } catch {
      // Element may already be connected to a different context
    }
  }

  disconnect() {
    try { this.source?.disconnect(); } catch {}
    this.source = null;
  }

  getFrequencyData(): Uint8Array {
    if (this.analyser) {
      this.analyser.getByteFrequencyData(this.dataArray);
    }
    return this.dataArray;
  }

  getAverageAmplitude(): number {
    const data = this.getFrequencyData();
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    return data.length > 0 ? sum / (data.length * 255) : 0;
  }

  get binCount(): number {
    return this.analyser?.frequencyBinCount ?? this.fftSize / 2;
  }

  dispose() {
    this.disconnect();
    try { this.ctx?.close(); } catch {}
    this.ctx = null;
    this.analyser = null;
  }
}
