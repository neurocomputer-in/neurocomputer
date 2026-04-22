import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Mic, Send, Paperclip } from 'lucide-react';

export function ChatInput({ onSend, isTyping }: { onSend: (val: string) => void, isTyping: boolean }) {
  const [isRecording, setIsRecording] = React.useState(false);
  const [val, setVal] = React.useState('');
  const [focused, setFocused] = React.useState(false);

  const handleSend = () => {
    if (val.trim() && !isTyping) {
      onSend(val.trim());
      setVal('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 p-6 z-30 shrink-0 bg-gradient-to-t from-black via-[#020202]/90 to-transparent pt-24 pointer-events-none">
      <motion.div 
        layout 
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="max-w-4xl mx-auto relative group pointer-events-auto"
      >
        {/* Magnetic Glow effect */}
        <motion.div 
           animate={{ opacity: focused || val ? 1 : 0.4 }}
           className="absolute -inset-1 bg-gradient-to-r from-indigo-500/40 via-purple-500/40 to-emerald-500/40 rounded-[32px] blur-xl transition-opacity duration-700" 
        />
        
        <div className={`relative bg-[#050505]/80 backdrop-blur-3xl rounded-[28px] p-2 flex items-end gap-2 border transition-colors duration-300 shadow-[0_8px_32px_-8px_rgba(0,0,0,0.8)] ${focused ? 'border-indigo-500/40' : 'border-white/10 hover:border-white/20'}`}>
          
          <motion.button whileHover={{ scale: 1.1, rotate: 15 }} whileTap={{ scale: 0.9 }} className="p-3.5 text-white/40 hover:text-white/90 hover:bg-white/10 rounded-2xl transition-colors shrink-0 mb-0.5 mt-0.5 ml-0.5">
            <Paperclip className="w-5 h-5" />
          </motion.button>

          <div className="flex-1 min-h-[48px] py-4 flex flex-col justify-center">
            <AnimatePresence mode="wait">
              {isRecording ? (
                <motion.div 
                  key="recording"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex items-center gap-3 px-3 text-rose-400 text-sm font-medium tracking-wide"
                >
                  <motion.span animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity }} className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.6)]" />
                  Neural Voice Input Active...
                </motion.div>
              ) : (
                <motion.textarea 
                  key="input"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  value={val}
                  onChange={e => setVal(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onFocus={() => setFocused(true)}
                  onBlur={() => setFocused(false)}
                  disabled={isTyping}
                  placeholder={isTyping ? "Neuro is typing..." : "Send a message to Neuro..."}
                  className="w-full bg-transparent border-none outline-none resize-none px-3 text-[15px] text-white placeholder:text-white/30 max-h-40 focus:ring-0 overflow-y-auto font-sans tracking-wide disabled:opacity-50"
                  rows={1}
                  style={{ height: val ? 'auto' : '24px' }}
                />
              )}
            </AnimatePresence>
          </div>

          <div className="flex items-center gap-1.5 shrink-0 mb-1 pr-1 bg-white/[0.03] rounded-2xl p-1 border border-white/[0.05]">
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setIsRecording(!isRecording)}
              disabled={isTyping}
              className={`p-3 rounded-xl transition-all duration-300 ${isRecording ? 'bg-rose-500 text-white shadow-[0_0_20px_rgba(244,63,94,0.5)]' : 'text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-50'}`}
            >
              <Mic className="w-5 h-5" />
            </motion.button>
            
            <motion.button 
              onClick={handleSend}
              disabled={!val.trim() || isTyping}
              whileHover={{ scale: (val.trim() && !isTyping) ? 1.05 : 1 }}
              whileTap={{ scale: (val.trim() && !isTyping) ? 0.95 : 1 }}
              className={`p-3 rounded-xl transition-all duration-300 ${(val.trim() && !isTyping) ? 'bg-indigo-500 text-white shadow-[0_0_20px_rgba(99,102,241,0.5)] cursor-pointer' : 'bg-transparent text-white/20 cursor-not-allowed'}`}
            >
              <Send className="w-5 h-5 ml-0.5" />
            </motion.button>
          </div>
        </div>
        
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="absolute -bottom-6 left-0 right-0 flex justify-center gap-4 text-[10px] uppercase font-mono tracking-widest text-white/20 font-semibold selection:bg-none">
          <span className="hover:text-white/50 cursor-pointer transition-colors">Alpha Build</span>
          <span>•</span>
          <span className="hover:text-white/50 cursor-pointer transition-colors">Vision Capable</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
