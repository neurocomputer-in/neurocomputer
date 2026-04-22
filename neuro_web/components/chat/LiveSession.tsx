'use client';
import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { PhoneOff, Mic, MicOff, Terminal, Minimize2 } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import { TERMINAL_LIVE_COL_PX } from '@/store/uiSlice';

export function LiveSession({ onClose, onEndCall }: { onClose: () => void; onEndCall: () => void }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const { isMuted, toggleMute } = useVoiceCall();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const activeTab = useAppSelector(s =>
    s.conversations.openTabs.find(t => t.cid === activeTabCid) ?? null
  );
  const isTerminal = activeTab?.type === 'terminal';
  const sidebarOpen = useAppSelector(s => s.ui.sidebarOpen);
  const sidebarWidth = useAppSelector(s => s.ui.sidebarWidth);
  const effectiveSidebar = sidebarOpen ? sidebarWidth : 0;
  const terminalLeftOffset = effectiveSidebar + TERMINAL_LIVE_COL_PX;
  const messages = useAppSelector(s =>
    activeTabCid ? (s.conversations.tabMessages[activeTabCid] ?? []) : []
  );
  const interimTranscript = useAppSelector(s => s.chat.interimTranscript);
  const activity = useAppSelector(s => s.chat.voiceCall.activity);
  const conversationTitle = activeTab?.title ?? 'Live Call';

  const activeSpeaker: 'user' | 'ai' | 'none' =
    activity === 'listening' ? 'user' :
    activity === 'speaking' || activity === 'thinking' ? 'ai' :
    'none';

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, interimTranscript]);

  if (!mounted) return null;

  const content = (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className={
        isTerminal
          ? "fixed right-0 top-0 bottom-0 z-[9999] flex flex-col bg-[#050914] overflow-hidden font-mono border-l border-sky-500/20"
          : "fixed inset-0 z-[9999] flex flex-col bg-[#050914] overflow-hidden font-mono"
      }
      style={isTerminal ? { left: `${terminalLeftOffset}px` } : undefined}
    >
      <div className="absolute inset-0 pointer-events-none opacity-20"
           style={{
             backgroundImage: 'linear-gradient(rgba(56, 189, 248, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.1) 1px, transparent 1px)',
             backgroundSize: '40px 40px',
             transform: 'perspective(1000px) rotateX(60deg) scale(2) translateY(-100px)'
           }}
      />

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_0%,_#050914_80%)] pointer-events-none z-10" />

      {/* Top HUD: real conversation title + live indicator */}
      <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-start z-20 pointer-events-none">
        <div className="flex flex-col gap-1 max-w-[50%] truncate">
          <span className="text-sky-400 font-mono text-xs tracking-[0.2em] font-semibold truncate">
            {conversationTitle}
          </span>
          <span className="text-white/30 font-mono text-[10px] tracking-widest">
            {activity === 'listening' ? 'LISTENING' :
             activity === 'thinking' ? 'THINKING' :
             activity === 'speaking' ? 'SPEAKING' :
             'CONNECTED'}
          </span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400 font-mono text-[10px] tracking-widest uppercase animate-pulse">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Live
        </div>
      </div>

      {/* 3D Holographic Core — centered horizontally since terminal mode
          has no transcript panel on the left; regular-size orb in both. */}
      <div className={
        isTerminal
          ? "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[250px] h-[250px] md:w-[400px] md:h-[400px] z-10 pointer-events-none perspective-[1200px]"
          : "absolute top-[35%] md:top-1/2 left-1/2 md:left-[70%] -translate-x-1/2 md:-translate-x-0 -translate-y-1/2 w-[250px] h-[250px] md:w-[400px] md:h-[400px] z-10 pointer-events-none perspective-[1200px]"
      }>
        <motion.div
          animate={{ scale: activeSpeaker === 'none' ? 1 : 1.2, opacity: activeSpeaker === 'none' ? 0.3 : 0.8 }}
          transition={{ duration: 0.5 }}
          className={`absolute inset-0 m-auto w-32 h-32 rounded-full blur-[40px] mix-blend-screen transition-colors duration-500 ${activeSpeaker === 'user' ? 'bg-emerald-500' : 'bg-sky-500'}`}
        />
        <motion.div
          animate={{ rotateX: [0, 360], rotateY: [0, 360], rotateZ: [0, 360] }}
          transition={{ duration: activeSpeaker === 'ai' ? 8 : 20, repeat: Infinity, ease: "linear" }}
          className="w-full h-full preserve-3d"
        >
          <div className={`absolute inset-0 border-[2px] rounded-full transition-colors duration-500 ${activeSpeaker === 'user' ? 'border-emerald-500/50' : 'border-sky-500/50'}`} style={{ transform: 'rotateX(45deg)' }} />
          <div className={`absolute inset-0 border-[1px] rounded-full transition-colors duration-500 ${activeSpeaker === 'user' ? 'border-emerald-400/40' : 'border-indigo-500/40'}`} style={{ transform: 'rotateY(45deg)' }} />
          <div className="absolute inset-0 border-[1px] border-fuchsia-500/30 rounded-full" style={{ transform: 'rotateZ(45deg) rotateX(90deg)' }} />
          <motion.div
            animate={{ rotateY: [-360, 0], rotateZ: [360, 0] }}
            transition={{ duration: activeSpeaker === 'ai' ? 4 : 12, repeat: Infinity, ease: "linear" }}
            className="absolute inset-[20%] border-[2px] border-dashed border-sky-400/50 rounded-full"
            style={{ transform: 'rotateX(90deg)' }}
          />
        </motion.div>
      </div>

      {/* Transcript Panel — hidden for terminal tabs since the xterm on
          the left already shows every stdin/stdout line. */}
      {!isTerminal && (
      <div className="absolute top-24 md:top-[15%] left-4 right-4 md:left-12 md:w-[500px] bottom-[20%] flex flex-col z-20 bg-black/40 backdrop-blur-md rounded-xl border border-sky-500/20 shadow-[0_0_30px_rgba(0,0,0,0.8)] overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-sky-500/20 bg-sky-500/5">
          <Terminal className="w-4 h-4 text-sky-400" />
          <span className="font-mono text-[10px] text-sky-400 uppercase tracking-widest">Transcript</span>
          <div className="ml-auto flex gap-1">
            <div className="w-2 h-2 rounded-full bg-rose-500/50" />
            <div className="w-2 h-2 rounded-full bg-amber-500/50" />
            <div className="w-2 h-2 rounded-full bg-emerald-500/50" />
          </div>
        </div>

        <div ref={scrollRef} className="flex flex-col gap-3 p-4 overflow-y-auto no-scrollbar scroll-smooth flex-1 font-mono">
          {messages.length === 0 && !interimTranscript && (
            <p className="text-white/30 text-[12px] italic">Start speaking — your words appear here.</p>
          )}
          <AnimatePresence initial={false}>
            {messages.map(msg => (
              <motion.div
                layout
                key={msg.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col mb-2"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] tracking-widest ${msg.isUser ? 'text-emerald-400' : 'text-sky-400'}`}>
                    {msg.isUser ? 'you:~$' : 'neuro:~$'}
                  </span>
                </div>
                <p className={`text-[13px] md:text-sm leading-relaxed whitespace-pre-wrap ${msg.isUser ? 'text-white' : 'text-white/70'}`}>
                  {msg.text}
                </p>
              </motion.div>
            ))}
            {interimTranscript && (
              <motion.div
                layout
                key="interim"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.7 }}
                className="flex flex-col mb-2"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] tracking-widest text-emerald-400/70">you:~$ (live)</span>
                </div>
                <p className="text-[13px] md:text-sm leading-relaxed italic text-white/60">
                  {interimTranscript}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
          {activity === 'thinking' && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-center gap-2 mt-2 h-6"
            >
              <span className="w-2 h-4 bg-sky-400 animate-pulse" />
              <span className="text-[11px] text-sky-400/70 tracking-widest">thinking...</span>
            </motion.div>
          )}
        </div>
      </div>
      )}

      {/* Bottom Control Dock */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30">
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center gap-0 p-1 bg-[#0a1120]/90 backdrop-blur-2xl border border-sky-500/30 rounded-xl shadow-[0_0_40px_rgba(14,165,233,0.15)] relative overflow-hidden"
        >
          <div className="absolute top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-50" />

          <button
            onClick={toggleMute}
            title={isMuted ? 'Unmute' : 'Mute'}
            className={`flex items-center justify-center w-16 h-12 transition-all border-r border-white/5 ${isMuted ? 'text-amber-500 bg-amber-500/10' : 'text-white/60 hover:text-white hover:bg-white/5'}`}
          >
            {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          <button
            onClick={onClose}
            title="Back to panel"
            className="flex items-center justify-center w-16 h-12 text-white/60 hover:text-sky-400 hover:bg-sky-500/10 transition-all border-r border-white/5"
          >
            <Minimize2 className="w-5 h-5" />
          </button>

          <button
            onClick={onEndCall}
            title="End call"
            className="flex items-center justify-center w-16 h-12 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-all"
          >
            <PhoneOff className="w-5 h-5" />
          </button>
        </motion.div>
      </div>

      <style>{`
        .perspective-\\[1200px\\] { perspective: 1200px; }
        .preserve-3d { transform-style: preserve-3d; }
      `}</style>
    </motion.div>
  );

  return createPortal(content, document.body);
}
