export type Sender = 'user' | 'bot';

export interface Message {
  sender: Sender;
  text: string;
}

export interface ApiResponse {
  answer: string;
}

export interface ApiTitleResponse {
    title: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  isPinned?: boolean;
}

export interface CodeSnippet {
  id: string;
  content: string;
  language: string;
}