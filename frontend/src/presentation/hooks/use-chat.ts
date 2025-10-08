import { useState, useRef, useCallback, useEffect } from 'react';
import type { ChatSession, Message, SessionStats } from '../../core/domain/entities';
import type { ApiError } from '../../core/domain/value-objects';
import { DIContainer } from '../../infrastructure/di/container';
import type { CreateSessionUseCase, SendMessageUseCase, GenerateTitleUseCase } from '../../core/application/use-cases/chat';
import type { DeleteSessionUseCase, UpdateSessionUseCase, GetSessionsUseCase } from '../../core/application/use-cases/session';
import { v4 as uuidv4 } from 'uuid';

export interface UseChatReturn {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  loading: boolean;
  createNewSession: () => Promise<void>;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void;
  sendMessage: (content: string, files?: File[]) => Promise<void>;
  retryMessage: (messageId: string) => Promise<void>;
  abortMessage: () => void;
  getActiveSessionStats: () => Promise<SessionStats | null>;
}

export const useChat = (): UseChatReturn => {
  const container = DIContainer.getInstance();
  const getSessionsUseCase = container.get<GetSessionsUseCase>('GetSessionsUseCase');
  const createSessionUseCase = container.get<CreateSessionUseCase>('CreateSessionUseCase');
  const sendMessageUseCase = container.get<SendMessageUseCase>('SendMessageUseCase');
  const generateTitleUseCase = container.get<GenerateTitleUseCase>('GenerateTitleUseCase');
  const deleteSessionUseCase = container.get<DeleteSessionUseCase>('DeleteSessionUseCase');
  const updateSessionUseCase = container.get<UpdateSessionUseCase>('UpdateSessionUseCase');

  const [sessions, setSessions] = useState<ChatSession[]>(() => getSessionsUseCase.execute());
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const initialSessions = getSessionsUseCase.execute();
    return initialSessions.length > 0 ? initialSessions[0].id : null;
  });
  const [loading, setLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const initializeSessions = async () => {
      if (sessions.length > 0) {
        const chatRepo = container.get('ChatRepository') as { createSession: () => Promise<string> };
        const storageRepo = container.get('SessionStorageRepository') as { 
          getBackendSessionMapping: () => Record<string, string>;
          saveBackendSessionMapping: (mapping: Record<string, string>) => void;
        };
        
        const backendMapping = storageRepo.getBackendSessionMapping();
        const sessionPromises = sessions.map(async (session) => {
          if (!backendMapping[session.id]) {
            try {
              const newBackendSessionId = await chatRepo.createSession();
              backendMapping[session.id] = newBackendSessionId;
            } catch (error) {
              console.error(`Failed to create backend session for ${session.id}:`, error);
            }
          }
        });
        
        await Promise.all(sessionPromises);
        storageRepo.saveBackendSessionMapping(backendMapping);
        return;
      }
      
      const newSession = await createSessionUseCase.execute();
      setSessions([newSession]);
      setActiveSessionId(newSession.id);
    };

    initializeSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createNewSession = useCallback(async () => {
    try {
      const newSession = await createSessionUseCase.execute();
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  }, [createSessionUseCase]);

  const switchSession = useCallback((sessionId: string) => {
    if (loading) {
      abortControllerRef.current?.abort();
      setLoading(false);
    }
    setActiveSessionId(sessionId);
  }, [loading]);

  const deleteSession = useCallback((sessionId: string) => {
    deleteSessionUseCase.execute(sessionId);
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    
    if (activeSessionId === sessionId) {
      const remainingSessions = sessions.filter(s => s.id !== sessionId);
      if (remainingSessions.length > 0) {
        setActiveSessionId(remainingSessions[0].id);
      } else {
        createNewSession();
      }
    }
  }, [deleteSessionUseCase, activeSessionId, sessions, createNewSession]);

  const updateSession = useCallback((sessionId: string, updates: Partial<ChatSession>) => {
    updateSessionUseCase.execute(sessionId, updates);
    setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, ...updates, updatedAt: new Date() } : s));
  }, [updateSessionUseCase]);

  const sendMessage = useCallback(async (content: string, files?: File[]) => {
    if (!activeSessionId || (!content.trim() && (!files || files.length === 0))) {
      return;
    }

    const isNewConversation = sessions.find(s => s.id === activeSessionId)?.messages.length === 1;
    
    const userMessage: Message = {
      id: uuidv4(),
      content,
      role: 'user',
      timestamp: new Date()
    };

    setSessions(prev => {
      const updated = prev.map(session => {
        if (session.id === activeSessionId) {
          const updatedSession = {
            ...session,
            messages: [...session.messages, userMessage],
            updatedAt: new Date(),
          };
          updateSessionUseCase.execute(session.id, updatedSession);
          return updatedSession;
        }
        return session;
      });
      return updated;
    });
    
    setLoading(true);
    abortControllerRef.current = new AbortController();

    try {
      const { botMessage } = await sendMessageUseCase.execute(
        activeSessionId,
        content,
        abortControllerRef.current.signal
      );

      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id === activeSessionId) {
            const updatedSession = {
              ...session,
              messages: [...session.messages, botMessage],
              updatedAt: new Date(),
            };
            updateSessionUseCase.execute(session.id, updatedSession);
            return updatedSession;
          }
          return session;
        });
        return updated;
      });

      if (isNewConversation && content.trim()) {
        const newTitle = await generateTitleUseCase.execute(content);
        updateSession(activeSessionId, { title: newTitle });
      }
    } catch (error: unknown) {
      const err = error as ApiError;
      
      if (err.message !== 'REQUEST_ABORTED') {
        const errorMessage = getErrorMessage(err);
        
        // Adiciona erro na mensagem do usuário ao invés de criar nova mensagem
        const canRetryAt = err.retryAfter 
          ? new Date(Date.now() + err.retryAfter * 1000)
          : undefined;
          
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === userMessage.id) {
                  return {
                    ...msg,
                    error: {
                      message: errorMessage,
                      retryAfter: err.retryAfter,
                      canRetry: err.type === 'QUOTA_ERROR' || err.type === 'NETWORK_ERROR',
                      canRetryAt,
                    }
                  };
                }
                return msg;
              });
              
              const updatedSession = {
                ...session,
                messages: updatedMessages,
                updatedAt: new Date(),
              };
              updateSessionUseCase.execute(session.id, updatedSession);
              return updatedSession;
            }
            return session;
          });
          return updated;
        });
        
        throw err;
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [activeSessionId, sessions, sendMessageUseCase, generateTitleUseCase, updateSession, updateSessionUseCase]);

  const retryMessage = useCallback(async (messageId: string) => {
    if (!activeSessionId || loading) return;
    
    const session = sessions.find(s => s.id === activeSessionId);
    if (!session) return;
    
    const messageToRetry = session.messages.find(m => m.id === messageId);
    if (!messageToRetry || messageToRetry.role !== 'user') return;
    
    // Não remove mensagens, apenas limpa o erro e faz o reenvio
    setLoading(true);
    abortControllerRef.current = new AbortController();

    try {
      const { botMessage } = await sendMessageUseCase.execute(
        activeSessionId,
        messageToRetry.content,
        abortControllerRef.current.signal
      );

      // Remove erro e adiciona resposta do bot
      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id === activeSessionId) {
            // Remove o erro da mensagem que tinha erro
            const messagesWithoutError = session.messages.map(msg => {
              if (msg.id === messageId) {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const { error, ...rest } = msg;
                return rest;
              }
              return msg;
            });
            
            // Adiciona a resposta do bot
            const updatedSession = {
              ...session,
              messages: [...messagesWithoutError, botMessage],
              updatedAt: new Date(),
            };
            updateSessionUseCase.execute(session.id, updatedSession);
            return updatedSession;
          }
          return session;
        });
        return updated;
      });
    } catch (error: unknown) {
      const err = error as ApiError;
      
      if (err.message !== 'REQUEST_ABORTED') {
        const errorMessage = getErrorMessage(err);
        const canRetryAt = err.retryAfter 
          ? new Date(Date.now() + err.retryAfter * 1000)
          : undefined;
        
        // Adiciona erro novamente na mesma mensagem
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === messageId) {
                  return {
                    ...msg,
                    error: {
                      message: errorMessage,
                      retryAfter: err.retryAfter,
                      canRetry: err.type === 'QUOTA_ERROR' || err.type === 'NETWORK_ERROR',
                      canRetryAt,
                    }
                  };
                }
                return msg;
              });
              
              const updatedSession = {
                ...session,
                messages: updatedMessages,
                updatedAt: new Date(),
              };
              updateSessionUseCase.execute(session.id, updatedSession);
              return updatedSession;
            }
            return session;
          });
          return updated;
        });
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [activeSessionId, sessions, loading, sendMessageUseCase, updateSessionUseCase]);

  const abortMessage = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
    }
  }, []);

  const getActiveSessionStats = useCallback(async (): Promise<SessionStats | null> => {
    if (!activeSessionId) return null;
    
    const chatRepo = container.get('ChatRepository') as { getSessionStats: (sessionId: string) => Promise<SessionStats | null> };
    const storageRepo = container.get('SessionStorageRepository') as { getBackendSessionMapping: () => Record<string, string> };
    const backendMapping = storageRepo.getBackendSessionMapping();
    const backendSessionId = backendMapping[activeSessionId];
    
    if (!backendSessionId) return null;
    
    try {
      return await chatRepo.getSessionStats(backendSessionId);
    } catch (error) {
      console.error('Failed to get session stats:', error);
      return null;
    }
  }, [activeSessionId, container]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  return {
    sessions,
    activeSession,
    loading,
    createNewSession,
    switchSession,
    deleteSession,
    updateSession,
    sendMessage,
    retryMessage,
    abortMessage,
    getActiveSessionStats,
  };
};

