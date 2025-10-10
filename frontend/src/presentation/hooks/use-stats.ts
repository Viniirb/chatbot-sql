import { useState, useCallback, useEffect } from 'react';
import type { SessionStats } from '../../core/domain/entities';

const STATS_STORAGE_KEY = 'chat_session_stats';
const STATS_SYNC_INTERVAL = 30000; // 30 segundos

interface LocalStats {
  [sessionId: string]: {
    messageCount: number;
    queryCount: number;
    lastUpdated: Date;
  };
}

export interface UseStatsReturn {
  getStats: (sessionId: string) => SessionStats | null;
  updateStats: (sessionId: string, messageCount: number, queryCount: number) => void;
  syncStatsToBackend: (sessionId: string) => Promise<void>;
  clearStats: (sessionId: string) => void;
}

export const useStats = (): UseStatsReturn => {
  const [localStats, setLocalStats] = useState<LocalStats>(() => {
    const stored = localStorage.getItem(STATS_STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Converter strings de data para Date objects
        Object.keys(parsed).forEach(key => {
          parsed[key].lastUpdated = new Date(parsed[key].lastUpdated);
        });
        return parsed;
      } catch {
        return {};
      }
    }
    return {};
  });

  // Salvar no localStorage sempre que houver mudanças
  useEffect(() => {
    localStorage.setItem(STATS_STORAGE_KEY, JSON.stringify(localStats));
  }, [localStats]);

  const syncStatsToBackend = useCallback(async (sessionId: string) => {
    const stats = localStats[sessionId];
    if (!stats) return;

    try {
      // TODO: Implementar chamada para o backend
      // await fetch(`/api/sessions/${sessionId}/stats`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     messageCount: stats.messageCount,
      //     queryCount: stats.queryCount,
      //     timestamp: stats.lastUpdated.toISOString(),
      //   }),
      // });
      
  // stats sincronizados
    } catch (error) {
      console.error(`[Stats] Erro ao sincronizar stats do session ${sessionId}:`, error);
    }
  }, [localStats]);

  // Sincronização periódica com o backend
  useEffect(() => {
    const interval = setInterval(() => {
      Object.keys(localStats).forEach(sessionId => {
        syncStatsToBackend(sessionId).catch(console.error);
      });
    }, STATS_SYNC_INTERVAL);

    return () => clearInterval(interval);
  }, [localStats, syncStatsToBackend]);

  const getStats = useCallback((sessionId: string): SessionStats | null => {
    const stats = localStats[sessionId];
    if (!stats) return null;

    return {
      sessionId,
      messageCount: stats.messageCount,
      queryCount: stats.queryCount,
      createdAt: stats.lastUpdated,
      sessionExists: true,
    };
  }, [localStats]);

  const updateStats = useCallback((sessionId: string, messageCount: number, queryCount: number) => {
    setLocalStats(prev => ({
      ...prev,
      [sessionId]: {
        messageCount,
        queryCount,
        lastUpdated: new Date(),
      },
    }));
  }, []);

  const clearStats = useCallback((sessionId: string) => {
    setLocalStats(prev => {
      const newStats = { ...prev };
      delete newStats[sessionId];
      return newStats;
    });
  }, []);

  return {
    getStats,
    updateStats,
    syncStatsToBackend,
    clearStats,
  };
};
