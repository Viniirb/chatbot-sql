import axios from 'axios';
import type { IExportRepository } from '../../core/domain/repositories/export-repository.interface';
import type { ExportRequest, ExportResponse } from '../../core/domain/value-objects/export-format';

export class ExportRepository implements IExportRepository {
  private readonly baseURL = 'http://127.0.0.1:8000';

  async exportSession(request: ExportRequest): Promise<ExportResponse> {
    try {
      const response = await axios.post(
        `${this.baseURL}/sessions/${encodeURIComponent(request.session.id)}/export`,
        request,
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
        : `chat-${request.session.id}.${request.format}`;

      return {
        blob: response.data,
        filename,
      };
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        const status = error.response.status;

        if (status === 404) {
          throw new Error('Sessão não encontrada no servidor');
        }

        if (status === 400) {
          const msg = error.response.data?.message || 'Requisição inválida';
          throw new Error(msg);
        }

        if (status >= 500) {
          throw new Error('Erro interno do servidor ao exportar');
        }
      }

      throw new Error('Erro ao exportar sessão. Tente novamente.');
    }
  }
}
