import { useState, useCallback } from 'react';
import type { ExportFormat } from '../../core/domain/value-objects/export-format';
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
        const { blob, filename } = await exportSessionUseCase.execute(sessionId, format);
        downloadFile(blob, filename);
      } catch (error) {
        console.error('Erro ao exportar sessão:', error);
        throw error;
      } finally {
        setExporting(false);
      }
    },
    [exportSessionUseCase, downloadFile]
  );

  return {
    exporting,
    exportSession,
    downloadFile,
  };
};
