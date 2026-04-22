'use client';

interface Props {
  audioUrl: string;
}

export default function VoicePlayer({ audioUrl }: Props) {
  return (
    <audio
      controls
      src={audioUrl}
      style={{ height: '32px', width: '200px' }}
    />
  );
}
