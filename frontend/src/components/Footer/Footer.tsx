import { ChatInput } from '../ChatInput/ChatInput';

interface Props {
  onSendMessage: (text: string, files: File[]) => void;
  isLoading: boolean;
  onStop?: () => void;
}

export const Footer = ({ onSendMessage, isLoading, onStop }: Props) => {
  return (
    <footer className="p-4 border-t border-gray-800">
      <div className="max-w-4xl mx-auto">
        <ChatInput 
          onSendMessage={onSendMessage} 
          isLoading={isLoading} 
          onStop={onStop} 
        />
        <p className="text-xs text-center text-gray-600 mt-3">
          © 2025 - N-Tecnologias. Todos os direitos reservados.
        </p>
      </div>
    </footer>
  );
};