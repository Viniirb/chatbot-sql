import type { ChatSession, SessionStats, Message } from '../entities';

export interface IChatRepository {
  createSession(): Promise<string>;
  getSessionStats(sessionId: string): Promise<SessionStats | null>;
  sendMessage(query: string, conversationHistory: Message[], sessionId?: string, signal?: AbortSignal): Promise<string>;
  generateTitle(prompt: string): Promise<string>;
}

export interface ISessionStorageRepository {
  getSessions(): Record<string, ChatSession>;
  saveSession(session: ChatSession): void;
  deleteSession(sessionId: string): void;
  clearAllSessions(): void;
  getBackendSessionMapping(): Record<string, string>;
  saveBackendSessionMapping(mapping: Record<string, string>): void;
}

export interface IServerStatusRepository {
  getServerStatus(): Promise<{
    status: 'ok' | 'error';
    service: string;
    dbStatus: 'connected' | 'erro_db' | 'falha_import';
  } | null>;
}

export interface IQuotaRepository {
  getQuotaStats(): Promise<{
    totalRequests: number;
    successfulRequests: number;
    successRate: number;
    quotaErrorsCount: number;
    recentErrors: Array<{
      errorType: string;
      timestamp: number;
    }>;
  } | null>;
  
  getHealthStatus(): Promise<{
    status: 'ok' | 'error';
    quotaHealth: {
      successRate: number;
      totalRequests: number;
      recentErrors: number;
    };
  } | null>;
}

export * from './export-repository.interface';