"""
Structured Logging with Trace IDs for Temporal Workflows

Provides structured logging with automatic trace context binding:
- workflow_id: Unique workflow identifier
- run_id: Workflow run identifier (for retries)
- activity_name: Name of the current activity
- creative_id/idea_id: Business context

Usage in workflows:
    from temporal.tracing import get_workflow_logger

    @workflow.run
    async def run(self, input: CreativeInput) -> PipelineResult:
        logger = get_workflow_logger(creative_id=input.creative_id)
        logger.info("Processing creative")
        # Output: {"workflow_id": "...", "run_id": "...", "creative_id": "...", "event": "Processing creative"}

Usage in activities:
    from temporal.tracing import get_activity_logger

    @activity.defn
    async def transcribe_audio(audio_url: str, creative_id: str) -> dict:
        logger = get_activity_logger(creative_id=creative_id)
        logger.info("Starting transcription")
        # Output: {"activity": "transcribe_audio", "creative_id": "...", "event": "Starting transcription"}
"""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.typing import EventDict, WrappedLogger


def _add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log events."""
    import datetime

    event_dict["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    return event_dict


def _add_log_level(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def _rename_event_key(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Rename 'event' to 'message' for consistency."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def configure_structlog(json_output: bool = True) -> None:
    """
    Configure structlog for the application.

    Args:
        json_output: If True, output JSON logs (production).
                    If False, use console renderer (development).
    """
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        _add_timestamp,
        _add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _rename_event_key,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_workflow_logger(**context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger bound with workflow context.

    Must be called from within a workflow context.
    Automatically extracts workflow_id and run_id from Temporal.

    Args:
        **context: Additional context to bind (creative_id, idea_id, etc.)

    Returns:
        Bound structlog logger

    Example:
        logger = get_workflow_logger(creative_id="abc-123")
        logger.info("Starting pipeline")
    """
    from temporalio import workflow

    info = workflow.info()

    bound_context = {
        "workflow_id": info.workflow_id,
        "run_id": info.run_id,
        "workflow_type": info.workflow_type,
    }
    bound_context.update(context)

    return structlog.get_logger().bind(**bound_context)


def get_activity_logger(**context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger bound with activity context.

    Must be called from within an activity context.
    Automatically extracts activity name and workflow info from Temporal.

    Args:
        **context: Additional context to bind (creative_id, transcript_id, etc.)

    Returns:
        Bound structlog logger

    Example:
        logger = get_activity_logger(creative_id="abc-123")
        logger.info("Transcription started", url=audio_url)
    """
    from temporalio import activity

    info = activity.info()

    bound_context = {
        "activity": info.activity_type,
        "workflow_id": info.workflow_id,
        "run_id": info.workflow_run_id,
        "attempt": info.attempt,
    }

    # Add task queue for debugging routing issues
    if info.task_queue:
        bound_context["task_queue"] = info.task_queue

    bound_context.update(context)

    return structlog.get_logger().bind(**bound_context)


def get_logger(name: Optional[str] = None, **context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a generic structured logger with optional context binding.

    Use this for non-workflow/activity code (e.g., API routes, scripts).

    Args:
        name: Logger name (usually __name__)
        **context: Context to bind

    Returns:
        Bound structlog logger

    Example:
        logger = get_logger(__name__, request_id="xyz")
        logger.info("Processing request")
    """
    logger = structlog.get_logger(name) if name else structlog.get_logger()
    if context:
        return logger.bind(**context)
    return logger


class WorkflowLoggerMixin:
    """
    Mixin class for workflows that provides a pre-bound logger.

    Usage:
        @workflow.defn
        class MyWorkflow(WorkflowLoggerMixin):
            @workflow.run
            async def run(self, input: MyInput) -> MyResult:
                self._init_logger(creative_id=input.creative_id)
                self._log.info("Starting workflow")
    """

    _log: structlog.stdlib.BoundLogger

    def _init_logger(self, **context: Any) -> None:
        """Initialize the workflow logger with context."""
        self._log = get_workflow_logger(**context)


class ActivityLoggerMixin:
    """
    Mixin for activity classes that need a pre-bound logger.

    Note: Most activities are functions, not classes.
    Use get_activity_logger() directly for function-based activities.
    """

    _log: structlog.stdlib.BoundLogger

    def _init_logger(self, **context: Any) -> None:
        """Initialize the activity logger with context."""
        self._log = get_activity_logger(**context)
