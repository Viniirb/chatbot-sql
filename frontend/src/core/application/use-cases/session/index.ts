import type { ISessionStorageRepository } from '../../../domain/repositories';
import type { ChatSession } from '../../../domain/entities';

export class GetSessionsUseCase {
  private storageRepository: ISessionStorageRepository;
  
  constructor(storageRepository: ISessionStorageRepository) {
    this.storageRepository = storageRepository;
  }

  execute(): ChatSession[] {
    const sessions = this.storageRepository.getSessions();
    return Object.values(sessions).sort((a, b) => {
      if (a.isPinned === b.isPinned) {
        return b.updatedAt.getTime() - a.updatedAt.getTime();
      }
      return a.isPinned ? -1 : 1;
    });
  }
}

export class DeleteSessionUseCase {
  private storageRepository: ISessionStorageRepository;
  
  constructor(storageRepository: ISessionStorageRepository) {
    this.storageRepository = storageRepository;
  }

  execute(sessionId: string): void {
    this.storageRepository.deleteSession(sessionId);
    
    const backendMapping = this.storageRepository.getBackendSessionMapping();
    delete backendMapping[sessionId];
    this.storageRepository.saveBackendSessionMapping(backendMapping);
  }
}

export class UpdateSessionUseCase {
  private storageRepository: ISessionStorageRepository;
  
  constructor(storageRepository: ISessionStorageRepository) {
    this.storageRepository = storageRepository;
  }

  execute(sessionId: string, updates: Partial<ChatSession>): void {
    const sessions = this.storageRepository.getSessions();
    const session = sessions[sessionId];
    
    if (session) {
      const updatedSession = {
        ...session,
        ...updates,
        updatedAt: new Date()
      };
      this.storageRepository.saveSession(updatedSession);
    }
  }
}

export class ClearAllSessionsUseCase {
  private storageRepository: ISessionStorageRepository;
  
  constructor(storageRepository: ISessionStorageRepository) {
    this.storageRepository = storageRepository;
  }

  execute(): void {
    this.storageRepository.clearAllSessions();
  }
}