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
  const hasError = !!message.error;
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [canRetryNow, setCanRetryNow] = useState(true);
  
  useEffect(() => {
    if (!message.error?.canRetryAt) {
      setCanRetryNow(true);
      setTimeRemaining(0);
      return;
    }
    
    const updateTimer = () => {
      const now = new Date().getTime();
      const retryTime = message.error!.canRetryAt!.getTime();
      const remaining = Math.max(0, Math.ceil((retryTime - now) / 1000));
      
      setTimeRemaining(remaining);
      setCanRetryNow(remaining === 0);
    };
    
    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    
    return () => clearInterval(interval);
  }, [message.error]);
  
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
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 10 }}
      transition={{ duration: 0.3 }}
      className={`flex items-start space-x-4 ${
        message.role === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
      }`}
    >
      <div
        className={`flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full ${
          hasError 
            ? 'bg-red-600 text-white'
            : message.role === 'user' 
            ? 'bg-primary text-white' 
            : 'bg-gray-700 text-gray-400'
        }`}
      >
        {hasError ? <AlertCircle size={20} /> : message.role === 'user' ? <User size={20} /> : <Bot size={20} />}
      </div>

      <div className="flex flex-col gap-2 max-w-2xl">
        <div
          className={`px-4 py-2 rounded-lg prose prose-invert prose-p:my-2 prose-headings:my-3 ${
            hasError
              ? 'bg-red-900/30 border border-red-600/50 text-gray-200'
              : message.role === 'user'
              ? 'bg-bubble-user text-white'
              : 'bg-gray-700 text-gray-200'
          }`}
        >
          <ReactMarkdown
            components={{
              code(props: React.ComponentProps<'code'> & { inline?: boolean }) {
                const { inline, className, children, ...rest } = props;
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    style={a11yDark as any}
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
        
        {hasError && message.error && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-900/50 border border-red-600/50 rounded-lg text-sm">
            <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
            <span className="text-red-200 flex-1">{message.error.message}</span>
            {message.error.canRetry && onRetry && (
              <button
                onClick={() => canRetryNow && onRetry(message.id)}
                disabled={!canRetryNow}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors flex-shrink-0 ${
                  canRetryNow 
                    ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer' 
                    : 'bg-gray-600 text-gray-300 cursor-not-allowed opacity-60'
                }`}
              >
                {canRetryNow ? (
                  <>
                    <RefreshCw size={14} />
                    Reenviar
                  </>
                ) : (
                  <>
                    <Clock size={14} />
                    Aguarde {formatTime(timeRemaining)}
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};