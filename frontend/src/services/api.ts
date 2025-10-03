import axios from 'axios';
import type { ApiResponse } from '../types';

const API_URL = 'http://127.0.0.1:8000/ask';

export const askAgent = async (query: string): Promise<string> => {
  try {
    const response = await axios.post<ApiResponse>(API_URL, { query });
    return response.data.answer;
  } catch (error) {
    console.error("Erro ao chamar a API:", error);
    return "Desculpe, ocorreu um erro de comunicação com o servidor. Verifique o terminal do backend para mais detalhes.";
  }
};