'use client';
import { createContext, useContext } from 'react';
import { PaneContext } from '@/components/panes/PaneContext';

export interface WindowBinding {
  windowId: string;
  cid: string;      // active tab's cid — provided by Window.tsx
}

export const WindowContext = createContext<WindowBinding | null>(null);

export function useWindowCid(): string | null {
  return useContext(WindowContext)?.cid ?? null;
}

export function useWindowId(): string | null {
  return useContext(WindowContext)?.windowId ?? null;
}

export function useActiveCid(): string | null {
  const winBinding = useContext(WindowContext);
  if (winBinding) return winBinding.cid;
  const paneBinding = useContext(PaneContext);
  if (paneBinding) return paneBinding.activeCid;
  return null;
}
