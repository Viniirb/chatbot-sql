import type { ExportRequest, ExportResponse } from '../value-objects/export-format';

export interface IExportRepository {
  exportSession(request: ExportRequest): Promise<ExportResponse>;
}
