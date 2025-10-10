import { useState, useCallback } from 'react';
import type { ExportFormat, ExportRequest } from '../../core/domain/value-objects/export-format';
import type { ChatSession, Message } from '../../core/domain/entities';
import type { IExportSessionUseCase } from '../../core/application/use-cases/export';
import { DIContainer } from '../../infrastructure/di/container';

export interface UseExportReturn {
  exporting: boolean;
  exportSession: (sessionId: string, format: ExportFormat) => Promise<void>;
  downloadFile: (blob: Blob, filename: string) => void;
}

export const useExport = (): UseExportReturn => {
  const [exporting, setExporting] = useState(false);
  const container = DIContainer.getInstance();
  const exportSessionUseCase = container.get<IExportSessionUseCase>('ExportSessionUseCase');
  const storageRepo = container.get('SessionStorageRepository') as { getSessions: () => Record<string, ChatSession> };

  const downloadFile = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, []);

  const exportSession = useCallback(
    async (sessionId: string, format: ExportFormat) => {
      setExporting(true);
      try {
        const sessions = storageRepo.getSessions();
        const session = sessions[sessionId];
        if (!session) throw new Error('Sessão não encontrada localmente');

        const payload = {
          id: session.id,
          title: session.title,
          createdAt: session.createdAt instanceof Date ? session.createdAt.toISOString() : new Date(session.createdAt).toISOString(),
          updatedAt: session.updatedAt instanceof Date ? session.updatedAt.toISOString() : new Date(session.updatedAt).toISOString(),
          messages: session.messages.map((m: Message) => ({
            id: m.id,
            content: m.content,
            role: m.role,
            timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : new Date(m.timestamp).toISOString(),
          }))
        };

        const request: ExportRequest = {
          format,
          session: payload,
        };

        const { blob, filename } = await exportSessionUseCase.execute(request);
        downloadFile(blob, filename);
      } catch (error) {
        console.error('Erro ao exportar sessão:', error);
        throw error;
      } finally {
        setExporting(false);
      }
    },
    [exportSessionUseCase, downloadFile, storageRepo]
  );

  return {
    exporting,
    exportSession,
    downloadFile,
  };
};
