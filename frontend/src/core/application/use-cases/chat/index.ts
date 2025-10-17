import type { IChatRepository, ISessionStorageRepository } from '../../../domain/repositories';
import type { ChatSession, Message } from '../../../domain/entities';
import { v4 as uuidv4 } from 'uuid';

export class CreateSessionUseCase {
  private chatRepository: IChatRepository;
  private storageRepository: ISessionStorageRepository;
  
  constructor(
    chatRepository: IChatRepository,
    storageRepository: ISessionStorageRepository
  ) {
    this.chatRepository = chatRepository;
    this.storageRepository = storageRepository;
  }

  async execute(): Promise<ChatSession> {
    try {
      const backendSessionId = await this.chatRepository.createSession();
      const sessionId = uuidv4();
      
      const session: ChatSession = {
        id: sessionId,
        title: 'Nova Conversa',
        messages: [{
          id: uuidv4(),
          content: 'Olá! Em que posso ajudar com o banco de dados hoje?',
          role: 'assistant',
          timestamp: new Date()
        }],
        isPinned: false,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      this.storageRepository.saveSession(session);
      
      const backendMapping = this.storageRepository.getBackendSessionMapping();
      backendMapping[sessionId] = backendSessionId;
      this.storageRepository.saveBackendSessionMapping(backendMapping);
      
      return session;
    } catch {
      const sessionId = uuidv4();
      const fallbackSession: ChatSession = {
        id: sessionId,
        title: 'Nova Conversa',
        messages: [{
          id: uuidv4(),
          content: 'Olá! Em que posso ajudar com o banco de dados hoje?',
          role: 'assistant',
          timestamp: new Date()
        }],
        isPinned: false,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      
      this.storageRepository.saveSession(fallbackSession);
      return fallbackSession;
    }
  }
}

export class SendMessageUseCase {
  private chatRepository: IChatRepository;
  private storageRepository: ISessionStorageRepository;
  
  constructor(
    chatRepository: IChatRepository,
    storageRepository: ISessionStorageRepository
  ) {
    this.chatRepository = chatRepository;
    this.storageRepository = storageRepository;
  }

  async execute(
    sessionId: string,
    content: string,
    signal?: AbortSignal,
    clientMessageId?: string
  ): Promise<{ botMessage: Message; requestId?: string }> {
    const backendMapping = this.storageRepository.getBackendSessionMapping();
    const backendSessionId = backendMapping[sessionId];
    
    const sessions = this.storageRepository.getSessions();
    const currentSession = sessions[sessionId];
    const conversationHistory = currentSession?.messages || [];

    const response = await this.chatRepository.sendMessage(
      content,
      conversationHistory,
      backendSessionId,
      signal,
      clientMessageId
    );

    // Response pode ser string ou um objeto { answer: string, requestId?: string }
    let answerText: string;
    let requestId: string | undefined;
    if (typeof response === 'string') {
      answerText = response;
    } else if (response && typeof response === 'object') {
      // tenta extrair answer/requestId com segurança
      answerText = (response as { answer?: string }).answer || 'Desculpe, não encontrei resultados para sua pergunta.';
      requestId = (response as { requestId?: string }).requestId;
    } else {
      answerText = 'Desculpe, não encontrei resultados para sua pergunta.';
    }

    const botMessage: Message = {
      id: uuidv4(),
      content: answerText,
      role: 'assistant',
      timestamp: new Date()
    };

    return { botMessage, requestId };
  }
}

export class GenerateTitleUseCase {
  private chatRepository: IChatRepository;
  
  constructor(chatRepository: IChatRepository) {
    this.chatRepository = chatRepository;
  }

  async execute(prompt: string): Promise<string> {
    try {
      return await this.chatRepository.generateTitle(prompt);
    } catch {
      return 'Conversa';
    }
  }
}