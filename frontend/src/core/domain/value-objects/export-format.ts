export type ExportFormat = 'pdf' | 'json' | 'txt';

export interface ExportRequest {
  sessionId: string;
  format: ExportFormat;
}

export interface ExportResponse {
  blob: Blob;
  filename: string;
}
