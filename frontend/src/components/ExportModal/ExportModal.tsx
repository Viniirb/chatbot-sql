import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, FileJson, File, Download, CheckCircle, Loader2 } from 'lucide-react';
import type { ExportFormat } from '../../core/domain/value-objects/export-format';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (format: ExportFormat) => Promise<void>;
  sessionTitle?: string;
}

const exportOptions = [
  { value: 'pdf', label: 'PDF', icon: FileText, color: 'text-red-500', bgColor: 'bg-red-500/10', description: 'Documento portátil' },
  { value: 'json', label: 'JSON', icon: FileJson, color: 'text-blue-500', bgColor: 'bg-blue-500/10', description: 'Formato estruturado' },
  { value: 'txt', label: 'TXT', icon: File, color: 'text-gray-500', bgColor: 'bg-gray-500/10', description: 'Texto simples' },
] as const;

type ExportState = 'idle' | 'exporting' | 'success' | 'error';

export const ExportModal = ({ isOpen, onClose, onExport, sessionTitle }: ExportModalProps) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat | null>(null);
  const [exportState, setExportState] = useState<ExportState>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleExport = async () => {
    if (!selectedFormat) return;

    setExportState('exporting');
    setErrorMessage('');

    try {
      await onExport(selectedFormat);
      setExportState('success');
      
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (error) {
      setExportState('error');
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao exportar');
    }
  };

  const handleClose = () => {
    if (exportState === 'exporting') return;
    
    setSelectedFormat(null);
    setExportState('idle');
    setErrorMessage('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="absolute inset-0 bg-black/80 backdrop-blur-md"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-md bg-gradient-to-br from-gray-900/95 via-purple-950/30 to-gray-900/95 backdrop-blur-2xl rounded-3xl shadow-2xl shadow-purple-500/20 border border-purple-500/30 overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-purple-500/30 flex items-center justify-between bg-gradient-to-r from-gray-900/50 to-purple-900/30">
            <div>
              <h2 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Exportar Conversa</h2>
              {sessionTitle && (
                <p className="text-sm text-gray-400 mt-0.5">{sessionTitle}</p>
              )}
            </div>
            <button
              onClick={handleClose}
              disabled={exportState === 'exporting'}
              className="text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {exportState === 'idle' && (
              <>
                <p className="text-sm text-gray-400 mb-4">
                  Escolha o formato para exportar a conversa:
                </p>
                <div className="grid grid-cols-3 gap-3 mb-6">
                  {exportOptions.map((option) => {
                    const Icon = option.icon;
                    const isSelected = selectedFormat === option.value;
                    
                    return (
                      <button
                        key={option.value}
                        onClick={() => setSelectedFormat(option.value as ExportFormat)}
                        className={`relative p-5 rounded-2xl border-2 transition-all duration-300 hover:scale-105 ${
                          isSelected
                            ? 'border-purple-500 bg-gradient-to-br from-purple-500/20 to-pink-500/20 shadow-lg shadow-purple-500/30'
                            : 'border-purple-500/20 bg-gray-800/50 backdrop-blur-sm hover:border-purple-500/40 hover:bg-gray-800/70'
                        }`}
                      >
                        <div className="flex flex-col items-center gap-2">
                          <div className={`p-3 rounded-lg ${option.bgColor}`}>
                            <Icon className={`w-6 h-6 ${option.color}`} />
                          </div>
                          <div className="text-center">
                            <div className="font-semibold text-gray-200 text-sm">
                              {option.label}
                            </div>
                            <div className="text-xs text-gray-500">
                              {option.description}
                            </div>
                          </div>
                        </div>
                        {isSelected && (
                          <motion.div
                            layoutId="selected-indicator"
                            className="absolute top-2 right-2 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center"
                          >
                            <CheckCircle size={16} className="text-white" />
                          </motion.div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            {exportState === 'exporting' && (
              <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
                <p className="text-gray-200 font-medium">Gerando exportação...</p>
                <p className="text-sm text-gray-400 mt-1">Por favor, aguarde</p>
              </div>
            )}

            {exportState === 'success' && (
              <div className="flex flex-col items-center justify-center py-8">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                >
                  <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
                </motion.div>
                <p className="text-gray-200 font-medium text-lg">Exportado com sucesso!</p>
                <p className="text-sm text-gray-400 mt-1">O download será iniciado automaticamente</p>
              </div>
            )}

            {exportState === 'error' && (
              <div className="flex flex-col items-center justify-center py-8">
                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-4">
                  <X className="w-8 h-8 text-red-500" />
                </div>
                <p className="text-gray-200 font-medium text-lg">Erro ao exportar</p>
                <p className="text-sm text-red-400 mt-2 text-center">{errorMessage}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          {exportState === 'idle' && (
            <div className="px-6 py-5 border-t border-purple-500/30 bg-gradient-to-r from-gray-900/50 to-purple-900/30 backdrop-blur-xl flex justify-end gap-3">
              <button
                onClick={handleClose}
                className="px-6 py-2.5 rounded-xl text-gray-300 bg-gray-800/80 backdrop-blur-sm border border-gray-700 hover:text-white hover:bg-gray-700 hover:border-gray-600 transition-all duration-300 hover:scale-105 font-semibold shadow-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleExport}
                disabled={!selectedFormat}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-purple-700 hover:from-purple-500 hover:via-purple-600 hover:to-purple-600 text-white font-semibold transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2 shadow-xl shadow-purple-500/50"
              >
                <Download size={16} />
                Exportar
              </button>
            </div>
          )}

          {exportState === 'error' && (
            <div className="px-6 py-5 border-t border-purple-500/30 bg-gradient-to-r from-gray-900/50 to-purple-900/30 backdrop-blur-xl flex justify-end gap-3">
              <button
                onClick={() => {
                  setExportState('idle');
                  setErrorMessage('');
                }}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-purple-500 to-purple-700 hover:from-purple-500 hover:via-purple-600 hover:to-purple-600 text-white font-semibold transition-all duration-300 hover:scale-105 shadow-xl shadow-purple-500/50"
              >
                Tentar novamente
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
