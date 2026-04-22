import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, MessageSquare, PanelLeftClose, Settings, Box, Database, Cpu } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedProject } from '@/store/projectSlice';
import { setActiveTab, loadMessages } from '@/store/conversationSlice';
import { useLiveKitContext } from '@/providers/LiveKitProvider';

export function Sidebar({ isOpen, setIsOpen }: { isOpen: boolean, setIsOpen: (val: boolean) => void }) {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const conversations = useAppSelector(s => s.conversations.conversations);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const { connectToConversation } = useLiveKitContext();

  const handleTabClick = async (cid: string) => {
    dispatch(setActiveTab(cid));
    dispatch(loadMessages(cid));
    try {
      if (connectToConversation) {
        await connectToConversation(cid);
      }
    } catch (err) {}
  };

  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: "spring", bounce: 0, duration: 0.5 }}
          className="h-full bg-black/20 backdrop-blur-xl border-r border-white/[0.05] flex flex-col overflow-hidden whitespace-nowrap shrink-0 z-50 absolute md:relative top-0 left-0"
        >
          <div className="p-5 flex items-center justify-between border-b border-white/[0.05] shrink-0 hover:bg-white/[0.02] transition-colors">
            <motion.div whileHover={{ scale: 1.05 }} className="flex items-center gap-3 cursor-pointer">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-indigo-500/30 flex items-center justify-center relative shadow-[0_0_20px_-5px_rgba(99,102,241,0.4)]">
                <Cpu className="w-5 h-5 text-indigo-300" />
              </div>
              <span className="font-display font-semibold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">Neuro</span>
            </motion.div>
            <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={() => setIsOpen(false)} className="p-2 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors">
              <PanelLeftClose className="w-5 h-5" />
            </motion.button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-8">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between px-2">
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest font-semibold">Projects</span>
                <motion.button whileHover={{ scale: 1.2, rotate: 180 }} whileTap={{ scale: 0.9 }} className="text-white/40 hover:text-white transition-colors">
                  <Plus className="w-4 h-4" />
                </motion.button>
              </div>
              <div className="flex flex-col gap-1">
                {projects.map(p => (
                  <ProjectItem 
                    key={p.id || 'all'}
                    icon={<Box size={16}/>} 
                    name={p.name} 
                    active={selectedProjectId === p.id} 
                    onClick={() => dispatch(setSelectedProject(p.id))}
                  />
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between px-2">
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest font-semibold">History</span>
              </div>
              <div className="flex flex-col gap-1">
                {conversations.map(c => (
                  <HistoryItem 
                    key={c.id}
                    title={c.title || 'New Chat'} 
                    time={new Date(c.updatedAt || Date.now()).toLocaleDateString([], { month: 'short', day: 'numeric'})} 
                    active={activeTabCid === c.id} 
                    onClick={() => handleTabClick(c.id)}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="p-4 border-t border-white/[0.05] shrink-0">
            <motion.button whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.05)" }} whileTap={{ scale: 0.98 }} className="flex items-center gap-3 px-4 py-3 w-full rounded-xl bg-white/[0.02] transition-colors text-white/70">
              <Settings className="w-5 h-5 text-white/50" />
              <span className="text-sm font-medium tracking-wide">Settings</span>
            </motion.button>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function ProjectItem({ icon, name, active = false, onClick }: { icon: React.ReactNode, name: string, active?: boolean, onClick?: () => void }) {
  return (
    <motion.button onClick={onClick} whileHover={{ x: 4, backgroundColor: "rgba(255,255,255,0.05)" }} whileTap={{ scale: 0.98 }} className={`relative flex items-center gap-3 px-3 py-2.5 w-full rounded-xl transition-colors ${active ? 'text-white' : 'text-white/50'}`}>
      {active && (
        <motion.div layoutId="active-project" className="absolute inset-0 bg-indigo-500/20 border border-indigo-500/30 rounded-xl" transition={{ type: "spring", bounce: 0.2, duration: 0.6 }} />
      )}
      <span className={`relative z-10 ${active ? 'text-indigo-400' : 'text-white/40'}`}>{icon}</span>
      <span className="relative z-10 text-sm font-medium tracking-wide">{name}</span>
    </motion.button>
  );
}

function HistoryItem({ title, time, active = false, onClick }: { title: string, time: string, active?: boolean, onClick?: () => void }) {
  return (
    <motion.button onClick={onClick} whileHover={{ x: 4, backgroundColor: "rgba(255,255,255,0.05)" }} whileTap={{ scale: 0.98 }} className={`group relative flex items-center gap-3 px-3 py-3 w-full rounded-xl text-left ${active ? 'bg-white/5' : ''}`}>
      <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${active ? 'bg-white/10 text-white' : 'bg-transparent text-white/30 group-hover:text-white/70 group-hover:bg-white/5'}`}>
        <MessageSquare className="w-4 h-4" />
      </div>
      <div className="flex flex-col min-w-0">
        <span className={`text-sm tracking-wide truncate ${active ? 'text-white font-medium' : 'text-white/60 group-hover:text-white/90'}`}>{title}</span>
        <span className="text-[10px] text-white/40 mt-0.5 tracking-wider">{time}</span>
      </div>
    </motion.button>
  );
}
