import { useState, useEffect } from "react";
import axios from "axios";
import { ChatInput } from "../ChatInput/ChatInput";

interface ServerStatusResponse {
  status: "ok" | "error";
  service: string;
  db_status: "ok" | "erro_db" | "falha_import";
}

const API_BASE_URL = "http://127.0.0.1:8000";

const getServerStatus = async (): Promise<ServerStatusResponse | null> => {
  try {
    const response = await axios.get<ServerStatusResponse>(
      `${API_BASE_URL}/status`
    );
    return response.data;
  } catch {
    return {
      status: "error",
      service: "Offline",
      db_status: "falha_import",
    };
  }
};

const getStatusDisplay = (status: ServerStatusResponse | null) => {
  if (!status) {
    return { text: "Verificando Status...", color: "text-yellow-500" };
  }

  if (status.status === "error" || status.db_status === "falha_import") {
    return { text: "Servidor: OFFLINE", color: "text-red-500" };
  }

  switch (status.db_status) {
    case "ok":
      return {
        text: "Status Servidor: OK (Em Funcionamento)",
        color: "text-green-400",
      };
    case "erro_db":
      return {
        text: "Status Servidor: Erro de Conexão",
        color: "text-red-500",
      };
    default:
      return { text: "Status Servidor: OK", color: "text-yellow-500" };
  }
};

interface Props {
  onSendMessage: (text: string, files: File[]) => void;
  isLoading: boolean;
  onStop?: () => void;
}

export const Footer = ({ onSendMessage, isLoading, onStop }: Props) => {
  const [serverStatus, setServerStatus] = useState<ServerStatusResponse | null>(
    null
  );

  useEffect(() => {
    const fetchStatus = async () => {
      const status = await getServerStatus();
      setServerStatus(status);
    };

    fetchStatus();
    const intervalId = setInterval(fetchStatus, 5000);

    return () => clearInterval(intervalId);
  }, []);

  const statusDisplay = getStatusDisplay(serverStatus);

  return (
    <footer className="p-4 border-t border-gray-800">
      <div className="max-w-4xl mx-auto">
        <ChatInput
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          onStop={onStop}
        />

        <div className="flex justify-between items-center mt-3">
          {/* O status fica à esquerda */}
          <p className={`text-xs font-medium ${statusDisplay.color}`}>
            {statusDisplay.text}
          </p>
          {/* Os direitos autorais ficam à direita */}
          <p className="text-xs text-right text-gray-600">
            © 2025 - N-Tecnologias. Todos os direitos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
};
