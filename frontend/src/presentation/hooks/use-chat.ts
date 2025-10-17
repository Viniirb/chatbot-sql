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
  const currentRequestIdRef = useRef<string | null>(null);
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
  }, [container, createSessionUseCase, sessions]);

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
          const updatedMessages = [...session.messages, userMessage];
          // Calcula queryCount dinamicamente
          const newQueryCount = updatedMessages.filter(m => m.role === 'user' && m.content.toLowerCase().includes('select')).length;
          const updatedSession = {
            ...session,
            messages: updatedMessages,
            updatedAt: new Date(),
            queryCount: newQueryCount,
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
      const { botMessage, requestId } = await sendMessageUseCase.execute(
        activeSessionId,
        content,
        abortControllerRef.current.signal,
        userMessage.id
      );

      currentRequestIdRef.current = requestId || null;

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
    } catch (rawError: unknown) {
      const err = rawError as ApiError;
      // Detecta erro de rede/fetch
      if (err.message === 'REQUEST_ABORTED') {
        // Marca a mensagem local como abortada para permitir reenvio
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === userMessage.id) {
                  return {
                    ...msg,
                    error: {
                      message: 'Requisição cancelada pelo usuário',
                      canRetry: true
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
        // Also attempt to inform backend to cancel the running work
        try {
          const chatRepo = container.get('ChatRepository') as { cancelRequest: (id: string) => Promise<boolean> };
          if (currentRequestIdRef.current) {
            chatRepo.cancelRequest(currentRequestIdRef.current).catch(() => {});
          }
        } catch {
          // ignore
        }
  } else if (rawError instanceof TypeError || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        // Erro de conexão
        const networkError: ApiError = {
          type: 'NETWORK_ERROR',
          errorCode: undefined,
          message: 'Falha de conexão com o servidor. Tente novamente mais tarde.',
        };
        const errorMessage = getErrorMessage(networkError);
  // atribuindo erro de rede à mensagem
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              // Se não existe mensagem do usuário, adiciona uma nova bolha de erro
              const hasUserMessage = session.messages.some(msg => msg.id === userMessage.id);
              let updatedMessages;
              if (hasUserMessage) {
                updatedMessages = session.messages.map(msg => {
                  if (msg.id === userMessage.id) {
                    // atualizando mensagem existente com erro
                    return {
                      ...msg,
                      error: {
                        message: errorMessage,
                        canRetry: true,
                      }
                    };
                  }
                  return msg;
                });
              } else {
                // adicionando nova mensagem de erro
                updatedMessages = [
                  ...session.messages,
                  {
                    ...userMessage,
                    error: {
                      message: errorMessage,
                      canRetry: true,
                    }
                  }
                ];
              }
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
      } else {
        const errorMessage = getErrorMessage(err);
        const canRetryAt = err.retryAfter 
          ? new Date(Date.now() + err.retryAfter * 1000)
          : undefined;
  // atribuindo erro à mensagem
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              let foundUserMsg = false;
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === userMessage.id) {
                  // atualizando mensagem existente com erro
                  foundUserMsg = true;
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
              // Se não encontrou a mensagem do usuário, cria uma bolha de erro do assistente
              let finalMessages = updatedMessages;
              if (!foundUserMsg) {
                // adicionando bolha de erro do assistente
                finalMessages = [
                  ...updatedMessages,
                  {
                    id: Math.random().toString(36).slice(2),
                    content: errorMessage,
                    role: 'assistant',
                    timestamp: new Date(),
                    error: {
                      message: errorMessage,
                      canRetry: false,
                    }
                  }
                ];
              }
              const updatedSession = {
                ...session,
                messages: finalMessages,
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
      currentRequestIdRef.current = null;
    }
  }, [activeSessionId, sessions, sendMessageUseCase, generateTitleUseCase, updateSession, updateSessionUseCase, container]);


  const retryMessage = useCallback(async (messageId: string) => {
    if (!activeSessionId || loading) return;
    
    const session = sessions.find(s => s.id === activeSessionId);
    if (!session) return;
    
    const messageToRetry = session.messages.find(m => m.id === messageId);
    if (!messageToRetry || messageToRetry.role !== 'user') return;
    
    setLoading(true);
    abortControllerRef.current = new AbortController();

    setSessions(prev => {
      const updated = prev.map(session => {
        if (session.id === activeSessionId) {
          const messagesCleared = session.messages.map(msg => {
            if (msg.id === messageId) {
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              const { error, ...rest } = msg;
              const newMetadata = { ...(rest.metadata || {}), retrying: true };
              return { ...rest, metadata: newMetadata } as Message;
            }
            return msg;
          });
          const updatedSession = {
            ...session,
            messages: messagesCleared,
            updatedAt: new Date(),
          };
          updateSessionUseCase.execute(session.id, updatedSession);
          return updatedSession;
        }
        return session;
      });
      return updated;
    });

    try {
      const { botMessage, requestId } = await sendMessageUseCase.execute(
        activeSessionId,
        messageToRetry.content,
        abortControllerRef.current.signal,
        messageToRetry.id
      );

      currentRequestIdRef.current = requestId || null;

      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id === activeSessionId) {
            // Clear retrying flag from the retried user message
            const messagesClearedRetry = session.messages.map(m => {
              if (m.id === messageId) {
                const md = { ...(m.metadata || {}) } as Record<string, unknown>;
                delete md.retrying;
                return { ...m, metadata: Object.keys(md).length ? md : undefined };
              }
              return m;
            });

            const updatedSession = {
              ...session,
              messages: [...messagesClearedRetry, botMessage],
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
        // Restore the error on the message if the retry failed and clear retrying flag
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === messageId) {
                  const md = { ...(msg.metadata || {}) } as Record<string, unknown>;
                  delete md.retrying;
                  return {
                    ...msg,
                    metadata: Object.keys(md).length ? md : undefined,
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
      } else {
        // If retry was aborted, restore the error state and clear retrying flag
        setSessions(prev => {
          const updated = prev.map(session => {
            if (session.id === activeSessionId) {
              const updatedMessages = session.messages.map(msg => {
                if (msg.id === messageId) {
                  const md = { ...(msg.metadata || {}) } as Record<string, unknown>;
                  delete md.retrying;
                  return {
                    ...msg,
                    metadata: Object.keys(md).length ? md : undefined,
                    error: {
                      message: 'Requisição cancelada pelo usuário',
                      canRetry: true
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
      // Optimistically mark current user message as canceled so UI can show retry
      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id === activeSessionId) {
            const updatedMessages = session.messages.map(msg => {
              // find the most recent user message without assistant reply
              return {
                ...msg
              };
            });
            // Attempt to set the last user message as canceled
            for (let i = updatedMessages.length - 1; i >= 0; i--) {
              const m = updatedMessages[i];
              if (m.role === 'user' && !m.error) {
                updatedMessages[i] = {
                  ...m,
                  error: { message: 'Requisição cancelada pelo usuário', canRetry: true }
                } as Message;
                break;
              }
            }
            const updatedSession = { ...session, messages: updatedMessages, updatedAt: new Date() };
            updateSessionUseCase.execute(session.id, updatedSession);
            return updatedSession;
          }
          return session;
        });
        return updated;
      });

      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);

      // Try to inform backend about cancellation
      try {
        const chatRepo = container.get('ChatRepository') as { cancelRequest: (id: string) => Promise<boolean> };
        if (currentRequestIdRef.current) {
          chatRepo.cancelRequest(currentRequestIdRef.current).catch(() => {});
        }
      } catch {
        // ignore
      }
      currentRequestIdRef.current = null;
    }
  }, [activeSessionId, container, updateSessionUseCase]);

  const getActiveSessionStats = useCallback(async (): Promise<SessionStats | null> => {
    if (!activeSessionId) return null;

    const chatRepo = container.get('ChatRepository') as { getSessionStats: (sessionId: string) => Promise<SessionStats | null> };
    const storageRepo = container.get('SessionStorageRepository') as { getBackendSessionMapping: () => Record<string, string>; getSessions: () => Record<string, ChatSession> };
    const backendMapping = storageRepo.getBackendSessionMapping();
    const backendSessionId = backendMapping[activeSessionId];

    if (!backendSessionId) return null;

    try {
      const stats = await chatRepo.getSessionStats(backendSessionId);
      // Se stats retornam zeradas, tenta sincronizar com localStorage
      if (
        stats &&
        stats.messageCount === 0 &&
        stats.queryCount === 0 &&
        stats.message === 'Nova sessão criada automaticamente'
      ) {
        // Busca sessão local
        const localSessions = storageRepo.getSessions();
        const localSession = localSessions[activeSessionId];
        if (localSession) {
          const response = await fetch(`http://127.0.0.1:8000/sessions/${backendSessionId}/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id: localSession.id,
              title: localSession.title,
              createdAt: localSession.createdAt instanceof Date ? localSession.createdAt.toISOString() : localSession.createdAt,
              updatedAt: localSession.updatedAt instanceof Date ? localSession.updatedAt.toISOString() : localSession.updatedAt,
              messages: localSession.messages.map(m => ({
                ...m,
                timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : m.timestamp
              })),
              queryCount: localSession.messages.filter(m => m.role === 'user' && m.content.toLowerCase().includes('select')).length
            })
          });
          if (response.ok) {
            let synced = null;
            try {
              synced = await response.json();
            } catch {
              synced = null;
            }
            if (!synced) {
              // Retorno seguro se o backend não enviar JSON
              return {
                sessionId: backendSessionId,
                messageCount: localSession.messages.length,
                queryCount: 0,
                createdAt: new Date(),
                sessionExists: true,
                agent: stats.agent,
                message: 'Sessão sincronizada (sem resposta detalhada do backend)'
              };
            }
            // Fallback para sessionId/session_id, previne crash se resposta for nula
            return {
              sessionId: synced.sessionId || synced.session_id || backendSessionId,
              messageCount: synced.messageCount || synced.message_count || localSession.messages.length,
              queryCount: synced.queryCount || synced.query_count || 0,
              createdAt: synced.createdAt ? new Date(synced.createdAt) : (synced.created_at ? new Date(synced.created_at) : new Date()),
              sessionExists: true,
              agent: stats.agent,
              message: 'Sessão sincronizada com sucesso'
            };
          }
        }
      }
      return stats;
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
  
  // Tratamento especial para erro de tokens do modelo
  if (error.message && error.message.includes('MAX_TOKENS')) {
    return 'A resposta foi interrompida porque atingiu o limite máximo de tokens do modelo. Tente uma pergunta mais curta ou divida sua consulta.';
  }
  return error.message || 'Desculpe, ocorreu um erro inesperado. Tente novamente.';
}