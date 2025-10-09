import axios from 'axios';
import type { IExportRepository } from '../../core/domain/repositories/export-repository.interface';
import type { ExportFormat, ExportResponse } from '../../core/domain/value-objects/export-format';

export class ExportRepository implements IExportRepository {
  private readonly baseURL = 'http://127.0.0.1:8000';

  async exportSession(sessionId: string, format: ExportFormat): Promise<ExportResponse> {
    try {
      const response = await axios.post(
        `${this.baseURL}/sessions/${sessionId}/export`,
        { format },
        {
          responseType: 'blob',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const contentDisposition = response.headers['content-disposition'];
      const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
      const filename = filenameMatch 
        ? filenameMatch[1] 
        : `chat-${sessionId}.${format}`;

      return {
        blob: response.data,
        filename,
      };
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        const status = error.response.status;
        
        if (status === 404) {
          throw new Error('Sessão não encontrada');
        }
        
        if (status === 400) {
          throw new Error('Formato de exportação inválido');
        }
        
        if (status >= 500) {
          throw new Error('Erro interno do servidor ao exportar');
        }
      }
      
      throw new Error('Erro ao exportar sessão. Tente novamente.');
    }
  }
}
