import axios from 'axios';
import type { ApiResponse, ApiTitleResponse } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000';

export const askAgent = async (query: string, signal: AbortSignal): Promise<string> => {
  try {
    const response = await axios.post<ApiResponse>(`${API_BASE_URL}/ask`, { query }, { signal });
    return response.data.answer;
  } catch (error) {
    if (axios.isCancel(error)) {
      console.log("Request canceled by user");
      return 'REQUEST_ABORTED';
    }
    console.error("Erro ao chamar a API:", error);
    return "Desculpe, ocorreu um erro de comunicação com o servidor.";
  }
};

export const generateTitle = async (prompt: string): Promise<string> => {
    try {
      const response = await axios.post<ApiTitleResponse>(`${API_BASE_URL}/generate-title`, { prompt });
      return response.data.title;
    } catch (error) {
      console.error("Erro ao gerar título:", error);
      return "Conversa";
    }
  };