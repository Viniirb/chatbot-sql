import { ChatRepository } from '../repositories/chat-repository';
import { SessionStorageRepository } from '../repositories/session-storage-repository';
import { ServerStatusRepository } from '../repositories/server-status-repository';
import { QuotaRepository } from '../repositories/quota-repository';
import { ExportRepository } from '../repositories/export-repository';

import { CreateSessionUseCase, SendMessageUseCase, GenerateTitleUseCase } from '../../core/application/use-cases/chat';
import { GetSessionsUseCase, DeleteSessionUseCase, UpdateSessionUseCase, ClearAllSessionsUseCase } from '../../core/application/use-cases/session';
import { GetQuotaStatusUseCase } from '../../core/application/use-cases/quota';
import { ExportSessionUseCase } from '../../core/application/use-cases/export';

export class DIContainer {
  private static instance: DIContainer;
  private services = new Map<string, unknown>();

  private constructor() {
    this.registerRepositories();
    this.registerUseCases();
  }

  static getInstance(): DIContainer {
    if (!DIContainer.instance) {
      DIContainer.instance = new DIContainer();
    }
    return DIContainer.instance;
  }

  private registerRepositories(): void {
    this.services.set('ChatRepository', new ChatRepository());
    this.services.set('SessionStorageRepository', new SessionStorageRepository());
    this.services.set('ServerStatusRepository', new ServerStatusRepository());
    this.services.set('QuotaRepository', new QuotaRepository());
    this.services.set('ExportRepository', new ExportRepository());
  }

  private registerUseCases(): void {
    const chatRepo = this.get('ChatRepository') as ChatRepository;
    const storageRepo = this.get('SessionStorageRepository') as SessionStorageRepository;
    const quotaRepo = this.get('QuotaRepository') as QuotaRepository;
    const exportRepo = this.get('ExportRepository') as ExportRepository;

    this.services.set('CreateSessionUseCase', new CreateSessionUseCase(chatRepo, storageRepo));
    this.services.set('SendMessageUseCase', new SendMessageUseCase(chatRepo, storageRepo));
    this.services.set('GenerateTitleUseCase', new GenerateTitleUseCase(chatRepo));
    
    this.services.set('GetSessionsUseCase', new GetSessionsUseCase(storageRepo));
    this.services.set('DeleteSessionUseCase', new DeleteSessionUseCase(storageRepo));
    this.services.set('UpdateSessionUseCase', new UpdateSessionUseCase(storageRepo));
    this.services.set('ClearAllSessionsUseCase', new ClearAllSessionsUseCase(storageRepo));
    
    this.services.set('GetQuotaStatusUseCase', new GetQuotaStatusUseCase(quotaRepo));
    this.services.set('ExportSessionUseCase', new ExportSessionUseCase(exportRepo));
  }

  get<T>(serviceName: string): T {
    const service = this.services.get(serviceName);
    if (!service) {
      throw new Error(`Service ${serviceName} not found`);
    }
    return service as T;
  }
}