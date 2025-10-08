import type { IChatRepository } from '../../core/domain/repositories';
import type { SessionStats, Message } from '../../core/domain/entities';
import { ApiClient } from '../http/api-client';

interface ApiResponse {
  answer: string;
}

interface ApiTitleResponse {
  title: string;
}

interface SessionResponse {
  session_id: string;
}

interface SessionStatsResponse {
  session_id: string;
  created_at: number;
  last_activity: number;
  message_count: number;
  has_active_dataset: boolean;
  active_dataset_info: unknown | null;
  session_exists: boolean;
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
        // Converte timestamp Unix para Date
        const createdAt = new Date(response.created_at * 1000);
        const lastActivity = new Date(response.last_activity * 1000);
        
        return {
          sessionId: response.session_id,
          totalMessages: response.message_count,
          // Como o backend não retorna separado, vamos estimar baseado na contagem total
          userMessages: Math.ceil(response.message_count / 2),
          assistantMessages: Math.floor(response.message_count / 2),
          createdAt,
          lastActivity,
          contextLength: 0, // Backend não fornece, pode ser calculado se necessário
          tokenUsage: undefined, // Backend não fornece ainda
        };
      }
      
      return null;
    } catch (error) {
      console.error('Erro ao obter estatísticas da sessão:', error);
      return null;
    }
  }

  async sendMessage(query: string, conversationHistory: Message[], sessionId?: string, signal?: AbortSignal): Promise<string> {
    // Filtra apenas mensagens do usuário e formata como string
    const prompt = conversationHistory
      .filter(msg => msg.role === 'user')
      .map(msg => msg.content)
      .join('\n');

    const response = await this.apiClient.post<ApiResponse>(
      '/ask',
      { 
        query, 
        session_id: sessionId,
        prompt: prompt || undefined // Envia apenas o histórico de mensagens do usuário
      },
      signal
    );
    return response.answer;
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