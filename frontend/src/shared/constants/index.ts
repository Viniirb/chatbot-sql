export const API_CONFIG = {
  BASE_URL: 'http://127.0.0.1:8000',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

export const STORAGE_KEYS = {
  CHAT_SESSIONS: 'chat_sessions',
  BACKEND_SESSION_MAPPING: 'backend_session_mapping',
  THEME: 'chat_theme',
} as const;

export const UI_CONFIG = {
  SIDEBAR_WIDTH: 256,
  MAX_FILE_SIZE: 10 * 1024 * 1024,
  MAX_FILES: 5,
  SCROLL_BEHAVIOR: 'smooth',
  TOAST_DURATION: {
    ERROR: 6000,
    SUCCESS: 3000,
    INFO: 4000,
    QUOTA_ERROR: 10000,
  },
} as const;

export const SUPPORTED_FILE_TYPES = {
  IMAGES: ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
  DOCUMENTS: ['.pdf', '.txt', '.csv', '.docx', '.doc', '.xlsx', '.xls'],
  CODE: ['.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.cs', '.html', '.css', '.json'],
  ARCHIVES: ['.zip', '.rar', '.7z', '.tar', '.gz'],
} as const;

export const PROGRAMMING_LANGUAGES = [
  { value: 'plaintext', label: 'Texto Simples' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'java', label: 'Java' },
  { value: 'csharp', label: 'C#' },
  { value: 'sql', label: 'SQL' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'jsx', label: 'JSX' },
  { value: 'go', label: 'Go' },
] as const;

export const THEMES = [
  { id: 'theme-neutral', name: 'Neutro', color: 'bg-gray-500' },
  { id: 'theme-blue', name: 'Azul', color: 'bg-blue-600' },
  { id: 'theme-green', name: 'Verde', color: 'bg-green-800' },
  { id: 'theme-purple', name: 'Roxo', color: 'bg-purple-600' },
] as const;

export const QUOTA_ERROR_MESSAGES = {
  QUOTA_EXCEEDED: 'Limite de quota diário atingido',
  RATE_LIMIT: 'Limite de taxa excedido',
  RESOURCE_EXHAUSTED: 'Recursos esgotados',
  API_KEY_INVALID: 'Chave API inválida',
  BILLING_NOT_ENABLED: 'Cobrança não habilitada',
  TIMEOUT: 'Timeout na requisição',
  GENERIC_ERROR: 'Erro desconhecido',
} as const;