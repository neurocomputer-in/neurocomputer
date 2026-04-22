'use client';
import { createContext, useContext } from 'react';

export interface PaneBinding {
  paneId: string;
  activeCid: string | null;
}

export const PaneContext = createContext<PaneBinding | null>(null);

/**
 * Returns the pane-scoped active cid when the component is rendered
 * inside a PaneFrame. Returns null outside a PaneContext so the caller
 * can fall back to reading `state.conversations.activeTabCid` — which
 * preserves the legacy single-pane behaviour for components that
 * happen to render outside a PaneFrame (e.g. modal dialogs).
 */
export function usePaneCid(): string | null {
  const binding = useContext(PaneContext);
  return binding?.activeCid ?? null;
}

export function usePaneId(): string | null {
  return useContext(PaneContext)?.paneId ?? null;
}
