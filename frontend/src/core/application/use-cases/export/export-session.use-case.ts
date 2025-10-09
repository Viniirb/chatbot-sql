import type { IExportRepository } from '../../../domain/repositories/export-repository.interface';
import type { ExportFormat, ExportResponse } from '../../../domain/value-objects/export-format';

export interface IExportSessionUseCase {
  execute(sessionId: string, format: ExportFormat): Promise<ExportResponse>;
}

export class ExportSessionUseCase implements IExportSessionUseCase {
  private exportRepository: IExportRepository;

  constructor(exportRepository: IExportRepository) {
    this.exportRepository = exportRepository;
  }

  async execute(sessionId: string, format: ExportFormat): Promise<ExportResponse> {
    if (!sessionId) {
      throw new Error('ID da sessão é obrigatório');
    }

    const validFormats: ExportFormat[] = ['pdf', 'json', 'txt'];
    if (!validFormats.includes(format)) {
      throw new Error('Formato inválido. Use: pdf, json, txt');
    }

    return await this.exportRepository.exportSession(sessionId, format);
  }
}
