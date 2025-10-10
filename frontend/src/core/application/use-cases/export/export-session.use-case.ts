import type { IExportRepository } from '../../../domain/repositories/export-repository.interface';
import type { ExportFormat, ExportRequest, ExportResponse } from '../../../domain/value-objects/export-format';

export interface IExportSessionUseCase {
  execute(request: ExportRequest): Promise<ExportResponse>;
}

export class ExportSessionUseCase implements IExportSessionUseCase {
  private exportRepository: IExportRepository;

  constructor(exportRepository: IExportRepository) {
    this.exportRepository = exportRepository;
  }

  async execute(request: ExportRequest): Promise<ExportResponse> {
    if (!request || !request.session) {
      throw new Error('Dados da sessão são obrigatórios para exportação');
    }

    const validFormats: ExportFormat[] = ['pdf', 'json', 'txt'];
    if (!validFormats.includes(request.format)) {
      throw new Error('Formato inválido. Use: pdf, json, txt');
    }

    return await this.exportRepository.exportSession(request);
  }
}
