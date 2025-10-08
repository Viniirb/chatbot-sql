import type { IQuotaRepository } from '../../../domain/repositories';
import type { QuotaSystemState, QuotaErrorType } from '../../../domain/value-objects';

export class GetQuotaStatusUseCase {
  private quotaRepository: IQuotaRepository;
  
  constructor(quotaRepository: IQuotaRepository) {
    this.quotaRepository = quotaRepository;
  }

  async execute(): Promise<QuotaSystemState> {
    try {
      const stats = await this.quotaRepository.getQuotaStats();
      
      if (stats) {
        return {
          isHealthy: stats.successRate > 80,
          successRate: stats.successRate,
          hasRecentErrors: stats.recentErrors.length > 0,
          isRateLimited: stats.recentErrors.some(err => err.errorType === 'RATE_LIMIT'),
          lastError: stats.recentErrors.length > 0 ? {
            type: stats.recentErrors[0].errorType as QuotaErrorType,
            message: this.getErrorMessage(stats.recentErrors[0].errorType as QuotaErrorType),
            timestamp: stats.recentErrors[0].timestamp,
          } : undefined,
        };
      }

      const health = await this.quotaRepository.getHealthStatus();
      
      if (health && health.status === 'ok') {
        return {
          isHealthy: health.quotaHealth.successRate > 80,
          successRate: health.quotaHealth.successRate,
          hasRecentErrors: health.quotaHealth.recentErrors > 0,
          isRateLimited: false,
        };
      }

      throw new Error('Health check failed');
    } catch {
      return {
        isHealthy: false,
        successRate: 0,
        hasRecentErrors: true,
        isRateLimited: false,
        lastError: {
          type: 'GENERIC_ERROR',
          message: 'Não foi possível verificar o status',
          timestamp: Date.now(),
        },
      };
    }
  }

  private getErrorMessage(errorType: QuotaErrorType): string {
    switch (errorType) {
      case 'QUOTA_EXCEEDED':
        return 'Quota diária excedida';
      case 'RATE_LIMIT':
        return 'Limite de taxa atingido';
      case 'RESOURCE_EXHAUSTED':
        return 'Recursos esgotados';
      case 'API_KEY_INVALID':
        return 'Chave API inválida';
      case 'BILLING_NOT_ENABLED':
        return 'Cobrança não habilitada';
      case 'TIMEOUT':
        return 'Timeout';
      default:
        return 'Erro desconhecido';
    }
  }
}