import { useState } from 'react';
import type { Message } from '../types';
import { askAgent } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = { sender: 'user', text };
    setMessages(currentMessages => [...currentMessages, userMessage]);
    setLoading(true);

    let botResponseText = await askAgent(text);

    if (!botResponseText || !botResponseText.trim()) {
        botResponseText = "Desculpe, não encontrei resultados para sua pergunta. Tente ser mais específico ou verifique os dados.";
    }

    const botMessage: Message = { sender: 'bot', text: botResponseText };
    setMessages(currentMessages => [...currentMessages, botMessage]);
    setLoading(false);
  };

  return { messages, loading, sendMessage };
};