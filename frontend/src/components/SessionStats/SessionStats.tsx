import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare, Activity, RefreshCw, Sparkles, Thermometer, Layers } from 'lucide-react';
import type { SessionStats as SessionStatsType } from '../../core/domain/entities';
import { GeminiLogo } from './GeminiLogo';

interface SessionStatsProps {
  onGetStats: () => Promise<SessionStatsType | null>;
}

const getModelLogo = (model: string) => {
  const modelLower = model.toLowerCase();
  
  if (modelLower.includes('gemini')) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-400 to-purple-300 p-1.5 flex items-center justify-center shadow-lg">
          <GeminiLogo size={22} />
        </div>
        <span className="font-semibold text-gray-200">{model}</span>
      </div>
    );
  }
  
  if (modelLower.includes('gpt')) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-lg">
          <Sparkles size={18} className="text-white" />
        </div>
        <span className="font-semibold text-gray-200">{model}</span>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg">
        <Sparkles size={18} className="text-white" />
      </div>
      <span className="font-semibold text-gray-200">{model}</span>
    </div>
  );
};

export const SessionStats: React.FC<SessionStatsProps> = ({ onGetStats }) => {
  const [stats, setStats] = useState<SessionStatsType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
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
  }, [onGetStats]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) {
    return (
      <div className="bg-gray-900/90 backdrop-blur-xl p-5 rounded-2xl border border-purple-500/30 shadow-2xl shadow-purple-500/10">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-700 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 p-5 rounded-xl">
        <p className="text-red-400 text-sm mb-2">{error}</p>
        <button
          onClick={loadStats}
          className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
        >
          <RefreshCw size={12} />
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-yellow-900/20 border border-yellow-800 p-5 rounded-xl">
        <p className="text-yellow-400 text-sm flex items-center gap-2">
          <Activity size={16} />
          Estatísticas da sessão não disponíveis
        </p>
      </div>
    );
  }

  const formatDate = (date: Date) => {
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-gray-900/90 backdrop-blur-xl p-5 rounded-2xl border border-purple-500/30 shadow-2xl shadow-purple-500/10">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-gray-100 flex items-center gap-2">
          <Activity size={18} className="text-blue-400" />
          Estatísticas da Sessão
        </h3>
        <button
          onClick={loadStats}
          className="text-gray-400 hover:text-blue-400 transition-colors p-1.5 hover:bg-gray-700/50 rounded-lg"
          title="Atualizar estatísticas"
        >
          <RefreshCw size={16} />
        </button>
      </div>
      
      {/* Model Info */}
      {stats.agent && (
        <div className="mb-4 p-3 bg-gray-900/50 rounded-lg border border-gray-700/30">
          <div className="mb-3">
            {getModelLogo(stats.agent.model)}
          </div>
          <div className="text-xs text-gray-400 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Thermometer size={12} className="text-orange-400" />
                Temperature:
              </span>
              <span className="text-gray-300 font-medium">{stats.agent.temperature}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Layers size={12} className="text-green-400" />
                Max Tokens:
              </span>
              <span className="text-gray-300 font-medium">{stats.agent.max_tokens.toLocaleString()}</span>
            </div>
            <div className="pt-1.5 border-t border-gray-700/50">
              <span className="text-gray-500">Provider: </span>
              <span className="text-blue-400 font-medium">{stats.agent.provider}</span>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-blue-900/20 p-3 rounded-lg border border-blue-800/30">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare size={14} className="text-blue-400" />
            <span className="text-xs text-gray-400">Mensagens</span>
          </div>
          <p className="text-2xl font-bold text-blue-300">{stats.messageCount}</p>
        </div>
        
        <div className="bg-purple-900/20 p-3 rounded-lg border border-purple-800/30">
          <div className="flex items-center gap-2 mb-1">
            <Activity size={14} className="text-purple-400" />
            <span className="text-xs text-gray-400">Consultas</span>
          </div>
          <p className="text-2xl font-bold text-purple-300">{stats.queryCount}</p>
        </div>
      </div>

      {/* Additional Info */}
      <div className="pt-3 border-t border-gray-700/50 space-y-2">
        <div className="text-xs text-gray-400">
          <span className="text-gray-500">Criada em: </span>
          <span className="text-gray-300">{formatDate(stats.createdAt)}</span>
        </div>
        
        {stats.message && (
          <div className="text-xs">
            <span className="text-gray-500">Status: </span>
            <span className="text-green-400">{stats.message}</span>
          </div>
        )}
      </div>
    </div>
  );
};