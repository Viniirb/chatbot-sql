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
    <footer className="p-4 border-t border-gray-800">
      <div className="max-w-4xl mx-auto">
        <ChatInput
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          onStop={onStop}
        />

        <div className="flex justify-between items-center mt-3">
          <p className={`text-xs font-medium ${statusDisplay.color}`}>
            {statusDisplay.text}
          </p>
          <p className="text-xs text-right text-gray-600">
            © 2025 - Vinicius Rolim Barbosa. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
};
