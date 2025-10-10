export type ExportFormat = 'pdf' | 'json' | 'txt';

export interface ExportSessionPayload {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Array<{
    id: string;
    content: string;
    role: 'user' | 'assistant';
    timestamp: string;
  }>;
}

export interface ExportRequest {
  format: ExportFormat;
  session: ExportSessionPayload;
}

export interface ExportResponse {
  blob: Blob;
  filename: string;
}
