import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import type { ApiError } from '../../core/domain/value-objects';

export class ApiClient {
  private client: AxiosInstance;
  private statusClient: AxiosInstance;
  private readonly baseURL = 'http://127.0.0.1:8000';

  constructor() {
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 0,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.statusClient = axios.create({
      baseURL: this.baseURL,
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    const errorHandler = (error: unknown) => {
        if (axios.isCancel(error)) {
          return Promise.reject({ type: 'REQUEST_ABORTED' });
        }

        if (axios.isAxiosError(error) && error.response) {
          const status = error.response.status;
          const data = error.response.data;

          const errorDetail = data?.detail;
          const errorMessage = errorDetail?.error || '';
          
          const isQuotaError = 
            status === 429 || 
            status === 503 ||
            errorMessage.includes('quota') ||
            errorMessage.includes('RESOURCE_EXHAUSTED') ||
            errorMessage.includes('Too Many Requests') ||
            errorDetail?.error_code === 'PROCESSING_ERROR' && errorMessage.includes('429');

          if (isQuotaError) {
            let retryAfter: number | undefined;
            
            if (errorMessage.includes('retry in')) {
              const match = errorMessage.match(/retry in (\d+(\.\d+)?)/);
              if (match) {
                retryAfter = Math.ceil(parseFloat(match[1]));
              }
            }
            
            const apiError: ApiError = {
              type: 'QUOTA_ERROR',
              errorCode: 'QUOTA_EXCEEDED',
              message: 'Limite de requisições da API excedido. Aguarde alguns instantes.',
              retryAfter: retryAfter || errorDetail?.retry_after,
              userActionRequired: errorDetail?.user_action_required,
              timestamp: errorDetail?.timestamp || Date.now(),
            };
            return Promise.reject(apiError);
          }

          if (status >= 500) {
            return Promise.reject({
              type: 'SERVER_ERROR',
              message: errorMessage || 'Erro interno do servidor',
            } as ApiError);
          }

          if (status >= 400) {
            return Promise.reject({
              type: 'CLIENT_ERROR',
              message: errorMessage || 'Erro na requisição',
            } as ApiError);
          }
        }

        return Promise.reject({
          type: 'NETWORK_ERROR',
          message: 'Erro de comunicação com o servidor',
        } as ApiError);
    };

    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      errorHandler
    );
    
    this.statusClient.interceptors.response.use(
      (response: AxiosResponse) => response,
      errorHandler
    );
  }

  async get<T>(url: string, signal?: AbortSignal): Promise<T> {
    const response = await this.client.get<T>(url, { signal });
    return response.data;
  }

  async post<T>(url: string, data?: unknown, signal?: AbortSignal, headers?: Record<string, string>): Promise<T> {
    const response = await this.client.post<T>(url, data, { signal, headers });
    return response.data;
  }

  async put<T>(url: string, data?: unknown, signal?: AbortSignal): Promise<T> {
    const response = await this.client.put<T>(url, data, { signal });
    return response.data;
  }

  async delete<T>(url: string, signal?: AbortSignal): Promise<T> {
    const response = await this.client.delete<T>(url, { signal });
    return response.data;
  }

  async getStatus<T>(url: string): Promise<T> {
    const response = await this.statusClient.get<T>(url);
    return response.data;
  }
}