import { useState, useEffect, useRef, Suspense, lazy } from 'react';
import { useChat } from './presentation/hooks/use-chat';
import { Bot, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';

const MessageBubble = lazy(() => import('./components/MessageBubble/MessageBubble').then(module => ({ default: module.MessageBubble })));
const Sidebar = lazy(() => import('./components/Sidebar/Sidebar').then(module => ({ default: module.Sidebar })));
const Header = lazy(() => import('./components/Header/Header').then(module => ({ default: module.Header })));
const Footer = lazy(() => import('./components/Footer/Footer').then(module => ({ default: module.Footer })));

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
    updateSession,
    retryMessage,
    abortMessage,
    getActiveSessionStats
  } = useChat();

  const togglePinSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      updateSession(sessionId, { isPinned: !session.isPinned });
    }
  };

  const renameSession = (sessionId: string, newTitle: string) => {
    updateSession(sessionId, { title: newTitle });
  };
  const chatBoxRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [activeSession?.messages.length]);

  return (
    <div className="flex h-screen bg-black font-sans text-gray-200 overflow-hidden relative">
      {/* Background animated blur effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-purple-600/30 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-pink-600/20 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '4s' }} />
      </div>
      <Toaster 
        position="top-right"
        toastOptions={{
          className: 'toast-slide-in',
          style: {
            background: '#27272a',
            color: '#e4e4e7',
            border: '1px solid #3f3f46',
          },
        }}
      />
      <Suspense fallback={<div className="w-64 bg-gray-900 border-r border-gray-800 animate-pulse" />}>
        <Sidebar 
          isOpen={isSidebarOpen}
          sessions={sessions} 
          activeSessionId={activeSession?.id || null} 
          onNewChat={createNewSession} 
          onSwitchChat={switchSession}
          onDeleteChat={deleteSession}
          onTogglePin={togglePinSession}
          onRenameChat={renameSession}
          onGetSessionStats={getActiveSessionStats}
        />
      </Suspense>
      <div className="flex flex-col flex-1 relative backdrop-blur-xl bg-gray-950/50 z-10">
        <button 
          onClick={() => setSidebarOpen(!isSidebarOpen)} 
          className="absolute top-4 left-4 bg-white/5 backdrop-blur-md border border-white/10 text-gray-300 p-2 rounded-xl hover:bg-white/10 hover:border-purple-500/50 transition-all duration-300 z-20 shadow-lg shadow-purple-500/10"
        >
          {isSidebarOpen ? <PanelLeftClose size={16}/> : <PanelLeftOpen size={16}/>}
        </button>
        
        <Suspense fallback={<div className="p-4 border-b border-gray-800 h-20 animate-pulse" />}>
          <Header />
        </Suspense>

        <main className="flex-1 overflow-y-auto w-full max-w-4xl mx-auto custom-scroll">
          <div className="p-4 space-y-6" ref={chatBoxRef}>
            <AnimatePresence>
              {activeSession?.messages.map((msg, index) => (
                <Suspense key={`${activeSession.id}-${index}`} fallback={<div className="h-16 animate-pulse bg-gray-800 rounded-lg" />}>
                  <MessageBubble message={msg} onRetry={retryMessage} />
                </Suspense>
              ))}
            </AnimatePresence>
            {loading && (
              <div className="flex items-start space-x-4 animate-fade-in-up">
                <div className="flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur-sm border border-purple-500/30 animate-float">
                  <Bot size={20} className="text-purple-300" />
                </div>
                <div className="flex items-center space-x-2 px-5 py-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 backdrop-blur-sm border border-purple-500/20 rounded-2xl shadow-lg shadow-purple-500/10">
                  <div className="w-2 h-2 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-pulse [animation-delay:-0.3s] shadow-lg shadow-purple-400/50"></div>
                  <div className="w-2 h-2 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-pulse [animation-delay:-0.15s] shadow-lg shadow-purple-400/50"></div>
                  <div className="w-2 h-2 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-pulse shadow-lg shadow-purple-400/50"></div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </main>

        <Suspense fallback={<div className="h-32 bg-gray-900 border-t border-gray-800 animate-pulse" />}>
          <Footer 
              onSendMessage={sendMessage} 
              isLoading={loading} 
              onStop={abortMessage} 
          />
        </Suspense>
      </div>
    </div>
  );
}