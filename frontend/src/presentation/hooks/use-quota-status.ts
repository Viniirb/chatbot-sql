import { useState, useEffect, useCallback } from 'react';
import type { QuotaSystemState } from '../../core/domain/value-objects';
import { DIContainer } from '../../infrastructure/di/container';
import type { GetQuotaStatusUseCase } from '../../core/application/use-cases/quota';

export interface UseQuotaStatusReturn {
  quotaStatus: QuotaSystemState;
  loading: boolean;
  refetch: () => Promise<void>;
}

export const useQuotaStatus = (): UseQuotaStatusReturn => {
  const [quotaStatus, setQuotaStatus] = useState<QuotaSystemState>({
    isHealthy: true,
    successRate: 100,
    hasRecentErrors: false,
    isRateLimited: false,
  });
  const [loading, setLoading] = useState(false);

  const container = DIContainer.getInstance();
  const getQuotaStatusUseCase = container.get<GetQuotaStatusUseCase>('GetQuotaStatusUseCase');

  const fetchQuotaStatus = useCallback(async () => {
    setLoading(true);
    try {
      const status = await getQuotaStatusUseCase.execute();
      setQuotaStatus(status);
    } catch (error) {
      console.error('Failed to fetch quota status:', error);
      setQuotaStatus({
        isHealthy: false,
        successRate: 0,
        hasRecentErrors: true,
        isRateLimited: false,
        lastError: {
          type: 'GENERIC_ERROR',
          message: 'Não foi possível verificar o status',
          timestamp: Date.now(),
        },
      });
    } finally {
      setLoading(false);
    }
  }, [getQuotaStatusUseCase]);

  useEffect(() => {
    fetchQuotaStatus();
    
    const interval = setInterval(fetchQuotaStatus, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [fetchQuotaStatus]);

  return {
    quotaStatus,
    loading,
    refetch: fetchQuotaStatus,
  };
};