export type QuotaErrorType = 
  | 'QUOTA_EXCEEDED'
  | 'RATE_LIMIT'
  | 'RESOURCE_EXHAUSTED'
  | 'API_KEY_INVALID'
  | 'BILLING_NOT_ENABLED'
  | 'TIMEOUT'
  | 'GENERIC_ERROR';

export type ApiErrorType = 
  | 'QUOTA_ERROR' 
  | 'SERVER_ERROR' 
  | 'CLIENT_ERROR' 
  | 'NETWORK_ERROR';

export interface ApiError {
  type: ApiErrorType;
  message: string;
  errorCode?: QuotaErrorType;
  retryAfter?: number;
  userActionRequired?: boolean;
  timestamp?: number;
}

export interface QuotaSystemState {
  isHealthy: boolean;
  successRate: number;
  hasRecentErrors: boolean;
  isRateLimited: boolean;
  lastError?: {
    type: QuotaErrorType;
    message: string;
    timestamp: number;
  };
}

export type ServerStatus = 'ok' | 'error';
export type DatabaseStatus = 'ok' | 'erro_db' | 'falha_import';
export type Theme = 'theme-neutral' | 'theme-blue' | 'theme-green' | 'theme-purple' | 'theme-custom';

export * from './export-format';