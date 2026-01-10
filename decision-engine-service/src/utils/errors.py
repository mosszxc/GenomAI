"""
Custom Error Classes
"""


class DecisionEngineError(Exception):
    """Base exception for Decision Engine errors"""

    def __init__(self, code: str, message: str, details: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = 500


class IdeaNotFoundError(DecisionEngineError):
    """Raised when idea is not found"""

    def __init__(self, idea_id: str):
        super().__init__(
            "IDEA_NOT_FOUND", f"Idea not found: {idea_id}", {"idea_id": idea_id}
        )
        self.status_code = 404


class InvalidInputError(DecisionEngineError):
    """Raised when input validation fails"""

    def __init__(self, message: str, details: dict = None):
        super().__init__("INVALID_INPUT", message, details or {})
        self.status_code = 400


class SupabaseError(DecisionEngineError):
    """Raised when Supabase operation fails"""

    def __init__(self, message: str, details: dict = None):
        super().__init__("SUPABASE_ERROR", f"Supabase error: {message}", details or {})
        self.status_code = 500
