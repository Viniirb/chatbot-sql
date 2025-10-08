import type { IQuotaRepository } from '../../core/domain/repositories';
import { ApiClient } from '../http/api-client';

interface QuotaStatsResponse {
  status: 'ok' | 'error';
  stats: {
    total_requests: number;
    successful_requests: number;
    success_rate: number;
    quota_errors_count: number;
    error_types: Record<string, number>;
    recent_errors: Array<{
      error_type: string;
      timestamp: number;
      retry_after?: number;
    }>;
  };
}

interface HealthResponse {
  status: 'ok' | 'error';
  service: string;
  database: 'ok' | 'error';
  quota_health: {
    success_rate: number;
    total_requests: number;
    recent_errors: number;
  };
  timestamp: number;
}

export class QuotaRepository implements IQuotaRepository {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  async getQuotaStats(): Promise<{
    totalRequests: number;
    successfulRequests: number;
    successRate: number;
    quotaErrorsCount: number;
    recentErrors: Array<{
      errorType: string;
      timestamp: number;
    }>;
  } | null> {
    try {
      const response = await this.apiClient.get<QuotaStatsResponse>('/quota/stats');
      
      if (response.status === 'ok') {
        return {
          totalRequests: response.stats.total_requests,
          successfulRequests: response.stats.successful_requests,
          successRate: response.stats.success_rate,
          quotaErrorsCount: response.stats.quota_errors_count,
          recentErrors: response.stats.recent_errors.map(error => ({
            errorType: error.error_type,
            timestamp: error.timestamp,
          })),
        };
      }
      
      return null;
    } catch (error) {
      console.warn('Detailed quota stats not available:', error);
      return null;
    }
  }

  async getHealthStatus(): Promise<{
    status: 'ok' | 'error';
    quotaHealth: {
      successRate: number;
      totalRequests: number;
      recentErrors: number;
    };
  } | null> {
    try {
      const response = await this.apiClient.get<HealthResponse>('/health');
      
      return {
        status: response.status,
        quotaHealth: {
          successRate: response.quota_health.success_rate,
          totalRequests: response.quota_health.total_requests,
          recentErrors: response.quota_health.recent_errors,
        },
      };
    } catch (error) {
      console.error('Failed to fetch health status:', error);
      return null;
    }
  }
}