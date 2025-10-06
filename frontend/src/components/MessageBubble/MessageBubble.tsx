import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../types';
import { Bot, User } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  message: Message;
}

export const MessageBubble = ({ message }: Props) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 10 }}
      transition={{ duration: 0.3 }}
      className={`flex items-start space-x-4 ${
        message.sender === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
      }`}
    >
      <div
        className={`flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full ${
          message.sender === 'user' ? 'bg-primary text-white' : 'bg-gray-700 text-gray-400'
        }`}
      >
        {message.sender === 'user' ? <User size={20} /> : <Bot size={20} />}
      </div>

      <div
        className={`px-4 py-2 rounded-lg max-w-2xl prose prose-invert prose-p:my-2 prose-headings:my-3 ${
          message.sender === 'user'
            ? 'bg-bubble-user text-white'
            : 'bg-gray-700 text-gray-200'
        }`}
      >
        <ReactMarkdown
          components={{
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            code(props: any) {
              const { inline, className, children, ...rest } = props;
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  style={a11yDark as any}
                  language={match[1]}
                  PreTag="div"
                  {...rest}
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
          {message.text}
        </ReactMarkdown>
      </div>
    </motion.div>
  );
};