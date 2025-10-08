import type { IServerStatusRepository } from '../../core/domain/repositories';
import { ApiClient } from '../http/api-client';

interface ServerStatusResponse {
  status: 'ok' | 'error';
  service: string;
  dbStatus: 'connected' | 'erro_db' | 'falha_import';
}

export class ServerStatusRepository implements IServerStatusRepository {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  async getServerStatus(): Promise<{
    status: 'ok' | 'error';
    service: string;
    dbStatus: 'connected' | 'erro_db' | 'falha_import';
  } | null> {
    try {
      const response = await this.apiClient.get<ServerStatusResponse>('/status');
      return {
        status: response.status,
        service: response.service,
        dbStatus: response.dbStatus,
      };
    } catch (error) {
      console.error('Erro ao verificar status do servidor:', error);
      return {
        status: 'error',
        service: 'Offline',
        dbStatus: 'falha_import',
      };
    }
  }
}