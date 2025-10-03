import { SendHorizontal } from 'lucide-react';
import { useState } from 'react';

interface Props {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

export const ChatInput = ({ onSendMessage, isLoading }: Props) => {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    onSendMessage(prompt);
    setPrompt('');
  };

  return (
  <form onSubmit={handleSubmit} className="relative">
    <input
      type="text"
      value={prompt}
      onChange={(e) => setPrompt(e.target.value)}
      placeholder="Pergunte algo ao seu banco de dados..."
      disabled={isLoading}
      className="w-full p-4 pr-16 text-gray-800 bg-gray-100 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600"
    />
    <button
      type="submit"
      disabled={isLoading}
      className="absolute inset-y-0 right-0 flex items-center justify-center w-14 h-14 text-white bg-blue-600 rounded-full transition-colors hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
    >
      <SendHorizontal size={20} />
    </button>
  </form>
);
};