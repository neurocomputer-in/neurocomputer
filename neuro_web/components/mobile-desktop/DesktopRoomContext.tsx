'use client';
import { createContext, useContext } from 'react';
import type { Room } from 'livekit-client';

export interface DesktopRoomCtx {
  room: Room | null;
  sendControl: (payload: object) => void;
}

export const DesktopRoomContext = createContext<DesktopRoomCtx>({
  room: null,
  sendControl: () => {},
});

export function useDesktopRoom() {
  return useContext(DesktopRoomContext);
}
