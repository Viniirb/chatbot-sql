import { useState, useEffect, useCallback } from 'react';
import { DIContainer } from '../../infrastructure/di/container';
import type { IServerStatusRepository } from '../../core/domain/repositories';

export interface ServerStatus {
  status: 'ok' | 'error';
  service: string;
  dbStatus: 'connected' | 'erro_db' | 'falha_import';
}

export interface UseServerStatusReturn {
  serverStatus: ServerStatus | null;
  loading: boolean;
  refetch: () => Promise<void>;
}

export const useServerStatus = (): UseServerStatusReturn => {
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const container = DIContainer.getInstance();
  const serverStatusRepo = container.get<IServerStatusRepository>('ServerStatusRepository');

  const fetchServerStatus = useCallback(async () => {
    setLoading(true);
    try {
      const status = await serverStatusRepo.getServerStatus();
      setServerStatus(status);
    } catch (error) {
      console.error('Failed to fetch server status:', error);
      setServerStatus({
        status: 'error',
        service: 'Offline',
        dbStatus: 'falha_import',
      });
    } finally {
      setLoading(false);
    }
  }, [serverStatusRepo]);

  useEffect(() => {
    fetchServerStatus();
    
    const interval = setInterval(fetchServerStatus, 30000);
    
    return () => clearInterval(interval);
  }, [fetchServerStatus]);

  return {
    serverStatus,
    loading,
    refetch: fetchServerStatus,
  };
};