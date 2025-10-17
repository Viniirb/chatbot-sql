import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../core/domain/entities';

import { Bot, User, AlertCircle, RefreshCw, Clock } from 'lucide-react';
import { motion } from 'framer-motion';


interface Props {
  message: Message;
  onRetry?: (messageId: string) => void;
}
export const MessageBubble = ({ message, onRetry }: Props) => {

  // Sempre use a prop message.error, nunca um estado local para erro
  type MessageError = NonNullable<Message['error']>;
  const localError: MessageError | null = (message.error ?? null) as MessageError | null;
  const hasError = !!localError;
  const isRetrying = !!(message.metadata && (message.metadata as Record<string, unknown>)['retrying']);
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [canRetryNow, setCanRetryNow] = useState(true);

  useEffect(() => {
    if (hasError) {
      // debug: a mensagem contém erro
    }
    if (!localError?.canRetryAt) {
      setCanRetryNow(true);
      setTimeRemaining(0);
      return;
    }
    const updateTimer = () => {
      const now = new Date().getTime();
      let canRetryAtDate = localError!.canRetryAt!;
      if (!(canRetryAtDate instanceof Date)) {
        canRetryAtDate = new Date(canRetryAtDate as unknown as string);
      }
      const retryTime = canRetryAtDate.getTime();
      const remaining = Math.max(0, Math.ceil((retryTime - now) / 1000));
      setTimeRemaining(remaining);
      setCanRetryNow(remaining === 0);
    };
    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [localError, hasError, message.id]);

  const formatTime = (seconds: number): string => {
    if (seconds >= 3600) {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}h${mins > 0 ? ` ${mins}m` : ''}`;
    }
    if (seconds >= 60) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m${secs > 0 ? ` ${secs}s` : ''}`;
    }
    return `${seconds}s`;
  };

  const handleRetry = () => {
    if (canRetryNow && onRetry) {
      onRetry(message.id);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -5 }}
      transition={{ 
        duration: 0.3,
        ease: "easeOut"
      }}
      className={`flex items-start space-x-4 ${
        message.role === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
      }`}
    >
      <div className="relative">
        <div
          className={`flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full shadow-lg transition-all duration-300 ${
            hasError 
              ? 'bg-gradient-to-br from-red-500 to-red-700 text-white shadow-red-500/40 shadow-xl'
              : message.role === 'user' 
              ? 'bg-gradient-to-br from-purple-600 via-purple-500 to-purple-700 text-white shadow-purple-500/50 shadow-xl border border-purple-400/20' 
              : 'bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm text-purple-300 shadow-purple-500/30 border border-purple-500/30'
          }`}
        >
          {hasError ? <AlertCircle size={20} /> : message.role === 'user' ? <User size={20} /> : <Bot size={20} />}
        </div>
        {isRetrying && (
          <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
            <RefreshCw size={12} className="text-white animate-spin" />
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2 max-w-2xl">
        <div
          className={`px-5 py-3 rounded-2xl prose prose-invert prose-p:my-2 prose-headings:my-3 shadow-2xl backdrop-blur-xl transition-all duration-300 ${
            hasError
              ? 'bg-red-950/80 border border-red-500/50 text-gray-200 shadow-red-500/30'
              : message.role === 'user'
              ? 'bg-gradient-to-br from-purple-500/20 via-purple-600/30 to-pink-500/20 backdrop-blur-md border border-purple-400/40 text-white shadow-purple-500/30'
              : 'bg-gray-900/80 text-gray-200 border border-purple-500/30 shadow-purple-500/20'
          }`}
        >
          <ReactMarkdown
            components={{
              code(props: React.ComponentProps<'code'> & { inline?: boolean }) {
                const { inline, className, children, ...rest } = props;
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={a11yDark}
                    language={match[1]}
                    PreTag="div"
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...rest}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        {/* Renderiza bolha de erro SEMPRE que hasError for true */}
        {hasError && localError && (
          <>
            {/* debug: renderizando bolha de erro */}
            <div className="flex items-center gap-2 px-3 py-2 bg-red-900/50 border border-red-600/50 rounded-lg text-sm">
              <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
              <span className="text-red-200 flex-1">{localError.message}</span>
              {localError.canRetry && onRetry && (
                <button
                  onClick={handleRetry}
                  disabled={!canRetryNow}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all duration-300 flex-shrink-0 shadow-lg ${
                    canRetryNow 
                      ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white cursor-pointer hover:scale-105 shadow-red-500/40' 
                      : 'bg-gray-700 text-gray-400 cursor-not-allowed opacity-60'
                  }`}
                >
                  {canRetryNow ? (
                    <span className="flex items-center gap-1">
                      <RefreshCw size={14} />
                      Reenviar
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Clock size={14} />
                      Aguarde {formatTime(timeRemaining)}
                    </span>
                  )}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
};