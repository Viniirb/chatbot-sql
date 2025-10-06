import { useState, useEffect, useRef } from 'react';
import { MessageBubble } from './components/MessageBubble/MessageBubble';
import { useChat } from './hooks/useChat';
import { Bot, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { Sidebar } from './components/Sidebar/Sidebar';
import { AnimatePresence } from 'framer-motion';
import { Header } from './components/Header/Header';
import { Footer } from './components/Footer/Footer';
import { Toaster } from 'react-hot-toast';

export default function App() {
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const { 
    sessions, 
    activeSession, 
    loading, 
    sendMessage, 
    createNewSession, 
    switchSession, 
    deleteSession,
    togglePinSession,
    renameSession,
    abortRequest 
  } = useChat();
  const chatBoxRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [activeSession?.messages.length]);

  return (
    <div className="flex h-screen bg-black font-sans text-gray-200 overflow-hidden">
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#27272a',
            color: '#e4e4e7',
            border: '1px solid #3f3f46',
          },
        }}
      />
      <Sidebar 
        isOpen={isSidebarOpen}
        sessions={sessions} 
        activeSessionId={activeSession?.id || null} 
        onNewChat={createNewSession} 
        onSwitchChat={switchSession}
        onDeleteChat={deleteSession}
        onTogglePin={togglePinSession}
        onRenameChat={renameSession}
      />
      <div className="flex flex-col flex-1 relative bg-gray-900/30">
        <button 
          onClick={() => setSidebarOpen(!isSidebarOpen)} 
          className="absolute top-4 left-4 bg-gray-800/50 text-gray-300 p-2 rounded-full hover:bg-gray-700 z-10"
        >
          {isSidebarOpen ? <PanelLeftClose size={16}/> : <PanelLeftOpen size={16}/>}
        </button>
        
        <Header />

        <main className="flex-1 overflow-y-auto w-full max-w-4xl mx-auto custom-scroll">
          <div className="p-4 space-y-6" ref={chatBoxRef}>
            <AnimatePresence>
              {activeSession?.messages.map((msg, index) => (
                <MessageBubble key={`${activeSession.id}-${index}`} message={msg} />
              ))}
            </AnimatePresence>
            {loading && (
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full bg-gray-700">
                  <Bot size={20} className="text-gray-400" />
                </div>
                <div className="flex items-center space-x-2 px-4 py-3 bg-gray-700 rounded-lg">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse"></div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </main>

        <Footer 
            onSendMessage={sendMessage} 
            isLoading={loading} 
            onStop={abortRequest} 
        />
      </div>
    </div>
  );
}