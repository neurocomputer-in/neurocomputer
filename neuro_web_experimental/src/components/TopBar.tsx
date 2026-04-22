import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Volume2, VolumeX, PanelLeftOpen, Activity, ChevronDown, MonitorPlay, Radio } from 'lucide-react';
import WorkspaceDropdown from '@/components/workspace/WorkspaceDropdown';
import AgentDropdown from '@/components/agent/AgentDropdown';
import LlmSelector from '@/components/chat/LlmSelector';

export function TopBar({ sidebarOpen, setSidebarOpen, isLiveMode, onLiveToggle }: { sidebarOpen: boolean, setSidebarOpen: (val: boolean) => void, isLiveMode: boolean, onLiveToggle: () => void }) {
  const [ttsEnabled, setTtsEnabled] = React.useState(true);

  return (
    <header className="h-16 bg-black/20 backdrop-blur-xl border-b border-white/[0.05] flex items-center justify-between px-5 shrink-0 z-20 w-full shadow-sm relative">
      <div className="flex items-center gap-5">
        <AnimatePresence>
          {!sidebarOpen && (
            <motion.button 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </motion.button>
          )}
        </AnimatePresence>
        
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="hidden sm:flex items-center gap-2.5 px-4 py-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 shadow-[0_0_15px_-3px_rgba(16,185,129,0.2)]">
          <Activity className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono text-emerald-400 tracking-widest uppercase font-semibold">Live System</span>
        </motion.div>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden lg:flex items-center gap-2 p-1 bg-white/[0.02] rounded-xl border border-white/[0.05]">
          <WorkspaceDropdown />
          <div className="w-px h-6 bg-white/[0.05] mx-1"></div>
          <AgentDropdown />
          <div className="w-px h-6 bg-white/[0.05] mx-1"></div>
          <LlmSelector />
        </div>

        <div className="w-px h-6 bg-white/10 mx-2 hidden md:block"></div>

        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onLiveToggle}
          className={`px-4 py-2.5 rounded-xl flex items-center justify-center transition-all duration-300 shadow-lg border ${isLiveMode ? 'bg-rose-500/20 border-rose-500/40 text-rose-300' : 'bg-transparent border-rose-500/50 text-rose-400 hover:bg-rose-500/10'}`}
        >
          <Radio className={`w-4 h-4 mr-2 ${isLiveMode ? 'animate-pulse text-rose-400' : ''}`} />
          <span className="text-sm font-medium tracking-wide">Live Mode</span>
        </motion.button>

        <motion.button 
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setTtsEnabled(!ttsEnabled)}
          className={`hidden md:flex p-2.5 rounded-xl transition-all duration-300 shadow-lg ${ttsEnabled ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'bg-white/5 border border-white/5 hover:bg-white/10 text-white/50'}`}
          title="Toggle TTS"
        >
          {ttsEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
        </motion.button>
        
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="px-4 py-2.5 rounded-xl bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors text-white border border-white/10 text-sm font-medium tracking-wide shadow-md">
          <MonitorPlay className="w-4 h-4 mr-2 text-white/70" />
          Deploy
        </motion.button>
      </div>
    </header>
  );
}

function Selector({ label, value, active = false }: { label: string, value: string, active?: boolean }) {
  return (
    <motion.button whileHover={{ backgroundColor: "rgba(255,255,255,0.05)" }} className="flex items-center gap-3 px-3 py-1.5 rounded-lg transition-colors group">
      <div className="flex flex-col items-start leading-none gap-1">
         <span className="text-[9px] text-white/40 uppercase font-mono tracking-widest font-bold">{label}</span>
         <span className={`text-[13px] font-semibold tracking-wide ${active ? 'text-indigo-400' : 'text-white/80 group-hover:text-white'}`}>{value}</span>
      </div>
      <ChevronDown className={`w-4 h-4 ${active ? 'text-indigo-500/50' : 'text-white/30 group-hover:text-white/70'}`} />
    </motion.button>
  );
}
