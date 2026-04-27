'use client';
import type { Room } from 'livekit-client';
import type { LetterboxCtx } from './LetterboxContext';

interface Props {
  room: Room | null;
  onLetterboxChange: (lb: LetterboxCtx) => void;
}

export default function DesktopVideoView(_props: Props) {
  return null;
}
