import React, { useRef, useEffect } from 'react';
import { motion } from 'motion/react';
import { Bot, User, Code2, Sparkles, Copy, FileCode2 } from 'lucide-react';
import { ChatMessage } from '../App';

export function ChatPanel({ messages, isTyping }: { messages: ChatMessage[], isTyping: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col gap-8 relative no-scrollbar scroll-smooth">
      
      <div className="pt-20 pb-12 flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20, scale: 0.8 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          className="relative w-24 h-24 mb-8 flex items-center justify-center pointer-events-none"
        >
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 10, repeat: Infinity, ease: "linear" }} className="absolute inset-0 rounded-full bg-gradient-to-tr from-indigo-500 via-purple-500 to-emerald-400 blur-[8px] opacity-60" />
          <div className="absolute inset-1 bg-[#0a0a0a] rounded-full flex items-center justify-center border border-white/10 shadow-2xl">
            <Sparkles className="w-10 h-10 text-white/90" />
          </div>
        </motion.div>
        <motion.h1 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-4xl md:text-5xl font-display font-medium text-white mb-4 tracking-tight"
        >
          How can I help today?
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-white/40 text-sm md:text-base max-w-md font-mono tracking-wide leading-relaxed"
        >
          Neuro Gen-4 is connected to your workspace. Advanced analysis and code execution mode enabled.
        </motion.p>
      </div>

      <div className="flex flex-col gap-8 max-w-4xl mx-auto w-full pb-32">
        {messages.map((msg, idx) => (
          <MessageBubble key={msg.id} msg={msg} index={idx} />
        ))}
        {isTyping && <ThinkingBubble />}
      </div>
    </div>
  );
}

function ThinkingBubble() {
  return (
    <motion.div layout initial={{ opacity: 0, y: 20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} className="flex w-full gap-5 group">
      <div className="shrink-0 flex flex-col items-center">
         <div className="w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg relative">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 8, repeat: Infinity, ease: "linear" }} className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-indigo-500 via-emerald-400 to-purple-500 blur-[3px] opacity-60" />
            <div className="absolute inset-[1px] bg-[#111] rounded-2xl flex items-center justify-center">
              <Bot className="w-5 h-5 text-white/90" />
            </div>
         </div>
      </div>
      
      <div className="flex flex-col gap-1.5 max-w-[85%]">
        <div className="px-6 py-4 rounded-3xl text-[15px] leading-relaxed tracking-wide bg-white/[0.03] border border-white/[0.05] rounded-tl-sm shadow-xl backdrop-blur-2xl text-white/85 flex items-center gap-4 mt-2">
          <span className="flex gap-1.5">
            <motion.span animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0 }} className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
            <motion.span animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.15 }} className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]" />
            <motion.span animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.3 }} className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
          </span>
          <span className="text-white/50 text-[13px] font-mono tracking-widest uppercase font-semibold">Processing</span>
        </div>
      </div>
    </motion.div>
  );
}

function MessageBubble({ msg, index }: { msg: any, index: number }) {
  const isAI = msg.role === 'ai';
  const isTool = msg.role === 'tool';

  if (isTool) {
    return (
      <motion.div layout initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ duration: 0.4, delay: index * 0.1 }} className="mx-auto w-full flex justify-center py-4">
        <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col bg-[#050505]/80 border border-emerald-500/20 rounded-2xl overflow-hidden backdrop-blur-xl shadow-[0_0_30px_-5px_rgba(16,185,129,0.15)] relative group w-full max-w-2xl cursor-default">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent opacity-50 group-hover:opacity-100 transition-opacity"></div>
          <div className="px-5 py-3 border-b border-white/[0.03] bg-emerald-500/[0.02] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 shadow-inner">
                <FileCode2 className="w-4 h-4 text-emerald-400" />
              </div>
              <span className="font-mono text-xs text-white/90 tracking-wide">{msg.toolName}</span>
            </div>
            <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
               <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
               <span className="font-mono text-[9px] text-emerald-300 uppercase tracking-widest font-bold">Executed</span>
            </div>
          </div>
          <div className="px-5 py-4">
            <span className="text-sm font-mono text-white/60 leading-relaxed tracking-wide">{msg.content}</span>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div layout initial={{ opacity: 0, y: 20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 25, delay: index * 0.1 }} className={`flex w-full gap-5 group ${!isAI ? 'flex-row-reverse' : ''}`}>
      <div className="shrink-0 flex flex-col items-center">
         <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg relative ${isAI ? '' : 'bg-gradient-to-br from-indigo-500 to-purple-600'}`}>
            {isAI && <motion.div animate={{ rotate: 360 }} transition={{ duration: 8, repeat: Infinity, ease: "linear" }} className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-indigo-500 via-emerald-400 to-purple-500 blur-[3px] opacity-40 group-hover:opacity-60 transition-opacity" />}
            {isAI ? (
              <div className="absolute inset-[1px] bg-[#111] rounded-2xl flex items-center justify-center">
                <Bot className="w-5 h-5 text-white/90" />
              </div>
            ) : (
              <User className="w-5 h-5 text-white" />
            )}
         </div>
      </div>
      
      <div className={`flex flex-col gap-1.5 max-w-[85%] ${!isAI ? 'items-end' : ''}`}>
        <div className="flex items-center gap-2 text-[10px] text-white/30 uppercase font-mono px-1 tracking-widest">
          <span className="font-semibold text-white/50">{isAI ? 'Neuro-X1' : 'You'}</span>
          <span>•</span>
          <span>{msg.time}</span>
        </div>
        
        <div className={`px-6 py-4 rounded-3xl text-[15px] leading-relaxed tracking-wide ${isAI ? 'bg-white/[0.03] border border-white/[0.05] rounded-tl-sm shadow-xl backdrop-blur-2xl text-white/85' : 'bg-[#1a1a1a] border border-white/[0.08] rounded-tr-sm shadow-2xl text-white/90'}`}>
          {msg.content.includes('```') ? (
            <div className="flex flex-col gap-4">
              <p>{msg.content.split('```')[0]}</p>
              <motion.div whileHover={{ scale: 1.01 }} transition={{ type: "spring", stiffness: 400, damping: 30 }} className="group/code relative rounded-2xl overflow-hidden border border-white/10 bg-[#050505] shadow-2xl">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.05] bg-white/[0.02]">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-500/50"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50"></div>
                    </div>
                    <span className="ml-2 text-[10px] font-mono text-white/40 uppercase tracking-widest font-semibold flex-shrink-0">typescript</span>
                  </div>
                  <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-1.5 text-[10px] font-mono text-white/30 hover:text-white transition-colors uppercase tracking-widest px-2 py-1 rounded bg-white/5 hover:bg-white/10">
                     <Copy className="w-3 h-3" /> Copy
                  </motion.button>
                </div>
                <div className="p-5 overflow-x-auto no-scrollbar">
                  <pre className="font-mono text-sm text-white/70 leading-loose">
                    {msg.content.split('```')[1].replace('typescript\n', '').trim()}
                  </pre>
                </div>
              </motion.div>
              <p>{msg.content.split('```')[2]}</p>
            </div>
          ) : (
            <p>{msg.content}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
