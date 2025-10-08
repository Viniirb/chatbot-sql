import React, { useState, useEffect, useCallback } from 'react';
import type { SessionStats as SessionStatsType } from '../../core/domain/entities';

interface SessionStatsProps {
  onGetStats: () => Promise<SessionStatsType | null>;
  isVisible: boolean;
}

export const SessionStats: React.FC<SessionStatsProps> = ({ onGetStats, isVisible }) => {
  const [stats, setStats] = useState<SessionStatsType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    if (!isVisible) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const sessionStats = await onGetStats();
      setStats(sessionStats);
    } catch (err) {
      setError('Erro ao carregar estatísticas da sessão');
      console.error('Error loading session stats:', err);
    } finally {
      setLoading(false);
    }
  }, [isVisible, onGetStats]);

  useEffect(() => {
    if (isVisible) {
      loadStats();
    }
  }, [isVisible, loadStats]);

  if (!isVisible) return null;

  if (loading) {
    return (
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        <button
          onClick={loadStats}
          className="mt-2 text-xs text-red-600 dark:text-red-400 hover:underline"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4 rounded-lg">
        <p className="text-yellow-600 dark:text-yellow-400 text-sm">
          📊 Estatísticas da sessão não disponíveis
        </p>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-200">
          📊 Estatísticas da Sessão
        </h3>
        <button
          onClick={loadStats}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          title="Atualizar estatísticas"
        >
          🔄
        </button>
      </div>
      
      <div className="space-y-2 text-sm text-blue-700 dark:text-blue-300">
        <div className="flex justify-between">
          <span>Total de mensagens:</span>
          <span className="font-semibold">{stats.totalMessages}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Suas mensagens:</span>
          <span className="font-semibold">{stats.userMessages}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Respostas do assistente:</span>
          <span className="font-semibold">{stats.assistantMessages}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Contexto (caracteres):</span>
          <span className="font-semibold">{stats.contextLength.toLocaleString()}</span>
        </div>
        
        {stats.tokenUsage && (
          <div className="pt-2 border-t border-blue-200 dark:border-blue-700">
            <div className="flex justify-between">
              <span>Tokens totais:</span>
              <span className="font-semibold">{stats.tokenUsage.totalTokens.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-xs opacity-80">
              <span>Prompt: {stats.tokenUsage.promptTokens.toLocaleString()}</span>
              <span>Completion: {stats.tokenUsage.completionTokens.toLocaleString()}</span>
            </div>
          </div>
        )}
        
        <div className="pt-2 border-t border-blue-200 dark:border-blue-700 text-xs opacity-80">
          <div>Criado: {formatDate(stats.createdAt.toISOString())}</div>
          <div>Última atividade: {formatDate(stats.lastActivity.toISOString())}</div>
        </div>
      </div>
    </div>
  );
};