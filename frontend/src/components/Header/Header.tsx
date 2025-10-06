import { Database } from 'lucide-react';
import { ThemeSwitcher } from '../ThemeSwitcher/ThemeSwitcher';

export const Header = () => {
  return (
    <header className="p-4 border-b border-gray-800">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center space-x-3">
          <Database size={28} className="text-gray-400" />
          <div>
            <h1 className="text-lg font-semibold text-gray-200">Chat com Banco de Dados</h1>
            <p className="text-xs text-gray-400">Agente de IA para consultas em linguagem natural</p>
          </div>
        </div>
        <ThemeSwitcher />
      </div>
    </header>
  );
};