import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Plus, Terminal, LayoutDashboard } from 'lucide-react';

interface Tab {
  id: string;
  title: string;
  icon: React.ReactNode;
}

export function TabBar() {
  const [tabs, setTabs] = React.useState<Tab[]>([
    { id: '1', title: 'Main Session', icon: <LayoutDashboard className="w-3.5 h-3.5"/> },
    { id: '2', title: 'Log Analysis', icon: <Terminal className="w-3.5 h-3.5"/> }
  ]);
  const [activeTab, setActiveTab] = React.useState('1');

  return (
    <div className="h-12 border-b border-white/[0.05] flex items-center px-2 bg-black/40 backdrop-blur-md shrink-0 overflow-x-auto no-scrollbar relative z-10 shadow-sm">
      <AnimatePresence mode="popLayout">
        {tabs.map((tab) => (
          <motion.div
            layout
            initial={{ opacity: 0, y: -10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8, transition: { duration: 0.15 } }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              group relative flex items-center gap-2 px-4 py-2 mx-1 mt-1 text-sm cursor-pointer select-none transition-colors min-w-[150px] max-w-[220px] rounded-t-xl
              ${activeTab === tab.id ? 'text-white bg-white/10' : 'text-white/40 hover:text-white/80 hover:bg-white/[0.05]'}
            `}
          >
            {activeTab === tab.id && (
              <motion.div 
                layoutId="active-tab-indicator"
                className="absolute top-0 left-2 right-2 h-[2px] bg-gradient-to-r from-indigo-500 to-purple-500 rounded-b-full shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
            <span className="flex-1 truncate flex items-center gap-2 text-[13px] font-medium tracking-wide">
               {tab.icon}
               <span className="truncate">{tab.title}</span>
            </span>
            <motion.button 
              whileHover={{ scale: 1.2, backgroundColor: "rgba(255,255,255,0.1)" }}
              whileTap={{ scale: 0.9 }}
              className={`p-1 rounded-md transition-colors ${activeTab === tab.id ? 'opacity-100 text-white/50 hover:text-white' : 'opacity-0 group-hover:opacity-100 text-white/30 hover:text-white/80'}`}
              onClick={(e) => {
                e.stopPropagation();
                setTabs(tabs.filter(t => t.id !== tab.id));
                if (activeTab === tab.id && tabs.length > 1) {
                  setActiveTab(tabs.find(t => t.id !== tab.id)!.id);
                }
              }}
            >
              <X className="w-3 h-3" />
            </motion.button>
          </motion.div>
        ))}
      </AnimatePresence>
      <motion.div layout>
        <motion.button 
          whileHover={{ scale: 1.1, backgroundColor: "rgba(255,255,255,0.1)" }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setTabs([...tabs, { id: Date.now().toString(), title: 'New Context', icon: <Terminal className="w-3.5 h-3.5"/> }])}
          className="p-2 ml-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
        </motion.button>
      </motion.div>
    </div>
  );
}
