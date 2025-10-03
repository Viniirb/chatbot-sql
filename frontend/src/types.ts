export type Sender = 'user' | 'bot';

export interface Message{
    sender: Sender;
    text: string;
}

export interface ApiResponse {
    answer: string;
}