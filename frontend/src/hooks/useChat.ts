import { useState, useEffect, useRef } from 'react';
import type { Message, ChatSession } from '../types';
import { askAgent, generateTitle } from '../services/api';
import { v4 as uuidv4 } from 'uuid';

const CHAT_SESSIONS_KEY = 'chat_sessions';

export const useChat = () => {
  const [sessions, setSessions] = useState<Record<string, ChatSession>>({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      const savedSessions = localStorage.getItem(CHAT_SESSIONS_KEY);
      const parsedSessions = savedSessions ? JSON.parse(savedSessions) : null;
      
      if (parsedSessions && Object.keys(parsedSessions).length > 0) {
        setSessions(parsedSessions);
        setActiveSessionId(Object.keys(parsedSessions)[0]);
      } else {
        const newId = uuidv4();
        const newSession: ChatSession = {
          id: newId,
          title: "Nova Conversa",
          messages: [{ sender: 'bot', text: "Olá! Em que posso ajudar com o banco de dados hoje?" }],
          isPinned: false,
        };
        setSessions({ [newId]: newSession });
        setActiveSessionId(newId);
      }
    } catch (error) {
      console.error("Failed to load sessions from localStorage", error);
    }
  }, []);

  useEffect(() => {
    try {
      if (Object.keys(sessions).length > 0) {
        localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(sessions));
      } else {
        localStorage.removeItem(CHAT_SESSIONS_KEY);
      }
    } catch (error) {
      console.error("Failed to save sessions to localStorage", error);
    }
  }, [sessions]);

  const createNewSession = () => {
    const existingEmptySession = Object.values(sessions).find(
      session => session.title === "Nova Conversa" && session.messages.length <= 1
    );

    if (existingEmptySession) {
      setActiveSessionId(existingEmptySession.id);
      return;
    }
    
    const newId = uuidv4();
    const newSession: ChatSession = {
      id: newId,
      title: "Nova Conversa",
      messages: [{ sender: 'bot', text: "Olá! Em que posso ajudar com o banco de dados hoje?" }],
      isPinned: false,
    };
    setSessions(prev => ({ [newId]: newSession, ...prev }));
    setActiveSessionId(newId);
  };

  const switchSession = (sessionId: string) => {
    if (loading) abortRequest();
    setActiveSessionId(sessionId);
  };
  
  const deleteSession = (sessionId: string) => {
    setSessions(prev => {
        const newSessions = { ...prev };
        delete newSessions[sessionId];
        return newSessions;
    });

    if (activeSessionId === sessionId) {
        const remainingIds = Object.keys(sessions).filter(id => id !== sessionId);
        if (remainingIds.length > 0) {
            setActiveSessionId(remainingIds[0]);
        } else {
            createNewSession();
        }
    }
  };

  const togglePinSession = (sessionId: string) => {
    setSessions(prev => {
        const session = prev[sessionId];
        if (!session) return prev;
        const updatedSession = { ...session, isPinned: !session.isPinned };
        return { ...prev, [sessionId]: updatedSession };
    });
  };
  
  const renameSession = (sessionId: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    setSessions(prev => {
        const session = prev[sessionId];
        if (!session) return prev;
        const updatedSession = { ...session, title: newTitle.trim() };
        return { ...prev, [sessionId]: updatedSession };
    });
  };

  const abortRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
    }
  };
  
  const sendMessage = async (text: string, files: File[]) => {
    if (!activeSessionId || (!text.trim() && files.length === 0)) return;

    const userMessage: Message = { sender: 'user', text };
    const isNewConversation = sessions[activeSessionId]?.messages.length === 1;
    
    setSessions(prev => {
      if (!activeSessionId) return prev;
      const active = prev[activeSessionId];
      const updatedSession = { ...active, messages: [...active.messages, userMessage] };
      return { ...prev, [activeSessionId]: updatedSession };
    });

    setLoading(true);
    abortControllerRef.current = new AbortController();

    const botResponseText = await askAgent(text, abortControllerRef.current.signal);

    if (botResponseText === 'REQUEST_ABORTED') return;

    setLoading(false);
    abortControllerRef.current = null;

    let finalBotResponse = botResponseText;
    if (!botResponseText || !botResponseText.trim()) {
      finalBotResponse = "Desculpe, não encontrei resultados para sua pergunta.";
    }
    
    const botMessage: Message = { sender: 'bot', text: finalBotResponse };

    setSessions(prev => {
        if (!activeSessionId) return prev;
        const active = prev[activeSessionId];
        const updatedSession = { ...active, messages: [...active.messages, botMessage] };
        return { ...prev, [activeSessionId]: updatedSession };
    });

    if (isNewConversation && text.trim()) {
        const newTitle = await generateTitle(text);
        setSessions(prev => {
            if (!activeSessionId) return prev;
            const active = prev[activeSessionId];
            if (!active) return prev;
            const updatedSession = { ...active, title: newTitle };
            return { ...prev, [activeSessionId]: updatedSession };
        });
    }
  };

  const activeSession = activeSessionId ? sessions[activeSessionId] : null;

  return { sessions, activeSession, loading, sendMessage, createNewSession, switchSession, deleteSession, togglePinSession, renameSession, abortRequest };
};