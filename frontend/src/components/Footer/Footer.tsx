import { ChatInput } from "../ChatInput/ChatInput";
import { useServerStatus } from "../../presentation/hooks/use-server-status";

const getStatusDisplay = (status: { status: string; service: string; dbStatus: string } | null, loading: boolean) => {
  if (loading) {
    return { text: "Verificando Status...", color: "text-yellow-500" };
  }

  if (!status || status.status === "error" || status.dbStatus === "falha_import") {
    return { text: "Servidor: OFFLINE", color: "text-red-500" };
  }

  switch (status.dbStatus) {
    case "connected":
      return {
        text: "Status Servidor: OK",
        color: "text-green-400",
      };
    case "erro_db":
      return {
        text: "Status Servidor: Erro de Conexão",
        color: "text-red-500",
      };
    case "falha_import":
      return {
        text: "Status Servidor: Erro de Importação",
        color: "text-red-500",
      };
    default:
      return { text: "Status Servidor: Desconhecido", color: "text-yellow-500" };
  }
};

interface Props {
  onSendMessage: (text: string, files: File[]) => Promise<void>;
  isLoading: boolean;
  onStop?: () => void;
}

export const Footer = ({ onSendMessage, isLoading, onStop }: Props) => {
  const { serverStatus, loading } = useServerStatus();
  const statusDisplay = getStatusDisplay(serverStatus, loading);

  return (
    <footer className="px-4 py-3 border-t border-purple-500/20 bg-black/95 backdrop-blur-xl shadow-2xl shadow-purple-500/5">
      <div className="max-w-4xl mx-auto space-y-2">
        <ChatInput
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          onStop={onStop}
        />

        <div className="flex justify-between items-center text-[10px] text-gray-500 px-1">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${statusDisplay.color === 'text-green-400' ? 'bg-green-400 shadow-green-400/50' : statusDisplay.color === 'text-yellow-500' ? 'bg-yellow-400 shadow-yellow-400/50' : 'bg-red-500 shadow-red-500/50'} animate-pulse shadow-lg`}></div>
            <span className={statusDisplay.color}>
              {statusDisplay.text}
            </span>
          </div>
          <span className="text-gray-600">
            © 2025 Vinicius Rolim Barbosa
          </span>
        </div>
      </div>
    </footer>
  );
};
