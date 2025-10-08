import { DIContainer } from './infrastructure/di/container';

const container = DIContainer.getInstance();

export { container as diContainer };

export type {
  ChatSession,
  Message,
  SessionStats,
  FileAttachment,
  CodeSnippet,
} from './core/domain/entities';

export type {
  ApiError,
  QuotaErrorType,
  QuotaSystemState,
  Theme,
} from './core/domain/value-objects';

export * from './presentation';
export * from './shared';