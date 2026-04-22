import React, { useState } from 'react';
import { AnimatePresence } from 'motion/react';
import { useAppSelector } from './store/hooks';
import { useChat } from './hooks/useChat';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { TabBar } from './components/TabBar';
import { ChatPanel } from './components/ChatPanel';
import { ChatInput } from './components/ChatInput';
import { Background } from './components/Background';
import { LiveSession } from './components/LiveSession';

export interface ChatMessage {
  id: string;
  role: 'ai' | 'user' | 'tool';
  content: string;
  time: string;
  toolName?: string;
}

const INITIAL_MESSAGES: ChatMessage[] = [
  { id: '1', role: 'ai', content: 'Neural systems online. How can I assist you in this workspace?', time: '09:00' },
  { id: '2', role: 'user', content: 'Load the Alpha Core project and analyze the main entry points.', time: '09:02' },
  { id: '3', role: 'tool', toolName: 'OpenCode Analysis', content: 'Analyzed 14 files in ./src. Main entry points found in main.ts and api/routes.ts.', time: '09:02' },
  { id: '4', role: 'ai', content: 'I have successfully loaded the Alpha Core project. The execution flow starts at `src/core/main.ts`.\n\n```typescript\nimport { Logger } from "@core/logger";\n\nasync function bootstrap() {\n  const app = new AlphaCore();\n  \n  Logger.info("Starting initialization sequence...");\n  await app.initialize();\n  \n  app.listen(3000, () => {\n    Logger.info("Neuro running on port 3000");\n  });\n}\n\nbootstrap();\n```\nWould you like me to map the dependency graph?', time: '09:03' }
];

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLiveMode, setIsLiveMode] = useState(false);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const reduxMessages = activeTabCid ? (tabMessages[activeTabCid] ?? []) : [];
  const isLoading = useAppSelector(s => s.chat.isLoading);

  const { sendMessage } = useChat();

  const mappedMessages: ChatMessage[] = reduxMessages.flatMap(m => {
    const res: ChatMessage[] = [];
    if (m.text) {
      res.push({
        id: m.id,
        role: m.isUser ? 'user' : 'ai',
        content: m.text,
        time: m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    }
    if (m.toolCalls && Array.isArray(m.toolCalls)) {
      m.toolCalls.forEach((tc, idx) => {
        if (tc.tool) {
          res.push({
            id: m.id + '-tool-' + idx,
            role: 'tool',
            content: tc.output || 'Executed process.',
            toolName: tc.tool,
            time: m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          });
        }
      });
    }
    return res;
  });

  const handleSendMessage = (content: string) => {
    sendMessage(content);
  };

  const isTyping = isLoading;

  return (
    <>
      <Background />
      <div className="flex h-screen w-full bg-transparent overflow-hidden selection:bg-indigo-500/30 relative z-10 text-white">
        <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} />
        
        <main className="flex-1 flex flex-col min-w-0 relative h-full">
          <TopBar 
            sidebarOpen={sidebarOpen} 
            setSidebarOpen={setSidebarOpen} 
            isLiveMode={isLiveMode}
            onLiveToggle={() => setIsLiveMode(!isLiveMode)}
          />
          <TabBar />
          
          <div className="flex-1 relative flex flex-col overflow-hidden">
            <AnimatePresence>
              {isLiveMode && (
                <LiveSession onClose={() => setIsLiveMode(false)} />
              )}
            </AnimatePresence>
            
            <ChatPanel messages={mappedMessages} isTyping={isTyping} />
            <ChatInput onSend={handleSendMessage} isTyping={isTyping} />
          </div>
        </main>
      </div>
    </>
  );
}
