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
    signal?: AbortSignal
  ): Promise<{ botMessage: Message }> {
    const backendMapping = this.storageRepository.getBackendSessionMapping();
    const backendSessionId = backendMapping[sessionId];
    
    const sessions = this.storageRepository.getSessions();
    const currentSession = sessions[sessionId];
    const conversationHistory = currentSession?.messages || [];

    const response = await this.chatRepository.sendMessage(
      content,
      conversationHistory,
      backendSessionId,
      signal
    );

    const botMessage: Message = {
      id: uuidv4(),
      content: response || 'Desculpe, não encontrei resultados para sua pergunta.',
      role: 'assistant',
      timestamp: new Date()
    };

    return { botMessage };
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