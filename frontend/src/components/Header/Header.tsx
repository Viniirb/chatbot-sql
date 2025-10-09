import { Database } from 'lucide-react';

export const Header = () => {
  return (
  <header className="p-4 border-b border-purple-500/20 bg-black/95 backdrop-blur-xl shadow-lg shadow-purple-500/10">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30 shadow-lg shadow-purple-500/20">
            <Database size={28} className="text-purple-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
              Chat com Banco de Dados
            </h1>
            <p className="text-xs text-gray-400 mt-0.5">Agente de IA para consultas em linguagem natural</p>
          </div>
        </div>
        {/* ColorPicker removido */}
      </div>
    </header>
  );
};