'use client';
import { createContext, useContext } from 'react';

export interface LetterboxCtx {
  offsetX: number;   // px from left edge to video area start
  offsetY: number;   // px from top edge to video area start
  drawW: number;     // rendered video width in px
  drawH: number;     // rendered video height in px
  containerW: number;
  containerH: number;
}

export const LetterboxContext = createContext<LetterboxCtx>({
  offsetX: 0, offsetY: 0, drawW: 1, drawH: 1, containerW: 1, containerH: 1,
});

export function useLetterbox() {
  return useContext(LetterboxContext);
}

/** Compute FitInside letterbox dimensions. */
export function computeLetterbox(
  containerW: number, containerH: number,
  videoW: number, videoH: number
): { offsetX: number; offsetY: number; drawW: number; drawH: number } {
  if (!videoW || !videoH) return { offsetX: 0, offsetY: 0, drawW: containerW, drawH: containerH };
  const containerAR = containerW / containerH;
  const videoAR = videoW / videoH;
  let drawW: number, drawH: number;
  if (videoAR > containerAR) {
    drawW = containerW;
    drawH = containerW / videoAR;
  } else {
    drawH = containerH;
    drawW = containerH * videoAR;
  }
  return {
    offsetX: (containerW - drawW) / 2,
    offsetY: (containerH - drawH) / 2,
    drawW,
    drawH,
  };
}
