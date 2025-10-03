import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../types';
import { Bot, User } from 'lucide-react';

interface Props {
  message: Message;
}

export const MessageBubble = ({ message }: Props) => {
  return (
    <div
      className={`flex items-start space-x-3 max-w-2xl animate-fade-in ${
        message.sender === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
      }`}
    >
      <div
        className={`flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full ${
          message.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
        }`}
      >
        {message.sender === 'user' ? <User size={20} /> : <Bot size={20} />}
      </div>

      <div
        className={`px-4 py-2 rounded-lg shadow-md ${
          message.sender === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-white text-gray-800 dark:bg-gray-700 dark:text-gray-200'
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
    </div>
  );
};