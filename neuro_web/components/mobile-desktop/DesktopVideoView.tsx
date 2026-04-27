'use client';
import { useEffect, useRef } from 'react';
import { Room, RoomEvent, Track, RemoteTrack, RemoteTrackPublication, RemoteParticipant } from 'livekit-client';
import { computeLetterbox, LetterboxCtx } from './LetterboxContext';
import { useAppSelector } from '@/store/hooks';
import { usePinch } from '@use-gesture/react';
import { api } from '@/services/api';

interface Props {
  room: Room | null;
  onLetterboxChange: (lb: LetterboxCtx) => void;
}

const USER_ID = 'desktop-web';

export default function DesktopVideoView({ room, onLetterboxChange }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { serverScreenW, serverScreenH } = useAppSelector(s => s.mobileDesktop);
  const videoSizeRef = useRef({ w: serverScreenW, h: serverScreenH });
  const onLetterboxRef = useRef(onLetterboxChange);
  onLetterboxRef.current = onLetterboxChange;

  function updateLetterbox() {
    const el = containerRef.current;
    if (!el) return;
    const cw = el.offsetWidth;
    const ch = el.offsetHeight;
    const { w, h } = videoSizeRef.current;
    const lb = computeLetterbox(cw, ch, w, h);
    onLetterboxRef.current({ ...lb, containerW: cw, containerH: ch });
  }

  useEffect(() => {
    videoSizeRef.current = { w: serverScreenW, h: serverScreenH };
    updateLetterbox();
  }, [serverScreenW, serverScreenH]);

  useEffect(() => {
    if (!room) return;

    function attachTrack(track: RemoteTrack) {
      if (track.kind !== Track.Kind.Video) return;
      if (!videoRef.current) return;
      track.attach(videoRef.current);
      videoRef.current.onloadedmetadata = () => {
        if (videoRef.current) {
          videoSizeRef.current = {
            w: videoRef.current.videoWidth,
            h: videoRef.current.videoHeight,
          };
          updateLetterbox();
        }
      };
    }

    const onSubscribed = (track: RemoteTrack, _pub: RemoteTrackPublication, _p: RemoteParticipant) => attachTrack(track);
    room.on(RoomEvent.TrackSubscribed, onSubscribed);

    room.remoteParticipants.forEach(p => {
      p.trackPublications.forEach(pub => {
        if (pub.track) attachTrack(pub.track as RemoteTrack);
      });
    });

    return () => { room.off(RoomEvent.TrackSubscribed, onSubscribed); };
  }, [room]);

  useEffect(() => {
    const obs = new ResizeObserver(updateLetterbox);
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  usePinch(({ offset: [scale] }) => {
    const zoom = Math.max(1, Math.min(10, scale));
    api.post('/screen/view', { user_id: USER_ID, zoom, pan_x: 0.5, pan_y: 0.5 }).catch(() => {});
  }, { target: containerRef });

  return (
    <div
      ref={containerRef}
      style={{ position: 'absolute', inset: 0, background: '#000', touchAction: 'none' }}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          objectFit: 'contain',
        }}
      />
    </div>
  );
}
