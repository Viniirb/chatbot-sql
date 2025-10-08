import type { ISessionStorageRepository } from '../../core/domain/repositories';
import type { ChatSession } from '../../core/domain/entities';

const SESSIONS_KEY = 'chat_sessions';
const BACKEND_MAPPING_KEY = 'backend_session_mapping';

export class SessionStorageRepository implements ISessionStorageRepository {
  getSessions(): Record<string, ChatSession> {
    try {
      const stored = localStorage.getItem(SESSIONS_KEY);
      if (!stored) return {};
      
      const parsed = JSON.parse(stored);
      
      return Object.entries(parsed).reduce((acc, [id, session]) => {
        const s = session as {
          id: string;
          title: string;
          isPinned: boolean;
          createdAt: string | Date;
          updatedAt: string | Date;
          messages: Array<{
            id: string;
            content: string;
            role: 'user' | 'assistant';
            timestamp: string | Date;
          }>;
        };
        
        const createdAt = s.createdAt instanceof Date ? s.createdAt : new Date(s.createdAt);
        const updatedAt = s.updatedAt instanceof Date ? s.updatedAt : new Date(s.updatedAt);
        
        acc[id] = {
          ...s,
          createdAt: isNaN(createdAt.getTime()) ? new Date() : createdAt,
          updatedAt: isNaN(updatedAt.getTime()) ? new Date() : updatedAt,
          messages: s.messages.map((msg) => {
            const timestamp = msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp);
            return {
              ...msg,
              timestamp: isNaN(timestamp.getTime()) ? new Date() : timestamp,
            };
          }),
        };
        return acc;
      }, {} as Record<string, ChatSession>);
    } catch (error) {
      console.error('Failed to load sessions from localStorage:', error);
      return {};
    }
  }

  saveSession(session: ChatSession): void {
    try {
      const sessions = this.getSessions();
      sessions[session.id] = session;
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.error('Failed to save session to localStorage:', error);
    }
  }

  deleteSession(sessionId: string): void {
    try {
      const sessions = this.getSessions();
      delete sessions[sessionId];
      
      if (Object.keys(sessions).length > 0) {
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
      } else {
        localStorage.removeItem(SESSIONS_KEY);
      }
    } catch (error) {
      console.error('Failed to delete session from localStorage:', error);
    }
  }

  clearAllSessions(): void {
    try {
      localStorage.removeItem(SESSIONS_KEY);
      localStorage.removeItem(BACKEND_MAPPING_KEY);
    } catch (error) {
      console.error('Failed to clear sessions from localStorage:', error);
    }
  }

  getBackendSessionMapping(): Record<string, string> {
    try {
      const stored = localStorage.getItem(BACKEND_MAPPING_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.error('Failed to load backend session mapping:', error);
      return {};
    }
  }

  saveBackendSessionMapping(mapping: Record<string, string>): void {
    try {
      if (Object.keys(mapping).length > 0) {
        localStorage.setItem(BACKEND_MAPPING_KEY, JSON.stringify(mapping));
      } else {
        localStorage.removeItem(BACKEND_MAPPING_KEY);
      }
    } catch (error) {
      console.error('Failed to save backend session mapping:', error);
    }
  }
}