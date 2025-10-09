import type { ExportFormat, ExportResponse } from '../value-objects/export-format';

export interface IExportRepository {
  exportSession(sessionId: string, format: ExportFormat): Promise<ExportResponse>;
}
