import type { IChatRepository } from '../../core/domain/repositories';
import type { SessionStats, Message } from '../../core/domain/entities';
import { ApiClient } from '../http/api-client';
import { v4 as uuidv4 } from 'uuid';

interface ApiResponse {
  answer: string;
}

interface ApiTitleResponse {
  title: string;
}

interface SessionResponse {
  session_id: string;
}

interface AgentInfo {
  model: string;
  temperature: number;
  max_tokens: number;
  provider: string;
}

interface SessionStatsResponse {
  session_id: string;
  message_count: number;
  query_count: number;
  created_at: string;
  session_exists: boolean;
  agent?: AgentInfo;
  message?: string;
}

export class ChatRepository implements IChatRepository {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  async createSession(): Promise<string> {
    try {
      const response = await this.apiClient.post<SessionResponse>('/sessions');
      return response.session_id;
    } catch (error) {
      console.error('Erro ao criar sessão:', error);
      throw new Error('Falha ao criar sessão de chat');
    }
  }

  async getSessionStats(sessionId: string): Promise<SessionStats | null> {
    try {
      const response = await this.apiClient.get<SessionStatsResponse>(`/sessions/${sessionId}/stats`);
      
      if (response && response.session_exists) {
        return {
          sessionId: response.session_id,
          messageCount: response.message_count,
          queryCount: response.query_count,
          createdAt: new Date(response.created_at),
          sessionExists: response.session_exists,
          agent: response.agent,
          message: response.message,
        };
      }
      
      return null;
    } catch (error) {
      console.error('Erro ao obter estatísticas da sessão:', error);
      return null;
    }
  }

  async sendMessage(query: string, conversationHistory: Message[], sessionId?: string, signal?: AbortSignal, clientMessageId?: string): Promise<{ answer: string; requestId: string }> {
    const prompt = conversationHistory
      .filter(msg => msg.role === 'user')
      .map(msg => msg.content)
      .join('\n');

    const requestId = uuidv4();

    const headers: Record<string, string> = {
      'X-Request-ID': requestId
    };

    if (clientMessageId) {
      headers['X-Client-Message-Id'] = clientMessageId;
    }

    const response = await this.apiClient.post<ApiResponse>(
      '/ask',
      { 
        query, 
        session_id: sessionId,
        prompt: prompt || undefined,
        client_message_id: clientMessageId
      },
      signal,
      headers
    );
    return { answer: response.answer, requestId };
  }

  async cancelRequest(requestId: string): Promise<boolean> {
    try {
      await this.apiClient.post(`/requests/${encodeURIComponent(requestId)}/cancel`, {});
      return true;
    } catch (error) {
      console.warn('Failed to send cancel request to server', error);
      return false;
    }
  }

  async generateTitle(prompt: string): Promise<string> {
    try {
      const response = await this.apiClient.post<ApiTitleResponse>(
        '/generate-title',
        { prompt }
      );
      return response.title;
    } catch (error) {
      console.error('Erro ao gerar título:', error);
      return 'Conversa';
    }
  }
}