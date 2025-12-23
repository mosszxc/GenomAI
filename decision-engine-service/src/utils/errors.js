/**
 * Custom Error Classes
 */
export class DecisionEngineError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'DecisionEngineError';
    this.code = code;
    this.details = details;
    this.status = 500;
  }
}

export class IdeaNotFoundError extends DecisionEngineError {
  constructor(ideaId) {
    super('IDEA_NOT_FOUND', `Idea not found: ${ideaId}`, { idea_id: ideaId });
    this.status = 404;
  }
}

export class InvalidInputError extends DecisionEngineError {
  constructor(message, details = {}) {
    super('INVALID_INPUT', message, details);
    this.status = 400;
  }
}

export class SupabaseError extends DecisionEngineError {
  constructor(message, details = {}) {
    super('SUPABASE_ERROR', `Supabase error: ${message}`, details);
    this.status = 500;
  }
}