function getErrorMessage(error: ApiError): string {
  if (error.type === 'QUOTA_ERROR') {
    switch (error.errorCode) {
      case 'QUOTA_EXCEEDED':
        // Se tem retryAfter em minutos, mostra isso. Senão, mostra 24h
        if (error.retryAfter && error.retryAfter < 3600) {
          const minutes = Math.ceil(error.retryAfter / 60);
          return `Limite de uso diário da API atingido. O serviço estará disponível novamente em ${minutes} minuto${minutes > 1 ? 's' : ''}.`;
        }
        return `Limite de uso diário da API atingido. O serviço estará disponível novamente em 24 horas.`;
      case 'RATE_LIMIT':
        if (error.retryAfter) {
          const minutes = Math.ceil(error.retryAfter / 60);
          return `Muitas requisições em pouco tempo. Aguarde ${minutes} minuto${minutes > 1 ? 's' : ''} antes de tentar novamente.`;
        }
        return `Muitas requisições em pouco tempo. Aguarde um momento antes de tentar novamente.`;
      case 'RESOURCE_EXHAUSTED':
        return `Recursos temporariamente indisponíveis. Tente novamente em alguns minutos.`;
      case 'API_KEY_INVALID':
        return `Problema de autenticação com o serviço. Entre em contato com o suporte.`;
      case 'BILLING_NOT_ENABLED':
        return `Serviço temporariamente indisponível por questões de cobrança. Entre em contato com o suporte.`;
      case 'TIMEOUT':
        return `Timeout na requisição. Tente uma pergunta mais simples ou aguarde um momento.`;
      default:
        if (error.retryAfter) {
          const minutes = Math.ceil(error.retryAfter / 60);
          return `Serviço temporariamente indisponível. Tente novamente em ${minutes} minuto${minutes > 1 ? 's' : ''}.`;
        }
        return `Serviço temporariamente indisponível. Tente novamente em alguns minutos.`;
    }
  }
  
  return error.message || 'Desculpe, ocorreu um erro inesperado. Tente novamente.';
}