import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { PhoneOff, Mic, MicOff, Terminal, Activity, Zap, Command, ChevronRight } from 'lucide-react';

interface TranscriptItem {
  id: string;
  role: 'user' | 'ai';
  text: string;
}

export function LiveSession({ onClose }: { onClose: () => void }) {
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([
    { id: 'init', role: 'ai', text: '> SYSTEM BOOT SEQUENCE INITIATED...' },
    { id: 'init2', role: 'ai', text: '> ESTABLISHING QUANTUM UPLINK... OK' }
  ]);
  const [activeSpeaker, setActiveSpeaker] = useState<'user' | 'ai' | 'none'>('none');
  
  // Terminal State
  const [inputValue, setInputValue] = useState('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  // Handle fake AI responses to commands
  const generateAIResponse = (cmd: string) => {
    setActiveSpeaker('ai');
    setTimeout(() => {
      let resp = "";
      const lcmd = cmd.toLowerCase();
      if (lcmd.includes("scan")) resp = "Scanning perimeter... No hostile signatures found.";
      else if (lcmd.includes("status")) resp = "System operational. Core temperature 42C.";
      else if (lcmd.includes("help")) resp = "Available commands: SCAN, STATUS, CLEAR, HELP.";
      else if (lcmd.includes("clear")) {
        setTranscript([]);
        setActiveSpeaker('none');
        return;
      }
      else resp = `Command unrecognized: [${cmd}]. Please refer to manual.`;
      
      setTranscript(prev => [...prev, { id: Date.now().toString(), role: 'ai', text: resp }]);
      setActiveSpeaker('none');
    }, 800 + Math.random() * 1000);
  };

  const handleCommandSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const cmd = inputValue.trim();
    
    // Add to history
    setCommandHistory(prev => [...prev, cmd]);
    setHistoryIndex(-1);
    
    // Add user message to transcript
    setTranscript(prev => [...prev, { id: Date.now().toString(), role: 'user', text: cmd }]);
    setInputValue('');
    setActiveSpeaker('user');
    
    // Trigger AI
    generateAIResponse(cmd);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIdx = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIdx);
        // commandHistory is oldest-first. We want ArrowUp to go backwards from newest.
        setInputValue(commandHistory[commandHistory.length - 1 - newIdx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIdx = historyIndex - 1;
        setHistoryIndex(newIdx);
        setInputValue(commandHistory[commandHistory.length - 1 - newIdx]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInputValue('');
      }
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="absolute inset-0 z-50 flex flex-col bg-[#050914] overflow-hidden font-mono"
    >
      {/* High-Tech Background Grid */}
      <div className="absolute inset-0 pointer-events-none opacity-20" 
           style={{ 
             backgroundImage: 'linear-gradient(rgba(56, 189, 248, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.1) 1px, transparent 1px)',
             backgroundSize: '40px 40px',
             transform: 'perspective(1000px) rotateX(60deg) scale(2) translateY(-100px)'
           }} 
      />

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_0%,_#050914_80%)] pointer-events-none z-10" />

      {/* Top HUD */}
      <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-start z-20 pointer-events-none">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-sky-400" />
            <span className="text-sky-400 font-mono text-xs tracking-[0.3em] font-bold shadow-[0_0_10px_rgba(56,189,248,0.5)]">NEURO_LINK_V4</span>
          </div>
          <span className="text-white/30 font-mono text-[10px] tracking-widest pl-6">SYS.OP.NORMAL</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400 font-mono text-[10px] tracking-widest uppercase animate-pulse">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          Live REC
        </div>
      </div>

      {/* 3D Holographic Gyroscope Core */}
      <div className="absolute top-[35%] md:top-1/2 left-1/2 md:left-[70%] -translate-x-1/2 md:-translate-x-0 -translate-y-1/2 w-[250px] h-[250px] md:w-[400px] md:h-[400px] z-10 pointer-events-none perspective-[1200px]">
        {/* Core Light */}
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
          {/* Ring 1 */}
          <div className={`absolute inset-0 border-[2px] rounded-full transition-colors duration-500 ${activeSpeaker === 'user' ? 'border-emerald-500/50' : 'border-sky-500/50'}`} style={{ transform: 'rotateX(45deg)' }} />
          {/* Ring 2 */}
          <div className={`absolute inset-0 border-[1px] rounded-full transition-colors duration-500 ${activeSpeaker === 'user' ? 'border-emerald-400/40' : 'border-indigo-500/40'}`} style={{ transform: 'rotateY(45deg)' }} />
          {/* Ring 3 */}
          <div className="absolute inset-0 border-[1px] border-fuchsia-500/30 rounded-full" style={{ transform: 'rotateZ(45deg) rotateX(90deg)' }} />
          
          {/* Inner Geometries */}
          <motion.div 
            animate={{ rotateY: [-360, 0], rotateZ: [360, 0] }}
            transition={{ duration: activeSpeaker === 'ai' ? 4 : 12, repeat: Infinity, ease: "linear" }}
            className="absolute inset-[20%] border-[2px] border-dashed border-sky-400/50 rounded-full"
            style={{ transform: 'rotateX(90deg)' }}
          />
        </motion.div>
      </div>

      {/* Terminal HUD Transcript & Input */}
      <div className="absolute top-24 md:top-[15%] left-4 right-4 md:left-12 md:w-[500px] bottom-[20%] flex flex-col z-20 bg-black/40 backdrop-blur-md rounded-xl border border-sky-500/20 shadow-[0_0_30px_rgba(0,0,0,0.8)] overflow-hidden">
        
        {/* Terminal Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-sky-500/20 bg-sky-500/5">
          <Terminal className="w-4 h-4 text-sky-400" />
          <span className="font-mono text-[10px] text-sky-400 uppercase tracking-widest shadow-sm">Command Matrix</span>
          <div className="ml-auto flex gap-1">
            <div className="w-2 h-2 rounded-full bg-rose-500/50" />
            <div className="w-2 h-2 rounded-full bg-amber-500/50" />
            <div className="w-2 h-2 rounded-full bg-emerald-500/50" />
          </div>
        </div>

        {/* Log Area */}
        <div ref={scrollRef} className="flex flex-col gap-3 p-4 overflow-y-auto no-scrollbar scroll-smooth flex-1 font-mono">
          <AnimatePresence>
            {transcript.map((msg, i) => (
              <motion.div 
                layout
                key={msg.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col mb-2"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] tracking-widest ${msg.role === 'user' ? 'text-emerald-400' : 'text-sky-400'}`}>
                    {msg.role === 'user' ? 'root@user:~$' : 'neuro@sys:~$'}
                  </span>
                </div>
                <p className={`text-[13px] md:text-sm leading-relaxed ${msg.role === 'ai' ? 'text-white/70' : 'text-white'}`}>
                  {msg.text}
                </p>
              </motion.div>
            ))}
          </AnimatePresence>
          {activeSpeaker === 'ai' && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} 
              className="flex items-center gap-2 mt-2 h-6"
            >
              <span className="w-2 h-4 bg-sky-400 animate-pulse" />
            </motion.div>
          )}
        </div>

        {/* Active Input Area */}
        <form onSubmit={handleCommandSubmit} className="mt-auto px-4 py-3 border-t border-sky-500/20 bg-black/60 flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-emerald-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-emerald-400 font-mono text-[13px] placeholder:text-white/20 focus:ring-0"
            placeholder="Enter command... (Use ↑/↓ for history)"
            autoComplete="off"
            spellCheck="false"
          />
          <Command className="w-4 h-4 text-white/20 shrink-0" />
        </form>
      </div>

      {/* Bottom Control Dock */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30">
        <motion.div 
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center gap-0 p-1 bg-[#0a1120]/90 backdrop-blur-2xl border border-sky-500/30 rounded-xl shadow-[0_0_40px_rgba(14,165,233,0.15)] relative overflow-hidden"
        >
          <div className="absolute top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-50" />
          
          <button onClick={() => setIsMuted(!isMuted)} className={`flex items-center justify-center w-16 h-12 transition-all border-r border-white/5 ${isMuted ? 'text-amber-500 bg-amber-500/10' : 'text-white/60 hover:text-white hover:bg-white/5'}`}>
            {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
          
          <button onClick={() => inputRef.current?.focus()} className="flex items-center justify-center w-16 h-12 text-white/60 hover:text-sky-400 hover:bg-sky-500/10 transition-all border-r border-white/5">
            <Terminal className="w-5 h-5" />
          </button>

          <button onClick={onClose} className="flex items-center justify-center w-16 h-12 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-all">
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
}
