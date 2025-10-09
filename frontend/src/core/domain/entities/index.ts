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
    canRetryAt?: Date;
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

export interface AgentInfo {
  model: string;
  temperature: number;
  max_tokens: number;
  provider: string;
}

export interface SessionStats {
  sessionId: string;
  messageCount: number;
  queryCount: number;
  createdAt: Date;
  sessionExists: boolean;
  agent?: AgentInfo;
  message?: string;
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