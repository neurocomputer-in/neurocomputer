import {
  Room, RoomEvent, DataPacket_Kind, RemoteParticipant,
  ConnectionState, RoomOptions, LocalAudioTrack,
  createLocalAudioTrack, Track, RemoteTrack, RemoteTrackPublication,
} from 'livekit-client';
import { apiGetChatToken } from './api';

export type DataMessageHandler = (text: string, topic: string) => void;

class LiveKitService {
  private room: Room | null = null;
  private currentCid: string | null = null;
  private messageHandler: DataMessageHandler | null = null;
  private stateHandler: ((state: ConnectionState) => void) | null = null;
  private connecting: boolean = false;
  private suppressStateEvents: boolean = false;

  // Voice call state
  private localAudioTrack: LocalAudioTrack | null = null;
  private remoteAudioHandler: ((track: MediaStreamTrack) => void) | null = null;

  onMessage(handler: DataMessageHandler) {
    this.messageHandler = handler;
  }

  onStateChange(handler: (state: ConnectionState) => void) {
    this.stateHandler = handler;
  }

  async connect(cid: string): Promise<void> {
    if (this.currentCid === cid && this.room?.state === ConnectionState.Connected) return;
    if (this.connecting) {
      console.log('[LK] already connecting, skipping duplicate');
      return;
    }
    this.connecting = true;

    this.suppressStateEvents = true;
    await this.disconnect();
    this.suppressStateEvents = false;

    this.currentCid = cid;

    const { token, url: rawUrl } = await apiGetChatToken(cid);

    let url = rawUrl;
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.startsWith('ws://')) {
      const isIp = /^ws:\/\/\d+\.\d+\.\d+\.\d+/.test(url);
      if (isIp) {
        console.warn(
          '[LiveKit] Remote LiveKit server (%s) does not support WSS. ' +
          'Voice/realtime features disabled when accessed over HTTPS. ' +
          'Set up a WSS-enabled LiveKit or access via HTTP to use voice.',
          url
        );
        this.connecting = false;
        throw new Error('LiveKit WSS unavailable');
      }
      url = 'wss://' + url.slice(5);
    }

    const options: RoomOptions = {
      adaptiveStream: false,
      dynacast: false,
    };

    this.room = new Room(options);

    this.room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      if (!this.suppressStateEvents) {
        this.stateHandler?.(state);
      }
    });

    this.room.on(
      RoomEvent.DataReceived,
      (payload: Uint8Array, participant?: RemoteParticipant, _kind?: DataPacket_Kind, topic?: string) => {
        try {
          const text = new TextDecoder().decode(payload);
          this.messageHandler?.(text, topic ?? 'agent_response');
        } catch (e) {
          console.error('Failed to decode DataChannel message', e);
        }
      }
    );

    // Handle remote audio tracks (agent's TTS audio during voice calls)
    this.room.on(
      RoomEvent.TrackSubscribed,
      (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          console.log('[LK] Remote audio track subscribed');
          const audioElement = track.attach();
          document.body.appendChild(audioElement);
          this.remoteAudioHandler?.(track.mediaStreamTrack);
        }
      }
    );

    this.room.on(
      RoomEvent.TrackUnsubscribed,
      (track: RemoteTrack) => {
        if (track.kind === Track.Kind.Audio) {
          console.log('[LK] Remote audio track unsubscribed');
          track.detach().forEach(el => el.remove());
        }
      }
    );

    try {
      await this.room.connect(url, token);
    } catch (err) {
      console.error('[LK] room.connect() FAILED:', err);
      throw err;
    } finally {
      this.connecting = false;
    }
  }

  // ---- Voice Call Audio Methods ----

  async enableAudio(): Promise<void> {
    if (!this.room) throw new Error('Not connected to a room');
    if (this.localAudioTrack) return;

    this.localAudioTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    });
    await this.room.localParticipant.publishTrack(this.localAudioTrack);
    console.log('[LK] Local audio track published');
  }

  async disableAudio(): Promise<void> {
    if (this.localAudioTrack && this.room) {
      await this.room.localParticipant.unpublishTrack(this.localAudioTrack);
      this.localAudioTrack.stop();
      this.localAudioTrack = null;
      console.log('[LK] Local audio track unpublished');
    }
  }

  setMuted(muted: boolean): void {
    if (this.localAudioTrack) {
      if (muted) this.localAudioTrack.mute();
      else this.localAudioTrack.unmute();
    }
  }

  isAudioEnabled(): boolean {
    return this.localAudioTrack !== null;
  }

  onRemoteAudio(handler: (track: MediaStreamTrack) => void) {
    this.remoteAudioHandler = handler;
  }

  getRoom(): Room | null {
    return this.room;
  }

  // ---- Existing Methods ----

  async disconnect(): Promise<void> {
    await this.disableAudio();
    if (this.room) {
      await this.room.disconnect();
      this.room = null;
    }
    this.currentCid = null;
  }

  getState(): ConnectionState {
    return this.room?.state ?? ConnectionState.Disconnected;
  }
}

export const livekitService = new LiveKitService();
