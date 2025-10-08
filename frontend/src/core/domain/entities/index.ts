export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  metadata?: Record<string, unknown>;
  error?: {
    message: string;
    retryAfter?: number;
    canRetry: boolean;
    canRetryAt?: Date; // Timestamp de quando pode reenviar
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  isPinned: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface SessionStats {
  sessionId: string;
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  createdAt: Date;
  lastActivity: Date;
  contextLength: number;
  tokenUsage?: TokenUsage;
}

export interface TokenUsage {
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
}

export interface FileAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  content?: string;
}

export interface CodeSnippet {
  id: string;
  content: string;
  language: string;
}