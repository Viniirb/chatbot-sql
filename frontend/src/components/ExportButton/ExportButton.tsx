import { useState } from 'react';
import { Download, FileText, FileJson, FileSpreadsheet, File } from 'lucide-react';
import type { ExportFormat } from '../../core/domain/value-objects/export-format';
import { useExport } from '../../presentation/hooks/use-export';

interface ExportButtonProps {
  backendSessionId?: string;
  className?: string;
}

const exportOptions = [
  { value: 'pdf', label: 'PDF', icon: FileText, color: 'text-red-500' },
  { value: 'json', label: 'JSON', icon: FileJson, color: 'text-blue-500' },
  { value: 'txt', label: 'TXT', icon: File, color: 'text-gray-500' },
  { value: 'excel', label: 'Excel', icon: FileSpreadsheet, color: 'text-green-500' },
] as const;

export const ExportButton = ({ backendSessionId, className = '' }: ExportButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { exporting, exportSession } = useExport();

  const handleExport = async (format: ExportFormat) => {
    if (!backendSessionId) {
      setError('Sessão não sincronizada com o backend');
      setTimeout(() => setError(null), 3000);
      return;
    }

    setError(null);
    setIsOpen(false);

    try {
      await exportSession(backendSessionId, format);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao exportar';
      setError(errorMessage);
      setTimeout(() => setError(null), 5000);
    }
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={exporting}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-white font-medium text-sm"
        title="Exportar chat"
      >
        <Download className="w-4 h-4" />
        {exporting ? 'Exportando...' : 'Exportar'}
      </button>

      {isOpen && !exporting && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 z-20 overflow-hidden">
            <div className="py-1">
              {exportOptions.map((option) => {
                const Icon = option.icon;
                return (
                  <button
                    key={option.value}
                    onClick={() => handleExport(option.value as ExportFormat)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left"
                  >
                    <Icon className={`w-4 h-4 ${option.color}`} />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      Exportar como {option.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}

      {error && (
        <div className="absolute right-0 mt-2 w-64 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 z-20">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
};
