import { useQuotaStatus } from '../../presentation/hooks/use-quota-status';
import { AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react';

export const QuotaStatusIndicator = () => {
  const { quotaStatus, loading, refetch } = useQuotaStatus();

  const getStatusColor = () => {
    if (loading) return 'text-gray-400';
    if (!quotaStatus.isHealthy) return 'text-red-500';
    if (quotaStatus.hasRecentErrors) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getStatusIcon = () => {
    if (loading) return <RefreshCw size={16} className="animate-spin" />;
    if (!quotaStatus.isHealthy) return <AlertTriangle size={16} />;
    if (quotaStatus.hasRecentErrors) return <Clock size={16} />;
    return <CheckCircle size={16} />;
  };

  const getStatusText = () => {
    if (loading) return 'Verificando...';
    if (!quotaStatus.isHealthy) return 'Serviço offline';
    if (quotaStatus.isRateLimited) return 'Taxa limitada';
    if (quotaStatus.hasRecentErrors) return 'Instável';
    return 'Online';
  };

  const getTooltipText = () => {
    const baseText = `Taxa de sucesso: ${quotaStatus.successRate.toFixed(1)}%`;
    if (quotaStatus.lastError) {
      const errorTime = new Date(quotaStatus.lastError.timestamp).toLocaleTimeString();
      return `${baseText}\nÚltimo erro: ${quotaStatus.lastError.message} (${errorTime})`;
    }
    return baseText;
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={refetch}
        className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${getStatusColor()}`}
        title={getTooltipText()}
        disabled={loading}
      >
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
      </button>
      
      {!loading && (
        <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
          <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                quotaStatus.successRate > 90 ? 'bg-green-500' :
                quotaStatus.successRate > 70 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${quotaStatus.successRate}%` }}
            />
          </div>
          <span>{quotaStatus.successRate.toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
};