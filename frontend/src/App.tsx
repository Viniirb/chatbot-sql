import { Bot, Database } from 'lucide-react';
import { ChatInput } from './components/ChatInput/ChatInput';
import { MessageBubble } from './components/MessageBubble/MessageBubble';
import { useChat } from './hooks/useChat';
import { useEffect, useRef } from 'react';

export default function App() {
  const { messages, loading, sendMessage } = useChat();
  const chatBoxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  return (
  <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900 font-sans">
    <header className="p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center space-x-3 max-w-4xl mx-auto">
        <Database size={28} className="text-blue-500" />
        <h1 className="text-xl font-semibold text-gray-800 dark:text-white">Chat com Banco de Dados</h1>
      </div>
    </header>

    <main className="flex-1 overflow-y-auto">
      <div className="p-4 space-y-4 max-w-4xl mx-auto" ref={chatBoxRef}>
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))}
        {loading && (
          <div className="flex items-start space-x-3 animate-pulse">
            <div className="p-3 bg-gray-200 dark:bg-gray-700 rounded-full">
              <Bot size={20} className="text-gray-600 dark:text-gray-400" />
            </div>
            <div className="px-4 py-3 text-gray-700 bg-gray-200 dark:bg-gray-700 rounded-lg">
              Pensando...
            </div>
          </div>
        )}
      </div>
    </main>

    <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
      <div className="max-w-4xl mx-auto">
        <ChatInput onSendMessage={sendMessage} isLoading={loading} />
      </div>
    </div>
  </div>
);
}
