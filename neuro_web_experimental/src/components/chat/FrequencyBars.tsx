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

      const data = analyser?.getFrequencyData();
      const display = displayValues.current;
      const barWidth = (w - BAR_GAP * (BAR_COUNT - 1)) / BAR_COUNT;
      const color = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;

      for (let i = 0; i < BAR_COUNT; i++) {
        let target: number;
        if (data && data.length > i && (activity === 'listening' || activity === 'speaking')) {
          target = (data[i] / 255) * h;
        } else {
          target = (Math.random() * 0.12 + 0.02) * h;
        }

        if (target > display[i]) {
          display[i] += (target - display[i]) * 0.6;
        } else {
          display[i] *= 0.88;
        }

        const barH = Math.max(display[i], 1);
        const x = i * (barWidth + BAR_GAP);

        const grad = ctx.createLinearGradient(0, h, 0, h - barH);
        grad.addColorStop(0, color);
        grad.addColorStop(1, color + '00');

        ctx.fillStyle = grad;
        ctx.beginPath();
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
